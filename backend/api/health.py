"""Deployment probes with no Gemini request or user-query execution."""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def live(request):
    # Plain Django avoids API authentication/throttling and database dependencies.
    response = JsonResponse({"status": "ok"})
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def ready(request):
    from core.rag.embeddings import get_model, model_name
    from core.rag.retrieval import index_dir, index_status, load_store

    checks = {"database": False, "vector_index": False, "embedding_model": False}
    errors = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = cursor.fetchone() == (1,)
            if not checks["database"]:
                errors.append("DATABASE_UNAVAILABLE")
    except Exception:
        errors.append("DATABASE_UNAVAILABLE")
    dimension = None
    try:
        state = index_status()
        directory = index_dir() / state.get("version", "")
        present = all(
            (directory / name).is_file()
            for name in ("vectors.faiss", "chunks.json", "metadata.json")
        )
        if state["ready"] and present:
            store = load_store(state["version"])
            dimension = store.vectors.shape[1]
            checks["vector_index"] = True
        else:
            errors.append("VECTOR_UNAVAILABLE")
    except Exception:
        errors.append("VECTOR_UNAVAILABLE")
    try:
        model = get_model(model_name())
        checks["embedding_model"] = (
            dimension is not None and model.get_sentence_embedding_dimension() == dimension
        )
        if not checks["embedding_model"]:
            errors.append("EMBEDDING_UNAVAILABLE")
    except Exception:
        errors.append("EMBEDDING_UNAVAILABLE")
    successful = all(checks.values())
    response = JsonResponse(
        {"status": "ready" if successful else "unavailable", "checks": checks, "errors": errors},
        status=200 if successful else 503,
    )
    response["Cache-Control"] = "no-store"
    return response
