import asyncio
import json
from types import SimpleNamespace

import pytest
from core import corpus
from core.rag.documents import prepare_documents
from core.schemas import ScholarshipAnswer
from pydantic import ValidationError

from evaluation.ragas_eval import collect, load_dataset, provenance_checks, score_result
from evaluation.schemas import (
    METRICS,
    EvaluationResult,
    MetricResult,
    context_text,
)

ROOT = corpus.ROOT


def dataset():
    return load_dataset(ROOT / "evaluation/ragas_cases.json")


def result_fixture():
    sample = next(s for s in dataset().samples if s.id == "pragati_source")
    chunk = next(c for c in prepare_documents() if c.chunk_id == sample.reference_chunk_ids[0])
    return EvaluationResult(
        id=sample.id,
        category=sample.category,
        question=sample.question,
        reference=sample.reference,
        expected_scheme_ids=sample.expected_scheme_ids,
        reference_contexts=sample.reference_contexts,
        response=ScholarshipAnswer(
            answer="The source describes this scholarship's benefits.",
            status="success",
            sources=[dict(chunk.citation, excerpt=chunk.text)],
        ),
        retrieved_chunks=[chunk],
        retrieved_contexts=[context_text(chunk)],
        retrieval_scores={chunk.chunk_id: 0.8},
        top_k=8,
        retrieval_latency_ms=1,
        total_latency_ms=2,
        retrieval_calls=1,
        checks={"provenance_traceable": True},
        metrics={name: MetricResult(status="skipped", explanation="pending") for name in METRICS},
    )


def test_benchmark_covers_corpus_and_required_categories():
    data = dataset()
    assert len(data.samples) == 27
    assert {sid for s in data.samples for sid in s.expected_scheme_ids} == {
        s["scheme_id"] for s in corpus.records()
    }
    assert {s.category for s in data.samples} == {
        "direct",
        "eligibility",
        "benefits",
        "application",
        "documents",
        "multi_condition",
        "multi_chunk",
        "multi_scheme",
        "ambiguous",
        "out_of_domain",
        "unavailable",
        "provenance",
    }
    assert all(s.reference_contexts for s in data.samples if s.score_ragas)


@pytest.mark.parametrize(
    "change",
    [
        "stale_corpus",
        "wrong_chunk",
        "wrong_context",
        "unknown_scheme",
        "duplicate_id",
        "wrong_reference",
    ],
)
def test_dataset_rejects_untraceable_references(tmp_path, change):
    raw = json.loads((ROOT / "evaluation/ragas_cases.json").read_text(encoding="utf-8"))
    if change == "stale_corpus":
        raw["corpus_sha256"] = "0" * 64
    if change == "wrong_chunk":
        raw["samples"][0]["reference_chunk_ids"][0] = "missing"
    if change == "wrong_reference":
        raw["samples"][0]["reference"] = "An invented scholarship amount."
    if change == "wrong_context":
        raw["samples"][0]["reference_contexts"][0] = "invented fact"
    if change == "unknown_scheme":
        raw["samples"][0]["expected_scheme_ids"] = ["missing"]
    if change == "duplicate_id":
        raw["samples"][1]["id"] = raw["samples"][0]["id"]
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        load_dataset(path)


def test_evaluation_result_roundtrip_and_context_integrity():
    result = result_fixture()
    assert EvaluationResult.model_validate_json(result.model_dump_json()) == result
    raw = result.model_dump()
    with pytest.raises(ValidationError):
        EvaluationResult.model_validate(dict(raw, retrieved_contexts=["invented"]))
    with pytest.raises(ValidationError):
        EvaluationResult.model_validate(dict(raw, retrieval_scores={"missing": 0.9}))
    with pytest.raises(ValidationError):
        EvaluationResult.model_validate(
            dict(raw, retrieval_scores={result.retrieved_chunks[0].chunk_id: float("nan")})
        )
    with pytest.raises(ValidationError):
        MetricResult(status="ok", score=float("nan"))
    with pytest.raises(ValidationError):
        MetricResult(status="error", score=1, error={"code": "BAD", "message": "Failed"})


def test_citation_provenance_checks_original_record_and_actual_chunk():
    result = result_fixture()
    assert provenance_checks(result.response, result.retrieved_chunks)
    result.response.sources[0].original_record_key = "invented"
    assert not provenance_checks(result.response, result.retrieved_chunks)
    assert not provenance_checks(result.response, [])


@pytest.mark.django_db(transaction=True)
def test_evaluation_uses_actual_workflow_trace_once_and_cleans_session(monkeypatch):
    from apps.navigator.models import AgentExecution, UserSession
    from core.agent.tools import Tool
    from core.llm import Generation
    from core.schemas import RetrievalRequest

    sample = next(s for s in dataset().samples if s.id == "pragati_source")
    chunk = next(c for c in prepare_documents() if c.chunk_id == sample.reference_chunk_ids[0])
    calls = []

    def retrieve(payload):
        calls.append(payload.question)
        return {
            "chunks": [chunk],
            "scores": {chunk.chunk_id: 0.9},
            "warnings": [],
            "metrics": {"retrieved_chunk_count": 1},
            "timings_ms": {"retrieval_total": 3},
        }

    class Provider:
        name = "gemini"
        model = "test-model"

        def generate(self, context):
            raw = (
                {"notes_examined": [], "supported": True, "issues": []}
                if context.get("task") == "verify_grounding"
                else {
                    "answer": "The scholarship benefits are described in the source.",
                    "status": "success",
                    "supports": [{"chunk_id": chunk.chunk_id, "quote": chunk.text}],
                }
            )
            return Generation(json.dumps(raw), 10, 5)

    monkeypatch.setattr(
        "core.agent.workflow.classify_query",
        lambda q: {"out_of_scope": False, "intent": "benefits", "sections": ["benefits"]},
    )
    monkeypatch.setattr(
        "core.agent.workflow.RETRIEVAL_TOOL",
        Tool("scholarship_retrieval", RetrievalRequest, retrieve),
    )
    monkeypatch.setattr("core.llm.configured_providers", lambda: [Provider()])
    before = UserSession.objects.count()
    result = collect(sample, "test-run")
    assert len(calls) == 1 and result.retrieved_chunks == [chunk]
    assert result.retrieval_latency_ms == 3 and result.retrieval_scores[chunk.chunk_id] == 0.9
    assert result.retrieval_calls == 1 and len(result.llm_usage) == 2
    assert result.response.status == "success" and all(result.checks.values())
    assert UserSession.objects.count() == before
    assert AgentExecution.objects.get(request_id=result.response.request_id).session is None


def test_scoring_failure_is_explicit_not_a_zero_or_perfect_score():
    result = result_fixture()
    sample = next(s for s in dataset().samples if s.id == result.id)

    class FailingMetric:
        async def ascore(self, **kwargs):
            raise RuntimeError("private-provider-detail")

    # Optional metric adapters are imported only by explicit offline scoring.
    pytest.importorskip("ragas")
    asyncio.run(
        score_result(
            result, sample, {name: FailingMetric() for name in METRICS}, SimpleNamespace(usage=[])
        )
    )
    assert all(m.status == "error" and m.score is None for m in result.metrics.values())
    assert "private-provider-detail" not in result.model_dump_json()


def test_off_domain_scoring_skips_every_judge():
    pytest.importorskip("ragas")
    result = result_fixture()
    sample = next(s for s in dataset().samples if s.category == "out_of_domain")
    result.response = ScholarshipAnswer(
        answer="Scholarship help only.", status="out_of_scope", sources=[]
    )
    result.retrieved_chunks = []
    result.retrieved_contexts = []
    result.retrieval_scores = {}
    asyncio.run(score_result(result, sample, {}, SimpleNamespace(usage=[])))
    assert all(m.status == "skipped" and m.score is None for m in result.metrics.values())


def test_lock_capture_preserves_optional_provider_extras():
    from packaging.requirements import Requirement

    from scripts.lock_dependencies import capture

    distributions = {
        "adapter": SimpleNamespace(version="1.0", requires=['provider>=1; extra == "google"']),
        "provider": SimpleNamespace(version="2.0", requires=[]),
    }
    pins, _ = capture([Requirement("adapter[google]>=1")], distributions.__getitem__)
    assert pins == {"adapter": "1.0", "provider": "2.0"}


def test_ragas_nonfinite_score_has_no_fabricated_value():
    pytest.importorskip("ragas")
    result = result_fixture()
    sample = next(s for s in dataset().samples if s.id == result.id)

    class UndefinedMetric:
        async def ascore(self, **kwargs):
            return SimpleNamespace(value=float("nan"))

    asyncio.run(
        score_result(
            result, sample, {name: UndefinedMetric() for name in METRICS}, SimpleNamespace(usage=[])
        )
    )
    assert all(
        m.status == "error" and m.score is None and m.error.code == "RAGAS_SCORE_UNDEFINED"
        for m in result.metrics.values()
    )


def test_only_transient_application_failures_are_retried():
    from evaluation.ragas_eval import transient_failure

    row = result_fixture()
    for code in ("LLM_RATE_LIMITED", "LLM_TIMEOUT", "LLM_NETWORK_ERROR"):
        row.response = ScholarshipAnswer(
            answer="Provider failure",
            status="error",
            sources=[],
            error={"code": code, "message": "Unavailable"},
        )
        assert transient_failure(row)
    row.response = ScholarshipAnswer(
        answer="Rejected",
        status="error",
        sources=[],
        error={"code": "LLM_RESPONSE_REJECTED", "message": "Unsupported"},
    )
    assert not transient_failure(row)


def test_summary_counts_preserved_failed_attempt_usage():
    from evaluation.ragas_eval import summarize
    from evaluation.schemas import ProviderUsage

    row = result_fixture()
    row.llm_usage = [
        ProviderUsage(
            model="test",
            phase="generation",
            status="SUCCESS",
            input_tokens=10,
            output_tokens=5,
            latency_ms=1,
        )
    ]
    old = row.model_copy(deep=True)
    old.llm_usage[0].status = "FAILED"
    summary = summarize(SimpleNamespace(results=[row], previous_attempts=[old]))
    assert summary["questions"] == 1 and summary["previous_failed_attempts"] == 1
    assert summary["application_usage"]["calls"] == 2
    assert summary["application_usage"]["input_tokens"] == 20


def test_installed_ragas_metrics_compute_scores_with_structured_judgments(monkeypatch):
    # Synthetic judge responses exercise the actual installed RAGAS algorithms,
    # not a replacement metric. They are never used in saved/live benchmark reports.
    pytest.importorskip("ragas")
    import numpy as np
    from ragas.llms.base import InstructorBaseRagasLLM

    from evaluation.ragas_adapter import build_metrics

    monkeypatch.setattr(
        "evaluation.ragas_adapter.embed_query", lambda text: np.array([[1, 0]], dtype="float32")
    )

    class Judge(InstructorBaseRagasLLM):
        usage = []

        def generate(self, prompt, response_model):
            outputs = {
                "StatementGeneratorOutput": {
                    "statements": ["Supported claim", "Unsupported claim"]
                },
                "NLIStatementOutput": {
                    "statements": [
                        {"statement": "Supported claim", "reason": "Present", "verdict": 1},
                        {"statement": "Unsupported claim", "reason": "Absent", "verdict": 0},
                    ]
                },
                "AnswerRelevanceOutput": {
                    "question": "What benefits are provided?",
                    "noncommittal": 0,
                },
                "ContextPrecisionOutput": {"reason": "Relevant", "verdict": 1},
                "ContextRecallOutput": {
                    "classifications": [
                        {
                            "statement": "First reference claim",
                            "reason": "Present",
                            "attributed": 1,
                        },
                        {
                            "statement": "Second reference claim",
                            "reason": "Absent",
                            "attributed": 0,
                        },
                    ]
                },
            }
            return response_model.model_validate(outputs[response_model.__name__])

        async def agenerate(self, prompt, response_model):
            return self.generate(prompt, response_model)

    row = result_fixture()
    sample = next(s for s in dataset().samples if s.id == row.id)
    judge = Judge()
    asyncio.run(score_result(row, sample, build_metrics(judge), judge))
    assert row.metrics["faithfulness"].score == 0.5
    assert row.metrics["context_recall"].score == 0.5
    assert row.metrics["context_precision"].score == pytest.approx(1)
    assert row.metrics["answer_relevancy"].score == pytest.approx(1)


@pytest.mark.parametrize(
    "text, status", [("not JSON", "FAILED"), ('{"answer":"Valid structured output"}', "SUCCESS")]
)
def test_judge_adapter_records_actual_usage_and_sanitizes_errors(monkeypatch, text, status):
    pytest.importorskip("ragas")
    from pydantic import BaseModel

    from evaluation.ragas_adapter import GeminiJudge

    class Output(BaseModel):
        answer: str

    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            text=text,
            usage_metadata=SimpleNamespace(prompt_token_count=7, candidates_token_count=3),
        )

    client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content), close=lambda: None
    )
    monkeypatch.setattr("evaluation.ragas_adapter.genai.Client", lambda **kwargs: client)
    judge = GeminiJudge("configured-model", "fake-private-marker", delay=0)
    if status == "FAILED":
        with pytest.raises(RuntimeError, match="RAGAS_JUDGE_REQUEST_FAILED"):
            judge.generate("Offline metric prompt", Output)
    else:
        assert judge.generate("Offline metric prompt", Output).answer == "Valid structured output"
    assert len(calls) == 1 and calls[0]["model"] == "configured-model"
    assert calls[0]["config"].response_json_schema == Output.model_json_schema()
    assert judge.usage[0].input_tokens == 7 and judge.usage[0].output_tokens == 3
    assert judge.usage[0].status == status
    assert "fake-private-marker" not in judge.usage[0].model_dump_json()
    judge.close()


def test_offline_judge_does_not_retry_daily_exhaustion(monkeypatch):
    pytest.importorskip("ragas")
    from google.genai import errors
    from pydantic import BaseModel

    from evaluation.ragas_adapter import GeminiJudge

    class Output(BaseModel):
        answer: str

    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs)
        raise errors.APIError(
            429,
            {
                "error": {
                    "message": "SECRET",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                            "violations": [
                                {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}
                            ],
                        }
                    ],
                }
            },
        )

    client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content), close=lambda: None
    )
    monkeypatch.setattr("evaluation.ragas_adapter.genai.Client", lambda **kwargs: client)
    judge = GeminiJudge("test", "fake-key", delay=0)
    with pytest.raises(RuntimeError, match="RAGAS_JUDGE_REQUEST_FAILED"):
        judge.generate("Synthetic offline prompt", Output)
    assert len(calls) == 1 and judge.usage[0].error_code == "LLM_QUOTA_EXHAUSTED"
    assert judge.usage[0].input_tokens is None and judge.usage[0].status == "FAILED"
    assert "SECRET" not in judge.usage[0].model_dump_json()
    judge.close()


def test_offline_judge_preserves_transient_attempt_and_backoff(monkeypatch):
    pytest.importorskip("ragas")
    from google.genai import errors
    from pydantic import BaseModel

    from evaluation.ragas_adapter import GeminiJudge

    class Output(BaseModel):
        answer: str

    calls, sleeps = [], []

    def generate_content(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise errors.APIError(503, {"error": {"message": "SECRET"}})
        return SimpleNamespace(
            text='{ "answer": "Structured judgment" }',
            usage_metadata=SimpleNamespace(prompt_token_count=7, candidates_token_count=3),
        )

    client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content), close=lambda: None
    )
    monkeypatch.setattr("evaluation.ragas_adapter.genai.Client", lambda **kwargs: client)
    monkeypatch.setattr("evaluation.ragas_adapter.time.sleep", sleeps.append)
    judge = GeminiJudge("test", "fake-key", delay=0)
    assert judge.generate("Synthetic prompt", Output).answer == "Structured judgment"
    assert len(calls) == 2 and 10 in sleeps
    assert [u.status for u in judge.usage] == ["FAILED", "SUCCESS"]
    assert judge.usage[0].error_code == "LLM_PROVIDER_UNAVAILABLE"
    assert judge.usage[1].input_tokens == 7
    judge.close()
