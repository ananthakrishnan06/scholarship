"""Offline-only adapters for RAGAS 0.4.3's installed structured metric API."""

import asyncio
import threading
import time

from core.llm import generation_failure, quota_diagnostics
from core.rag.embeddings import embed_query
from google import genai
from google.genai import types
from ragas.embeddings.base import BaseRagasEmbedding
from ragas.llms.base import InstructorBaseRagasLLM
from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

from evaluation.schemas import ProviderUsage


class LocalEmbeddings(BaseRagasEmbedding):
    def embed_text(self, text, **kwargs):
        return embed_query(text)[0].tolist()

    async def aembed_text(self, text, **kwargs):
        return await asyncio.to_thread(self.embed_text, text)


class GeminiJudge(InstructorBaseRagasLLM):
    """Use the existing SDK with strict JSON schema and record real usage per attempt.

    RAGAS builds the prompts and calculates all scores. This adapter supplies only
    the structured model responses required by its modern metric interface.
    """

    def __init__(self, model, api_key, delay=2, timeout=60):
        self.model = model
        self.delay = delay
        self.client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=timeout * 1000)
        )
        self.usage = []
        self.judgments = []
        self._lock = threading.Lock()
        self._last_start = 0.0

    def generate(self, prompt, response_model):
        for attempt in range(2):
            with self._lock:
                time.sleep(max(0, self.delay - (time.monotonic() - self._last_start)))
                self._last_start = time.monotonic()
                started = time.perf_counter()
                usage = None
                status = "FAILED"
                output_received = False
                error_code = None
                backoff = 0
                try:
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_json_schema=response_model.model_json_schema(),
                            max_output_tokens=4096,
                            temperature=0,
                        ),
                    )
                    output_received = True
                    usage = response.usage_metadata
                    result = response_model.model_validate_json(response.text or "")
                    status = "SUCCESS"
                    self.judgments.append(
                        {
                            "schema": response_model.__name__,
                            "output": result.model_dump(mode="json"),
                        }
                    )
                    return result
                except Exception as exc:
                    # Never retain raw provider exceptions, prompts, headers or credentials.
                    error_code, _, retryable, _ = generation_failure(
                        exc, output_received=output_received
                    )
                    retry_after = quota_diagnostics(exc)["retry_after_seconds"] or 0
                    if retry_after > 20:
                        retryable = False
                    backoff = max(10 * 2**attempt, retry_after)
                    if not retryable or attempt:
                        raise RuntimeError("RAGAS_JUDGE_REQUEST_FAILED") from None
                finally:
                    self.usage.append(
                        ProviderUsage(
                            model=self.model,
                            phase="ragas_judge",
                            status=status,
                            error_code=error_code,
                            input_tokens=getattr(usage, "prompt_token_count", None),
                            output_tokens=getattr(usage, "candidates_token_count", None),
                            latency_ms=(time.perf_counter() - started) * 1000,
                        )
                    )
            time.sleep(backoff)
        raise RuntimeError("RAGAS_JUDGE_REQUEST_FAILED")

    async def agenerate(self, prompt, response_model):
        return await asyncio.to_thread(self.generate, prompt, response_model)

    def close(self):
        self.client.close()


def build_metrics(judge):
    return {
        "faithfulness": Faithfulness(llm=judge),
        "answer_relevancy": AnswerRelevancy(llm=judge, embeddings=LocalEmbeddings(), strictness=3),
        "context_precision": ContextPrecision(llm=judge),
        "context_recall": ContextRecall(llm=judge),
    }


def metric_arguments(name, result):
    common = {"user_input": result.question}
    if name in ("faithfulness", "answer_relevancy"):
        common["response"] = result.response.answer
    if name != "answer_relevancy":
        common["retrieved_contexts"] = result.retrieved_contexts
    if name in ("context_precision", "context_recall"):
        common["reference"] = result.reference
    return common
