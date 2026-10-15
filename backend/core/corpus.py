"""Read-only corpus access; no derived facts or duplicated source records."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.schemas import Citation

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/scholarship_dataset_ready.json"


@lru_cache(maxsize=1)
def load_dataset() -> dict[str, Any]:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    schemes = data["schemes"]
    ids = [s["scheme_id"] for s in schemes]
    if len(schemes) != data["record_count"] or len(ids) != len(set(ids)):
        raise ValueError("Dataset record count or scheme IDs are invalid.")
    if data["source_record_count"] - data["duplicates_removed"] != len(schemes):
        raise ValueError("Dataset deduplication totals are inconsistent.")
    for scheme in schemes:
        if not all(
            key in scheme for key in ("name", "eligibility", "original_record", "provenance")
        ):
            raise ValueError("A source record is missing required corpus fields.")
    original = json.loads(
        (ROOT / "data/combined_scholarship_schemes_cleaned.json").read_text(encoding="utf-8")
    )["schemes"]
    for scheme in schemes:
        key = scheme["provenance"]["original_record_key"]
        if scheme["original_record"] != original.get(key):
            raise ValueError("Original source record differs from the preserved source corpus.")
    return data


def fingerprint() -> str:
    return hashlib.sha256(DATASET.read_bytes()).hexdigest()


def records(scheme_ids: list[str] | None = None) -> list[dict]:
    schemes = load_dataset()["schemes"]
    if scheme_ids is None:
        return schemes
    unknown = set(scheme_ids) - {s["scheme_id"] for s in schemes}
    if unknown:
        raise ValueError("Unknown scholarship identifiers.")
    return [s for s in schemes if s["scheme_id"] in scheme_ids]


def detail(scheme_id: str) -> dict:
    return records([scheme_id])[0]


def citation(scheme: dict, chunk_id: str) -> Citation:
    source = scheme.get("source") or {}
    return Citation(
        scheme_id=scheme["scheme_id"],
        scheme_name=scheme["name"],
        source_name=source.get("source_name"),
        source_url=source.get("source_url") or None,
        retrieved_from=chunk_id,
        original_record_key=scheme["provenance"].get("original_record_key"),
    )


def search(
    question: str = "",
    scheme_ids: list[str] | None = None,
    category: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    import re

    candidates = records(scheme_ids)
    if category:
        aliases = {
            "sc": "scheduled caste",
            "st": "scheduled tribe",
            "obc": "other backward",
            "ebc": "economically backward",
            "dnt": "denotified",
            "sebc": "socially and educationally backward",
        }
        wanted = category.strip().lower()
        label = aliases.get(wanted, wanted)
        candidates = [
            s
            for s in candidates
            if any(
                re.search(
                    r"\b" + re.escape(term) + r"\b",
                    json.dumps(
                        [s.get("eligibility"), s.get("target_groups"), s.get("tags")]
                    ).lower(),
                )
                for term in (wanted, label)
            )
        ]
    terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    if not terms:
        return candidates[:top_k]
    scored = []
    for s in candidates:
        text = (s["name"] + " " + s.get("search_text", "")).lower()
        score = sum(t in text for t in terms)
        if score:
            scored.append((score, s))
    return [s for _, s in sorted(scored, key=lambda pair: pair[0], reverse=True)[:top_k]]
