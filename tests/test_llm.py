"""Gemini wire compatibility and safe, actionable failure diagnostics."""

import json
from types import SimpleNamespace

import httpx
import pytest
from apps.navigator.models import AgentExecution
from core.llm import GeminiProvider, GroqProvider, grounded_generation, validate_draft
from google import genai
from google.genai import errors
from pydantic import ValidationError

pytestmark = pytest.mark.django_db


def test_gemini_sends_json_schema_and_preserves_strict_local_validation(monkeypatch):
    chunk = SimpleNamespace(chunk_id="probe:documents", text="Required: Aadhaar Card.", citation={})
    draft = {
        "answer": "You need an Aadhaar Card.",
        "status": "success",
        "supports": [{"chunk_id": chunk.chunk_id, "quote": chunk.text}],
    }
    requests = []

    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        config = body["generationConfig"]
        assert "responseSchema" not in config
        schema = config["responseJsonSchema"]
        assert schema["additionalProperties"] is False
        assert schema["$defs"]["Quote"]["additionalProperties"] is False
        assert "additional_properties" not in json.dumps(body)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"role": "model", "parts": [{"text": json.dumps(draft)}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 8},
            },
        )

    real_client = genai.Client

    def client_with_transport(**kwargs):
        kwargs["http_options"].client_args = {"transport": httpx.MockTransport(handle)}
        return real_client(**kwargs)

    monkeypatch.setattr(genai, "Client", client_with_transport)
    result = GeminiProvider("gemini-test", "dummy-test-key").generate({"question": "Documents?"})
    assert len(requests) == 1
    assert validate_draft(result.text, [chunk]).supports[0].quote == chunk.text
    assert (result.input_tokens, result.output_tokens) == (10, 8)
    with pytest.raises(ValidationError):
        validate_draft(json.dumps(dict(draft, invented_status="ELIGIBLE")), [chunk])
    with pytest.raises(ValidationError):
        invalid = dict(draft, supports=[dict(draft["supports"][0], extra="unsupported")])
        validate_draft(json.dumps(invalid), [chunk])


def test_groq_sends_json_and_preserves_strict_local_validation(monkeypatch):
    import groq

    chunk = SimpleNamespace(chunk_id="probe:documents", text="Required: Aadhaar Card.", citation={})
    draft = {
        "answer": "You need an Aadhaar Card.",
        "status": "success",
        "supports": [{"chunk_id": chunk.chunk_id, "quote": chunk.text}],
    }
    requests = []

    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": json.dumps(draft)},
                        "finish_reason": "stop",
                        "index": 0,
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 10},
            },
        )

    real_groq = groq.Groq

    def groq_with_transport(**kwargs):
        kwargs["http_client"] = httpx.Client(transport=httpx.MockTransport(handle))
        return real_groq(**kwargs)

    monkeypatch.setattr(groq, "Groq", groq_with_transport)
    result = GroqProvider("llama-3.3-70b-versatile", "dummy-groq-key").generate({"question": "Documents?"})
    assert len(requests) == 1
    assert validate_draft(result.text, [chunk]).supports[0].quote == chunk.text
    assert (result.input_tokens, result.output_tokens) == (12, 10)


@pytest.mark.parametrize(
    "status, expected",
    [
        (400, "LLM_REQUEST_INVALID"),
        (401, "LLM_AUTH_FAILED"),
        (403, "LLM_AUTH_FAILED"),
        (404, "LLM_MODEL_UNAVAILABLE"),
        (429, "LLM_RATE_LIMITED"),
        (503, "LLM_PROVIDER_UNAVAILABLE"),
    ],
)
def test_provider_errors_are_distinct_and_never_expose_details(status, expected, caplog):
    class Broken:
        name, model = "gemini", "test"
        calls = 0

        def generate(self, context):
            self.calls += 1
            raise errors.APIError(
                status, {"error": {"message": "SECRET credential and user profile"}}
            )

    provider = Broken()
    execution = AgentExecution.objects.create(request_id="diagnostics-test")
    draft, warnings, _ = grounded_generation({}, [], execution, [provider])
    assert draft is None
    assert all(w["code"] == expected for w in warnings)
    assert provider.calls == (2 if status == 429 or status >= 500 else 1)
    assert execution.llm_calls.count() == provider.calls
    assert "SECRET" not in json.dumps(warnings)
    for record in caplog.records:
        assert "SECRET" not in str(getattr(record, "details", {}))


def test_timeout_has_separate_warning_and_one_retry():
    class Slow:
        name, model = "gemini", "test"
        calls = 0

        def generate(self, context):
            self.calls += 1
            raise httpx.ReadTimeout("SECRET request URL")

    provider = Slow()
    execution = AgentExecution.objects.create(request_id="timeout-test")
    draft, warnings, _ = grounded_generation({}, [], execution, [provider])
    assert draft is None and provider.calls == 2
    assert {w["code"] for w in warnings} == {"LLM_TIMEOUT"}
    assert "SECRET" not in json.dumps(warnings)


def test_transient_review_retries_same_phase_with_exponential_backoff(monkeypatch):
    from apps.navigator.models import LLMUsageLog
    from core.llm import DIAGNOSTICS, Generation

    chunk = SimpleNamespace(chunk_id="source:0", text="An annual award.", citation={})
    phases, sleeps, diagnostics = [], [], []
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("LLM_RETRY_BASE_SECONDS", "5")
    monkeypatch.setattr("core.llm.time.sleep", sleeps.append)

    class Recovering:
        name, model = "gemini", "test"

        def generate(self, context):
            phase = context.get("task", "generation")
            phases.append(phase)
            if phase == "generation":
                return Generation(
                    json.dumps(
                        {
                            "answer": "An annual award.",
                            "status": "success",
                            "supports": [{"chunk_id": chunk.chunk_id, "quote": chunk.text}],
                        }
                    ),
                    10,
                    5,
                )
            if phases.count(phase) < 3:
                raise errors.APIError(429, {"error": {"message": "SECRET"}})
            return Generation('{"supported":true,"issues":[],"notes_examined":[]}', 7, 3)

    execution = AgentExecution.objects.create(request_id="backoff-review")
    token = DIAGNOSTICS.set(diagnostics)
    try:
        draft, warnings, _ = grounded_generation({}, [chunk], execution, [Recovering()])
    finally:
        DIAGNOSTICS.reset(token)
    assert draft is not None and not warnings
    assert phases == ["generation", "verify_grounding", "verify_grounding", "verify_grounding"]
    assert sleeps == [5, 10]
    assert list(
        LLMUsageLog.objects.filter(execution=execution).values_list("status", flat=True)
    ) == ["SUCCESS", "FAILED", "FAILED", "SUCCESS"]
    assert (
        sum(
            d.get("error_code") == "LLM_RATE_LIMITED" and "backoff_seconds" not in d
            for d in diagnostics
        )
        == 2
    )
    assert "SECRET" not in json.dumps(diagnostics)


def test_source_aliases_expand_only_known_ids_without_changing_quotes(monkeypatch):
    chunks = [SimpleNamespace(chunk_id="long-original-source:0", text="Exact fact.", citation={})]
    requests = []

    def generate_content(**kwargs):
        requests.append(kwargs)
        wire = json.loads(kwargs["contents"])
        assert wire["sources"][0]["chunk_id"] == "s1"
        assert wire["sources"][0]["text"] == chunks[0].text
        assert kwargs["config"].response_json_schema["$defs"]["Quote"]["properties"]["chunk_id"][
            "enum"
        ] == ["s1"]
        return SimpleNamespace(
            text=json.dumps(
                {
                    "answer": "Exact fact.",
                    "status": "success",
                    "supports": [{"chunk_id": "s1", "quote": "Exact fact."}],
                }
            ),
            usage_metadata=None,
        )

    client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content), close=lambda: None
    )
    monkeypatch.setattr(genai, "Client", lambda **kwargs: client)
    provider = GeminiProvider("test", "fake-secret")
    result = provider.generate(
        {"sources": [{"chunk_id": chunks[0].chunk_id, "text": chunks[0].text}]}
    )
    assert validate_draft(result.text, chunks).supports[0].chunk_id == chunks[0].chunk_id
    assert validate_draft(result.text, chunks).answer == "Exact fact."
    provider.close()


def test_invalid_facts_cannot_reach_a_fallback_provider():
    from core.llm import Generation

    class Invalid:
        name, model = "gemini", "test"
        calls = 0

        def generate(self, context):
            self.calls += 1
            return Generation('{"answer":"Invented","status":"success","supports":[]}', 10, 3)

    first, fallback = Invalid(), Invalid()
    execution = AgentExecution.objects.create(request_id="no-quality-fallback")
    draft, warnings, _ = grounded_generation({}, [], execution, [first, fallback])
    assert draft is None and first.calls == 1 and fallback.calls == 0
    assert warnings[-1]["code"] == "LLM_RESPONSE_REJECTED"


def test_only_verified_metadata_counts_are_allowed_not_unsupported_years():
    chunks = [
        SimpleNamespace(
            chunk_id=f"scheme-{i}", scheme_id=f"scheme-{i}", text="Girl students.", citation={}
        )
        for i in range(3)
    ]
    data = {
        "answer": "These three schemes support girl students.",
        "status": "success",
        "supports": [{"chunk_id": c.chunk_id, "quote": c.text} for c in chunks],
    }
    assert validate_draft(json.dumps(data), chunks).status == "success"
    for answer in (
        "These two schemes support girls.",
        "The award lasts three years.",
        "It pays three lakh.",
        "Students may receive three scholarships.",
        "The knowledge base contains only three schemes.",
    ):
        with pytest.raises(ValueError):
            validate_draft(json.dumps(dict(data, answer=answer)), chunks)


def test_review_cannot_claim_it_examined_an_unknown_note():
    from core.llm import GroundingRejected, validate_review

    with pytest.raises(GroundingRejected):
        validate_review(
            '{"supported":true,"issues":[],"notes_examined":["invented:0"]}', {"sources": []}
        )


def test_retry_budget_stops_before_exceeding_browser_timeout(monkeypatch):
    from core.llm import DEADLINE, provider_call

    clocks = [0.0]

    def sleep(seconds):
        clocks[0] += seconds

    monkeypatch.setattr("core.llm.time.monotonic", lambda: clocks[0])
    monkeypatch.setattr("core.llm.time.sleep", sleep)
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("LLM_RETRY_BASE_SECONDS", "5")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "30")

    class Unavailable:
        name, model = "gemini", "test"
        calls = 0

        def generate(self, context):
            self.calls += 1
            clocks[0] += 30
            raise httpx.ReadTimeout("private-detail")

    provider = Unavailable()
    execution = AgentExecution.objects.create(request_id="total-retry-budget")
    token = DEADLINE.set(90)
    try:
        with pytest.raises(httpx.ReadTimeout):
            provider_call(provider, {}, execution, "generation", lambda t: t)
    finally:
        DEADLINE.reset(token)
    assert provider.calls == 2 and clocks[0] == 65
    assert execution.llm_calls.count() == 2


def test_daily_quota_is_not_a_transient_rate_limit_or_retried():
    from core.llm import DIAGNOSTICS

    class DailyQuota:
        name, model = "gemini", "test"
        calls = 0

        def generate(self, context):
            self.calls += 1
            raise errors.APIError(
                429,
                {
                    "error": {
                        "message": "SECRET",
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                                "violations": [
                                    {
                                        "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                                        "quotaValue": "500",
                                    }
                                ],
                            },
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": "53s",
                            },
                        ],
                    }
                },
            )

    provider = DailyQuota()
    execution = AgentExecution.objects.create(request_id="daily-quota-test")
    diagnostics = []
    token = DIAGNOSTICS.set(diagnostics)
    try:
        draft, warnings, _ = grounded_generation({}, [], execution, [provider])
    finally:
        DIAGNOSTICS.reset(token)
    assert draft is None and provider.calls == 1
    assert warnings[-1]["code"] == "LLM_QUOTA_EXHAUSTED"
    assert diagnostics[0]["daily_exhausted"] is True
    assert diagnostics[0]["retry_after_seconds"] == 53
    assert "SECRET" not in json.dumps(diagnostics)


def test_server_retry_delay_is_respected_or_stops_when_above_cap(monkeypatch):
    sleeps = []
    monkeypatch.setattr("core.llm.time.sleep", sleeps.append)
    monkeypatch.setenv("LLM_RETRY_BASE_SECONDS", "1")

    class PerMinute:
        name, model = "gemini", "test"
        calls = 0

        def generate(self, context):
            self.calls += 1
            raise errors.APIError(
                429,
                {
                    "error": {
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": "7s",
                            }
                        ]
                    }
                },
            )

    execution = AgentExecution.objects.create(request_id="retry-after-test")
    provider = PerMinute()
    grounded_generation({}, [], execution, [provider])
    assert provider.calls == 2 and sleeps == [7]
    monkeypatch.setenv("LLM_RETRY_MAX_SECONDS", "5")
    provider = PerMinute()
    sleeps.clear()
    grounded_generation({}, [], execution, [provider])
    assert provider.calls == 1 and not sleeps
