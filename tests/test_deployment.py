"""Deployment regression checks: isolation, proxy/CORS, integrity and cache layout."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.db import OperationalError
from django.test import Client, override_settings

from scripts.provision_rag_assets import (
    ROOT,
    download_model,
    load_manifest,
    safe_error_message,
    validate_index,
    validate_model_files,
)


@pytest.mark.parametrize("path", ["/api/health/live", "/health/live"])
def test_liveness_has_no_database_or_generation_dependency(monkeypatch, path):
    connection = Mock()
    connection.cursor.side_effect = OperationalError("synthetic unavailable database")
    monkeypatch.setattr("api.health.connection", connection)
    monkeypatch.setattr(
        "core.llm.grounded_generation", Mock(side_effect=AssertionError("Unexpected Gemini call"))
    )
    monkeypatch.setattr(
        "core.rag.embeddings.get_model", Mock(side_effect=AssertionError("Unexpected model load"))
    )
    response = Client().get(path)
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    connection.cursor.assert_not_called()
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/api/health/ready", "/health/ready"])
def test_readiness_checks_index_and_local_model_without_gemini(monkeypatch, path):
    version = load_manifest()["index_version"]
    monkeypatch.setattr(
        "core.rag.retrieval.index_status", lambda: {"ready": True, "version": version}
    )
    monkeypatch.setattr(
        "core.rag.retrieval.load_store",
        lambda version: SimpleNamespace(vectors=SimpleNamespace(shape=(139, 384))),
    )
    model = Mock()
    model.get_sentence_embedding_dimension.return_value = 384
    loader = Mock(return_value=model)
    monkeypatch.setattr("core.rag.embeddings.get_model", loader)
    monkeypatch.setattr(
        "core.llm.grounded_generation", Mock(side_effect=AssertionError("Unexpected Gemini call"))
    )
    monkeypatch.setattr(
        "core.rag.embeddings.embed_query", Mock(side_effect=AssertionError("Unexpected inference"))
    )
    response = Client().get(path)
    assert response.status_code == 200
    assert all(response.json()["checks"].values())
    assert response.json()["errors"] == []
    assert loader.call_args.kwargs.get("allow_download", False) is False


@pytest.mark.django_db
def test_readiness_failed_dependencies_are_sanitized(monkeypatch):
    connection = Mock()
    connection.cursor.side_effect = OperationalError("synthetic private connection details")
    monkeypatch.setattr("api.health.connection", connection)
    monkeypatch.setattr("core.rag.retrieval.index_status", lambda: {"ready": True, "version": "v"})
    monkeypatch.setattr(
        "core.rag.retrieval.load_store",
        Mock(side_effect=ValueError("synthetic file integrity details")),
    )
    monkeypatch.setattr(
        "core.rag.embeddings.get_model", Mock(side_effect=OSError("synthetic cache details"))
    )
    response = Client().get("/api/health/ready")
    assert response.status_code == 503
    assert set(response.json()["errors"]) == {
        "DATABASE_UNAVAILABLE",
        "VECTOR_UNAVAILABLE",
        "EMBEDDING_UNAVAILABLE",
    }
    assert "synthetic" not in response.content.decode()


def test_https_proxy_and_vercel_session_header_preflight():
    origin = "https://frontend-test.example"
    with override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
        CORS_ALLOWED_ORIGINS=[origin],
    ):
        client = Client()
        secure = client.get("/api/health/live", HTTP_X_FORWARDED_PROTO="https")
        assert secure.status_code == 200 and "Location" not in secure
        assert client.get("/api/health/live").status_code == 301
        preflight = client.options(
            "/api/agent/query",
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,x-session-token,x-request-id",
        )
        assert preflight.status_code == 200
        assert preflight["Access-Control-Allow-Origin"] == origin
        assert all(
            header in preflight["Access-Control-Allow-Headers"]
            for header in ("x-session-token", "x-request-id")
        )
        denied = client.options(
            "/api/agent/query",
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_ORIGIN="https://untrusted-test.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        assert "Access-Control-Allow-Origin" not in denied


def test_collected_static_files_can_be_served_without_frontend_nginx(tmp_path, settings):
    path = tmp_path / "admin/css/base.css"
    path.parent.mkdir(parents=True)
    path.write_text("body { color: black; }")
    middleware = list(settings.MIDDLEWARE)
    middleware.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")
    with override_settings(
        MIDDLEWARE=middleware,
        STATIC_ROOT=tmp_path,
        DEBUG=False,
        WHITENOISE_AUTOREFRESH=False,
        WHITENOISE_USE_FINDERS=False,
        SECURE_SSL_REDIRECT=False,
    ):
        response = Client().get("/static/admin/css/base.css")
        assert response.status_code == 200
        assert b"color: black" in b"".join(response.streaming_content)


def test_packaged_index_is_valid_and_tampering_is_rejected(tmp_path):
    manifest = load_manifest()
    for name in manifest["index_files"]:
        destination = tmp_path / "var/index" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "var/index" / name, destination)
    (tmp_path / "data").mkdir()
    shutil.copyfile(
        ROOT / "data/scholarship_dataset_ready.json",
        tmp_path / "data/scholarship_dataset_ready.json",
    )
    validate_index(manifest, tmp_path)
    vectors = tmp_path / "var/index" / manifest["index_version"] / "vectors.faiss"
    vectors.write_bytes(vectors.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum mismatch"):
        validate_index(manifest, tmp_path)


def test_model_validation_accepts_linux_blob_layout_and_rejects_escape(tmp_path):
    cache = tmp_path / "model"
    snapshot = cache / "snapshots" / ("a" * 40)
    snapshot.mkdir(parents=True)
    blob = cache / "blobs/weights"
    blob.parent.mkdir()
    blob.write_bytes(b"synthetic weights")
    try:
        (snapshot / "model.safetensors").symlink_to(blob)
    except OSError:
        # Windows without symlink privilege still verifies the copied-file path;
        # on Linux the same test exercises the actual HF cache symlink layout.
        shutil.copyfile(blob, snapshot / "model.safetensors")
    manifest = {"model_files": {"model.safetensors": hashlib.sha256(blob.read_bytes()).hexdigest()}}
    validate_model_files(manifest, snapshot)
    malicious = deepcopy(manifest)
    malicious["model_files"] = {"../../../outside": "0" * 64}
    with pytest.raises(ValueError, match="Unsafe"):
        validate_model_files(malicious, snapshot)


def test_model_download_uses_pinned_revision_and_updates_offline_reference(tmp_path, monkeypatch):
    revision = "a" * 40
    snapshot = tmp_path / "snapshots" / revision
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_bytes(b"{}")
    manifest = {
        "embedding_model": "public/test",
        "embedding_revision": revision,
        "model_files": {"config.json": hashlib.sha256(b"{}").hexdigest()},
    }
    downloader = Mock(return_value=str(snapshot))
    monkeypatch.setattr("huggingface_hub.snapshot_download", downloader)
    monkeypatch.setattr("scripts.provision_rag_assets.model_cache", lambda manifest: tmp_path)
    download_model(manifest)
    assert downloader.call_args.kwargs["revision"] == revision
    assert downloader.call_args.kwargs["allow_patterns"] == ["config.json"]
    assert downloader.call_args.kwargs["cache_dir"] == str(tmp_path.parent)
    assert downloader.call_args.kwargs["token"] is False
    assert (tmp_path / "refs/main").read_text() == revision


@pytest.mark.django_db
def test_readiness_detects_missing_files_even_with_a_cached_store(tmp_path, monkeypatch):
    version = "a" * 32
    bundle = tmp_path / version
    bundle.mkdir()
    for name in ("vectors.faiss", "chunks.json", "metadata.json"):
        (bundle / name).write_bytes(b"test file")
    monkeypatch.setattr("core.rag.retrieval.index_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "core.rag.retrieval.index_status", lambda: {"ready": True, "version": version}
    )
    loader = Mock(return_value=SimpleNamespace(vectors=SimpleNamespace(shape=(139, 384))))
    monkeypatch.setattr("core.rag.retrieval.load_store", loader)
    model = Mock()
    model.get_sentence_embedding_dimension.return_value = 384
    monkeypatch.setattr("core.rag.embeddings.get_model", lambda *args: model)
    assert Client().get("/api/health/ready").status_code == 200
    (bundle / "vectors.faiss").unlink()
    response = Client().get("/api/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["vector_index"] is False
    assert "VECTOR_UNAVAILABLE" in response.json()["errors"]
    assert loader.call_count == 1


def test_production_requests_enforce_allowed_hosts():
    with override_settings(
        DEBUG=False,
        SECURE_SSL_REDIRECT=False,
        ALLOWED_HOSTS=["demo.onrender.com"],
    ):
        assert Client().get("/health/live", HTTP_HOST="demo.onrender.com").status_code == 200
        assert Client().get("/health/live", HTTP_HOST="untrusted.example").status_code == 400


@pytest.mark.parametrize("path", ["/health/live", "/health/ready"])
def test_health_routes_do_not_redirect_trailing_slashes(path):
    assert Client().get(path + "/").status_code == 404
    assert Client().post(path).status_code == 405


@pytest.mark.parametrize(
    "key,value,reason",
    [
        ("format_version", 2, "Unsupported deployment asset manifest"),
        ("index_version", "../outside", "Invalid deployment index version"),
        ("embedding_revision", "main", "immutable revision"),
    ],
)
def test_invalid_asset_manifest_is_rejected(tmp_path, key, value, reason):
    manifest = load_manifest()
    manifest[key] = value
    directory = tmp_path / "deploy"
    directory.mkdir()
    (directory / "rag-assets.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=reason):
        load_manifest(tmp_path)


def test_model_checksum_mismatch_names_the_file(tmp_path):
    snapshot = tmp_path / "model/snapshots" / ("a" * 40)
    snapshot.mkdir(parents=True)
    (snapshot / "model.safetensors").write_bytes(b"tampered")
    manifest = {"model_files": {"model.safetensors": hashlib.sha256(b"reviewed").hexdigest()}}
    with pytest.raises(ValueError, match="Pinned model checksum mismatch: model.safetensors"):
        validate_model_files(manifest, snapshot)


def test_model_symlink_outside_repository_is_still_rejected(tmp_path):
    snapshot = tmp_path / "model/snapshots" / ("a" * 40)
    snapshot.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_bytes(b"reviewed")
    try:
        (snapshot / "model.safetensors").symlink_to(outside)
    except OSError:
        pytest.skip("Symlink privilege unavailable; exercised in the Linux container suite.")
    manifest = {"model_files": {"model.safetensors": hashlib.sha256(b"reviewed").hexdigest()}}
    with pytest.raises(ValueError, match="Unsafe model asset path"):
        validate_model_files(manifest, snapshot)


@pytest.mark.parametrize(
    "defect,reason",
    [("revision", "revision differs"), ("checksum", "checksum mismatch"), ("cache_location", "cache location differs")],
)
def test_failed_download_does_not_publish_offline_reference(tmp_path, monkeypatch, defect, reason):
    revision = "a" * 40
    snapshot = tmp_path / "snapshots" / (revision if defect == "checksum" else "b" * 40)
    snapshot.mkdir(parents=True)
    if defect == "cache_location":
        snapshot = tmp_path / "unexpected-cache/snapshots" / revision
        snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_bytes(b"{}")
    reference = tmp_path / "refs/main"
    reference.parent.mkdir()
    reference.write_text("previous-reviewed-revision")
    manifest = {
        "embedding_model": "public/test",
        "embedding_revision": revision,
        "model_files": {
            "config.json": hashlib.sha256(b"{}" if defect == "cache_location" else b"other bytes").hexdigest()
        },
    }
    monkeypatch.setattr("huggingface_hub.snapshot_download", Mock(return_value=str(snapshot)))
    monkeypatch.setattr("scripts.provision_rag_assets.model_cache", lambda manifest: tmp_path)
    with pytest.raises(ValueError, match=reason):
        download_model(manifest)
    assert reference.read_text() == "previous-reviewed-revision"


def test_cli_reports_the_validation_reason(tmp_path):
    directory = tmp_path / "scripts"
    directory.mkdir()
    script = directory / "provision_rag_assets.py"
    script.write_bytes((ROOT / "scripts/provision_rag_assets.py").read_bytes())
    (tmp_path / "deploy").mkdir()
    (tmp_path / "deploy/rag-assets.json").write_text('{"format_version": 2}', encoding="utf-8")
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert result.returncode == 1
    assert result.stderr.strip() == (
        "Deployment asset validation failed: ValueError: Unsupported deployment asset manifest."
    )


def test_error_diagnostics_redact_credentials_and_signed_urls(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-private-key")
    monkeypatch.setenv("MYSQL_PASSWORD", "synthetic-private-password")
    message = safe_error_message(
        ValueError(
            "Pinned model checksum mismatch: model.safetensors "
            "synthetic-private-key synthetic-private-password "
            "https://provider.example/model?signature=private-signed-value "
            "Authorization: Bearer synthetic-private-token"
        )
    )
    assert "Pinned model checksum mismatch: model.safetensors" in message
    for secret in (
        "synthetic-private-key",
        "synthetic-private-password",
        "private-signed-value",
        "synthetic-private-token",
    ):
        assert secret not in message


def test_query_model_loading_never_downloads(monkeypatch):
    from core.rag.embeddings import get_model

    loader = Mock()
    monkeypatch.setitem(
        sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=loader)
    )
    get_model.cache_clear()
    try:
        get_model(load_manifest()["embedding_model"])
        assert loader.call_args.kwargs == {"device": "cpu", "local_files_only": True}
    finally:
        get_model.cache_clear()


@pytest.mark.skipif(shutil.which("sh") is None, reason="Production entrypoint is tested in Linux.")
@pytest.mark.parametrize("fail_migrations", [False, True])
def test_entrypoint_respects_port_and_stops_on_migration_failure(tmp_path, fail_migrations):
    binary = tmp_path / "bin"
    binary.mkdir()
    logger = '#!/bin/sh\nprintf "%s\\n" "$*" >> "$STARTUP_LOG"\n'
    python = binary / "python"
    python.write_text(logger + 'if [ "$FAIL_MIGRATIONS" = "true" ]; then exit 7; fi\n')
    gunicorn = binary / "gunicorn"
    gunicorn.write_text(logger)
    python.chmod(0o755)
    gunicorn.chmod(0o755)
    log = tmp_path / "startup.log"
    environment = os.environ.copy()
    environment.update(
        PATH=str(binary) + os.pathsep + environment["PATH"],
        STARTUP_LOG=str(log),
        PORT="10000",
        GUNICORN_WORKERS="1",
        GUNICORN_THREADS="2",
        FAIL_MIGRATIONS="true" if fail_migrations else "false",
    )
    result = subprocess.run(["sh", str(ROOT / "backend/entrypoint.sh")], env=environment)
    lines = log.read_text().splitlines()
    if fail_migrations:
        assert result.returncode == 7
        assert lines == ["backend/manage.py migrate --noinput"]
    else:
        assert result.returncode == 0
        assert lines[:3] == [
            "backend/manage.py migrate --noinput",
            "backend/manage.py seed_scholarships",
            "backend/manage.py collectstatic --noinput",
        ]
        assert "config.wsgi:application --bind 0.0.0.0:10000 --workers 1 --threads 2" in lines[3]


@pytest.mark.parametrize(
    "name", ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"]
)
def test_diagnostics_preserve_safe_tokenizer_filenames(name):
    reason = "Pinned model checksum mismatch: " + name
    assert safe_error_message(ValueError(reason)) == reason
