"""Public RAG requests, generated answers, and traceable source evidence."""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictBool,
    StringConstraints,
    TypeAdapter,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Identifier = Annotated[str, StringConstraints(min_length=1, max_length=200)]


class Citation(StrictModel):
    scheme_id: Identifier
    scheme_name: str = Field(min_length=1, max_length=500)
    source_name: str | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    retrieved_from: str = Field(min_length=1, max_length=500)
    original_record_key: str | None = Field(default=None, min_length=1, max_length=200)
    excerpt: str | None = Field(default=None, min_length=1, max_length=3000)

    @field_validator("source_url")
    @classmethod
    def safe_source_url(cls, value):
        if value is not None:
            url = TypeAdapter(HttpUrl).validate_python(value)
            if url.username or url.password:
                raise ValueError("Source URLs must not contain credentials.")
        return value


class ErrorItem(StrictModel):
    code: str
    message: str


class ScholarshipAnswer(StrictModel):
    answer: str = Field(min_length=1, max_length=8000)
    sources: list[Citation] = Field(max_length=16)
    status: Literal["success", "out_of_scope", "insufficient_evidence", "error"]
    error: ErrorItem | None = None
    request_id: str | None = None
    session_id: str | None = None

    @model_validator(mode="after")
    def consistent_status(self):
        if (self.status == "error") != (self.error is not None):
            raise ValueError("Only error responses must carry an error object.")
        if self.status in ("out_of_scope", "error") and self.sources:
            raise ValueError("Off-domain and failed answers cannot cite schemes.")
        if self.status == "success" and not self.sources:
            raise ValueError("Successful scholarship answers require sources.")
        if any(not source.excerpt for source in self.sources):
            raise ValueError("Answer citations require supporting excerpts.")
        return self


class SearchRequest(StrictModel):
    question: str = Field(default="", max_length=2000)
    scheme_ids: list[Identifier] | None = Field(default=None, max_length=16)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    top_k: int = Field(default=8, ge=1, le=16, strict=True)

    @field_validator("scheme_ids")
    @classmethod
    def distinct_identifiers(cls, value):
        if value is not None and len(value) != len(set(value)):
            raise ValueError("Scholarship identifiers must be unique.")
        return value


class RetrievalRequest(SearchRequest):
    intent: str | None = Field(default=None, max_length=30)
    sections: (
        list[
            Literal[
                "objective",
                "target_groups",
                "tags",
                "benefits",
                "eligibility",
                "documents_required",
                "application",
                "exclusions",
                "selection",
                "important_notes",
            ]
        ]
        | None
    ) = Field(default=None, max_length=10)


class QueryRequest(SearchRequest):
    context_scheme_id: str | None = Field(default=None, min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=40)


class Quote(StrictModel):
    chunk_id: str = Field(min_length=1, max_length=500)
    quote: str = Field(
        min_length=1,
        max_length=3000,
        description="One exact contiguous source span; do not join separated fields.",
    )


class GroundedDraft(StrictModel):
    answer: str = Field(min_length=1, max_length=8000)
    status: Literal["success", "out_of_scope", "insufficient_evidence"]
    supports: list[Quote] = Field(max_length=16)


class ClarificationDraft(GroundedDraft):
    status: Literal["insufficient_evidence"]
    supports: list[Quote] = Field(default_factory=list, max_length=0)


class GroundingReview(StrictModel):
    notes_examined: list[str] = Field(
        default_factory=list,
        max_length=32,
        description="IDs of ALL important_notes examined, including irrelevant notes. Do not list other section IDs.",
    )
    supported: StrictBool
    issues: list[str] = Field(max_length=16)
