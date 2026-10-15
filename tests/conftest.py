import pytest


@pytest.fixture(autouse=True)
def no_live_model_calls(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "none")
    monkeypatch.setenv("LLM_GROUNDING_REVIEW", "always")

    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("LLM_RETRY_BASE_SECONDS", "0")
