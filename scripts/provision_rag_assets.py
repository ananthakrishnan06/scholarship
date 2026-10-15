"""Validate the reviewed FAISS bundle and provision one pinned public model snapshot.

This packaging tool never ingests data, accesses Django's database, or calls Gemini.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_manifest(root=ROOT):
    manifest = json.loads((root / "deploy/rag-assets.json").read_text(encoding="utf-8"))
    if manifest["format_version"] != 1:
        raise ValueError("Unsupported deployment asset manifest.")
    if not re.fullmatch(r"[0-9a-f]{32}", manifest["index_version"]):
        raise ValueError("Invalid deployment index version.")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest["embedding_revision"]):
        raise ValueError("The model must use an immutable revision.")
    return manifest


def index_paths(manifest):
    version = manifest["index_version"]
    return {
        "CURRENT",
        *(version + "/" + name for name in ("vectors.faiss", "chunks.json", "metadata.json")),
    }


def validate_index(manifest, root=ROOT):
    directory = root / "var/index"
    if set(manifest["index_files"]) != index_paths(manifest):
        raise ValueError("The deployment index allowlist must contain exactly four files.")
    for name, expected in manifest["index_files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Deployment index checksum mismatch: " + name)
    if (directory / "CURRENT").read_text().strip() != manifest["index_version"]:
        raise ValueError("Deployment CURRENT differs from the reviewed index.")
    if (
        hashlib.sha256((root / "data/scholarship_dataset_ready.json").read_bytes()).hexdigest()
        != manifest["corpus_sha256"]
    ):
        raise ValueError("The deployment corpus differs from the reviewed index.")
    metadata = json.loads((directory / manifest["index_version"] / "metadata.json").read_text())
    expected = {
        "embedding_model": manifest["embedding_model"],
        "dimension": manifest["dimension"],
        "chunk_count": manifest["chunk_count"],
        "corpus_hash": manifest["corpus_sha256"],
    }
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError("Deployment index/model metadata mismatch.")
    for name, key in (("chunks.json", "chunks_sha256"), ("vectors.faiss", "index_sha256")):
        if manifest["index_files"][manifest["index_version"] + "/" + name] != metadata[key]:
            raise ValueError("Manifest and index integrity metadata disagree.")


def model_cache(manifest):
    from huggingface_hub.constants import HF_HUB_CACHE

    return Path(HF_HUB_CACHE) / ("models--" + manifest["embedding_model"].replace("/", "--"))


def validate_model_files(manifest, snapshot):
    for name, expected in manifest["model_files"].items():
        relative = Path(name)
        # Linux HF snapshots link weights into the sibling blobs directory.
        # Accept that cache layout, while rejecting escapes outside this model.
        path = (snapshot / relative).resolve()
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or snapshot.parent.parent.resolve() not in path.parents
        ):
            raise ValueError("Unsafe model asset path: " + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Pinned model checksum mismatch: " + name)


def download_model(manifest):
    from huggingface_hub import snapshot_download

    cache = model_cache(manifest)
    snapshot = Path(
        snapshot_download(
            repo_id=manifest["embedding_model"],
            revision=manifest["embedding_revision"],
            allow_patterns=list(manifest["model_files"]),
            cache_dir=str(cache.parent),
            token=False,  # This pinned public model requires no cached or environment token.
        )
    )
    if snapshot.name != manifest["embedding_revision"]:
        raise ValueError("Downloaded model revision differs from the manifest.")
    if snapshot.resolve() != (cache / "snapshots" / manifest["embedding_revision"]).resolve():
        raise ValueError("Downloaded model cache location differs from the validated cache.")
    validate_model_files(manifest, snapshot)
    # Query code uses the repository name, without a revision argument. Point its
    # offline default branch at exactly the validated immutable snapshot.
    reference = cache / "refs/main"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text(manifest["embedding_revision"], encoding="utf-8")


def check_model(manifest, root=ROOT):
    cache = model_cache(manifest)
    if (cache / "refs/main").read_text().strip() != manifest["embedding_revision"]:
        raise ValueError("The offline model reference differs from the pinned revision.")
    validate_model_files(manifest, cache / "snapshots" / manifest["embedding_revision"])
    sys.path.insert(0, str(root / "backend"))
    from core.corpus import load_dataset
    from core.rag.embeddings import embed_query, model_name
    from core.rag.vector_store import FAISSVectorStore

    if model_name() != manifest["embedding_model"]:
        raise ValueError("The configured model differs from the packaged index.")
    load_dataset()
    store, _ = FAISSVectorStore.load(root / "var/index")
    vector = embed_query("Scholarship benefits and application documents")
    if vector.shape != (1, manifest["dimension"]) or store.vectors.shape != (
        manifest["chunk_count"],
        manifest["dimension"],
    ):
        raise ValueError("The offline model and FAISS dimensions disagree.")
    if not store.search(vector, 1):
        raise ValueError("Offline FAISS search returned no evidence.")


def safe_error_message(exc):
    """Expose validation reasons while removing credentials and remote URLs."""
    message = str(exc)
    secrets = {
        value
        for key, value in os.environ.items()
        if value and re.search(r"(?:KEY|TOKEN|PASSWORD|SECRET|CREDENTIAL)", key, re.I)
    }
    if secrets:
        message = re.sub(
            "|".join(re.escape(value) for value in sorted(secrets, key=len, reverse=True)),
            "[redacted]",
            message,
        )
    message = re.sub(r"https?://[^\s]+", "[remote URL redacted]", message)
    message = re.sub(
        r"(?:AIza[0-9A-Za-z_-]{20,}|hf_[0-9A-Za-z]{20,}|sk-[0-9A-Za-z_-]{16,})",
        "[redacted]",
        message,
    )
    message = re.sub(
        r"(?i)\b(?:authorization:\s*bearer\s+|(?:password|token|api[_ -]?key)\s*[:=]\s*)[^\s,;]+",
        "[redacted]",
        message,
    )
    return message


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-model", action="store_true")
    parser.add_argument("--check-model", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest()
    validate_index(manifest)
    if args.download_model:
        download_model(manifest)
    if args.check_model:
        check_model(manifest)
    print(
        f"Deployment index verified: {manifest['chunk_count']} chunks, {manifest['dimension']} dimensions; offline model checked: {args.check_model}."
    )
    return 0


if __name__ == "__main__":
    # Keep downloaded files within the repository cache boundary checked above.
    # The Hub's shared Xet blobs otherwise resolve outside it on Linux.
    os.environ["HF_HUB_DISABLE_SHARED_BLOBS"] = "1"
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            "Deployment asset validation failed: "
            + type(exc).__name__
            + ": "
            + safe_error_message(exc),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
