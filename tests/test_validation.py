import pytest
from core.rag.documents import Chunk, prepare_documents
from core.schemas import Citation, QueryRequest, ScholarshipAnswer
from pydantic import ValidationError


@pytest.mark.parametrize(
    "payload",
    [
        {"question": " "},
        {"question": 12},
        {"question": "q" * 2001},
        {"question": "benefits", "top_k": True},
        {"question": "benefits", "top_k": "8"},
        {"question": "benefits", "top_k": 0},
        {"question": "benefits", "top_k": 17},
        {"question": "benefits", "scheme_ids": [""]},
        {"question": "benefits", "scheme_ids": ["a", "a"]},
        {"question": "benefits", "scheme_ids": ["a" * 201]},
        {"question": "benefits", "profile": {"income": 1}},
    ],
)
def test_request_rejects_malformed_data(payload):
    with pytest.raises(ValidationError):
        QueryRequest.model_validate(payload)


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "file:///private/key", "https://user:password@example.com", "invalid"],
)
def test_citation_rejects_unsafe_source_urls(url):
    with pytest.raises(ValidationError):
        Citation(
            scheme_id="a", scheme_name="Scheme A", retrieved_from="a:benefits:0", source_url=url
        )


def test_chunk_rejects_mismatched_provenance_and_empty_content():
    chunk = prepare_documents()[0].to_dict()
    wrong = dict(chunk, citation=dict(chunk["citation"], scheme_id="other"))
    with pytest.raises(ValidationError):
        Chunk(**wrong)
    with pytest.raises(ValidationError):
        Chunk(**dict(chunk, text=" "))
    with pytest.raises(ValidationError):
        Chunk(**dict(chunk, section="invented"))


@pytest.mark.parametrize(
    "payload",
    [
        {"answer": " ", "status": "out_of_scope", "sources": []},
        {"answer": "A claim", "status": "success", "sources": []},
        {"answer": "Failed", "status": "error", "sources": []},
        {
            "answer": "Redirect",
            "status": "out_of_scope",
            "sources": [],
            "error": {"code": "BAD", "message": "failed"},
        },
    ],
)
def test_response_rejects_inconsistent_status(payload):
    with pytest.raises(ValidationError):
        ScholarshipAnswer.model_validate(payload)


def test_response_sources_require_actual_excerpts():
    chunk = prepare_documents()[0]
    with pytest.raises(ValidationError):
        ScholarshipAnswer(answer="Claim", status="success", sources=[chunk.citation])
    cited = dict(chunk.citation, excerpt=chunk.text[:40])
    answer = ScholarshipAnswer(answer="Claim", status="success", sources=[cited])
    assert ScholarshipAnswer.model_validate_json(answer.model_dump_json()) == answer
    with pytest.raises(ValidationError):
        ScholarshipAnswer(answer="Redirect", status="out_of_scope", sources=[cited])
