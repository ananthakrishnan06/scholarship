"""Validated offline evaluation data; reuse production request, chunk and response types."""

from datetime import datetime
from typing import Literal

from core.rag.documents import Chunk
from core.schemas import ErrorItem, Identifier, QueryRequest, ScholarshipAnswer, StrictModel
from pydantic import Field, field_validator, model_validator

MetricName = Literal["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
Category = Literal[
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
]


class EvaluationSample(StrictModel):
    id: Identifier
    question: str
    reference: str = Field(min_length=1, max_length=16000)
    expected_scheme_ids: list[Identifier] = Field(default_factory=list, max_length=16)
    reference_chunk_ids: list[str] = Field(default_factory=list, max_length=40)
    reference_contexts: list[str] = Field(default_factory=list, max_length=40)
    category: Category
    expected_statuses: list[Literal["success", "out_of_scope", "insufficient_evidence"]] = Field(
        min_length=1
    )
    score_ragas: bool = True
    top_k: int = Field(default=8, ge=1, le=16, strict=True)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value):
        return QueryRequest(question=value).question

    @model_validator(mode="after")
    def aligned_references(self):
        if len(self.reference_chunk_ids) != len(self.reference_contexts):
            raise ValueError("Reference chunk IDs and contexts must align.")
        if len(set(self.reference_chunk_ids)) != len(self.reference_chunk_ids):
            raise ValueError("Reference chunks must be distinct.")
        if len(set(self.expected_scheme_ids)) != len(self.expected_scheme_ids):
            raise ValueError("Expected scheme identifiers must be distinct.")
        if self.score_ragas and not self.reference_contexts:
            raise ValueError("Factual RAGAS samples require dataset-derived reference context.")
        if self.category in ("out_of_domain", "ambiguous") and self.score_ragas:
            raise ValueError(
                "Domain redirects and clarification require separate behavioral evaluation."
            )
        return self


class EvaluationDataset(StrictModel):
    version: int = Field(ge=1)
    corpus_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_method: str = Field(min_length=1)
    samples: list[EvaluationSample] = Field(min_length=1)

    @model_validator(mode="after")
    def distinct_samples(self):
        if len({sample.id for sample in self.samples}) != len(self.samples):
            raise ValueError("Evaluation sample IDs must be unique.")
        return self


class ProviderUsage(StrictModel):
    provider: str = "gemini"
    model: str
    phase: str
    status: str
    error_code: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_ms: float = Field(ge=0, allow_inf_nan=False)


class MetricResult(StrictModel):
    status: Literal["ok", "error", "skipped"]
    score: float | None = Field(default=None, ge=-1, le=1, allow_inf_nan=False)
    latency_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    explanation: str | None = None
    error: ErrorItem | None = None

    @model_validator(mode="after")
    def truthful_score(self):
        if (self.status == "ok") != (self.score is not None):
            raise ValueError("Only successful metrics carry numeric scores.")
        if (self.status == "error") != (self.error is not None):
            raise ValueError("Failed metrics require an explicit error.")
        return self


class EvaluationResult(StrictModel):
    id: Identifier
    category: Category
    question: str
    reference: str
    expected_scheme_ids: list[Identifier]
    reference_contexts: list[str]
    response: ScholarshipAnswer
    retrieved_chunks: list[Chunk]
    retrieved_contexts: list[str]
    retrieval_scores: dict[str, float] = Field(default_factory=dict)
    top_k: int = Field(ge=1, le=16, strict=True)
    retrieval_metrics: dict = Field(default_factory=dict)
    retrieval_latency_ms: float = Field(ge=0, allow_inf_nan=False)
    total_latency_ms: float = Field(ge=0, allow_inf_nan=False)
    llm_diagnostics: list[dict] = Field(default_factory=list)
    llm_usage: list[ProviderUsage] = Field(default_factory=list)
    judge_diagnostics: dict[str, list[dict]] = Field(default_factory=dict)
    evaluator_usage: list[ProviderUsage] = Field(default_factory=list)
    retrieval_calls: int = Field(ge=0)
    checks: dict[str, bool]
    metrics: dict[MetricName, MetricResult]

    @model_validator(mode="after")
    def aligned_capture(self):
        if self.retrieved_contexts != [context_text(c) for c in self.retrieved_chunks]:
            raise ValueError("Evaluation contexts must come from captured production chunks.")
        if len({c.chunk_id for c in self.retrieved_chunks}) != len(self.retrieved_chunks):
            raise ValueError("Captured chunks must be distinct.")
        if not set(self.retrieval_scores).issubset({c.chunk_id for c in self.retrieved_chunks}):
            raise ValueError("Retrieval scores must identify captured chunks.")
        if any(not -1 <= score <= 1.00001 for score in self.retrieval_scores.values()):
            raise ValueError("FAISS cosine scores must be finite and bounded.")
        if set(self.metrics) != set(METRICS):
            raise ValueError("Every supported metric needs an explicit result or skip/error.")
        return self


def context_text(chunk):
    return f"{chunk.scheme_name} [{chunk.section}]\n{chunk.text}"


class EvaluationReport(StrictModel):
    run_id: str
    created_at: datetime
    mode: Literal["ragas"] = "ragas"
    corpus_sha256: str
    dataset_sha256: str
    index: dict
    package_versions: dict[str, str]
    configuration: dict
    results: list[EvaluationResult]
    previous_attempts: list[EvaluationResult] = Field(default_factory=list)
    resume_history: list[dict] = Field(default_factory=list)
    limitations: list[str]
