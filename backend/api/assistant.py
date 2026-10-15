from core import corpus, memory
from core.agent.workflow import query
from core.schemas import QueryRequest, ScholarshipAnswer
from rest_framework.response import Response

from api.common import endpoint


def execute(request, payload):
    if payload.scheme_ids is not None:
        corpus.records(payload.scheme_ids)
    if payload.context_scheme_id:
        corpus.detail(payload.context_scheme_id)
    session = (
        memory.get_session(payload.session_id, request.headers.get("X-Session-Token", ""))
        if payload.session_id
        else None
    )
    answer = query(payload, request.request_id, session)
    return Response(answer.model_dump(), status=503 if answer.status == "error" else 200)


@endpoint("POST", QueryRequest, response_schema=ScholarshipAnswer.model_json_schema())
def agent_query(request, payload):
    return execute(request, payload)


@endpoint("POST", QueryRequest, response_schema=ScholarshipAnswer.model_json_schema())
def rag_query(request, payload):
    return execute(request, payload)
