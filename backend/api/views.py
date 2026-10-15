"""Small REST handlers; business logic remains in application services."""

from core import corpus, memory
from core.schemas import SearchRequest
from django.db import connection
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from api.common import endpoint


@endpoint("POST", SearchRequest)
def scholarship_search(request, payload):
    found = corpus.search(**payload.model_dump())
    return Response(
        {
            "results": [
                {
                    "scheme_id": s["scheme_id"],
                    "name": s["name"],
                    "provider": s["provider"],
                    "objective": s.get("objective"),
                    "citation": corpus.citation(s, s["scheme_id"] + ":record").model_dump(),
                }
                for s in found
            ]
        }
    )


@endpoint("GET")
def scholarship_detail(request, payload, scheme_id):
    try:
        scheme = corpus.detail(scheme_id)
    except ValueError:
        return Response(
            {"error": {"code": "NOT_FOUND", "message": "Scholarship not found."}}, status=404
        )
    return Response(
        {
            "scholarship": scheme,
            "citation": corpus.citation(scheme, scheme_id + ":record").model_dump(),
        }
    )


@endpoint("POST")
def sessions_create(request, payload):
    if request.data:
        raise ValueError("Session creation does not accept profile or other arguments.")
    session, token = memory.create_session()
    return Response({"session_id": str(session.id), "session_token": token}, status=201)


@endpoint(["GET", "DELETE"])
def sessions_detail(request, payload, session_id):
    session = memory.get_session(session_id, request.headers.get("X-Session-Token", ""))
    if request.method == "DELETE":
        session.delete()
        return Response(status=204)
    return Response({"session_id": str(session.id), "context": memory.context(session)})


@endpoint("GET")
def health(request, payload):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    from core.rag.retrieval import index_status

    index = index_status()
    from core.llm import configured_providers

    try:
        providers = configured_providers()
        llm_ready = bool(providers and providers[0].api_key)
    except ValueError:
        llm_ready = False
    return Response(
        {
            "status": "ok",
            "database": connection.vendor,
            "dataset": {"records": len(corpus.records()), "sha256": corpus.fingerprint()},
            "vector_index": index,
            "assistant": "configured" if index["ready"] and llm_ready else "unavailable",
            "llm_configured": llm_ready,
        }
    )


@endpoint("POST", permissions=[IsAdminUser])
def admin_ingest(request, payload):
    from django.core.management import call_command

    call_command("ingest_scholarships")
    return Response({"status": "indexed", "records": len(corpus.records())})


@endpoint("GET", permissions=[IsAdminUser])
def agent_usage(request, payload):
    from apps.navigator.models import LLMUsageLog
    from django.db.models import Sum

    return Response(
        LLMUsageLog.objects.aggregate(
            calls=__import__("django.db.models", fromlist=["Count"]).Count("id"),
            input_tokens=Sum("input_tokens"),
            output_tokens=Sum("output_tokens"),
            total_tokens=Sum("total_tokens"),
            estimated_cost=Sum("estimated_cost"),
        )
    )
