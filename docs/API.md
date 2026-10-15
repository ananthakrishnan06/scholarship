# RAG API

Swagger UI: `/api/docs`; OpenAPI 3.1: `/api/schema`. Routes have no trailing slash.
Unknown fields and oversized/invalid inputs are rejected. X-Request-ID correlates logs.

| Route | Purpose |
|---|---|
| POST /api/agent/query | Conversational RAG answer |
| POST /api/rag/query | Same grounded workflow |
| POST /api/scholarships/search | Browse corpus records; question/category/scheme_ids/top_k |
| GET /api/scholarships/{scheme_id} | Full source record including eligibility criteria |
| POST /api/sessions | Create private conversation; returns token once |
| GET /api/sessions/{session_id} | Read conversation with X-Session-Token |
| DELETE /api/sessions/{session_id} | Delete conversation with its token |
| GET /api/health/live | Django liveness; no database, Gemini or user query |
| GET /api/health/ready | Database, validated index and locally cached embedding model readiness |
| GET /api/health | SQL/corpus/vector readiness and whether LLM is configured |
| POST /api/admin/ingest | Authenticated staff ingestion |
| GET /api/agent/usage | Authenticated staff aggregate usage |

Query fields: required question; optional scheme_ids, category, top_k (1-16, default
8), session_id and context_scheme_id. The latter supplies a selected scheme for implicit
follow-ups; explicit named questions can change topic. scheme_ids remains an explicit filter. A session_id requires X-Session-Token. No profile field is accepted.
`/api/profile/validate` and `/api/eligibility/check` have been removed and return 404.

Response: answer, sources, status, optional error, request_id, session_id. Sources
carry scheme/source identities, available official URL, the supporting reference and
exact excerpt. Frontend displays distinct cited scholarship names and safe source links.
`success`, `out_of_scope`, `insufficient_evidence` return 200; `error` returns 503.
An empty deadline is not a guessed deadline. An off-topic response has no sources and skips retrieval/provider calls. It does
not answer arithmetic, sports, coding or other unrelated requests. Sources use the
existing scheme_id to open #/scholarships/{id} within this website.
No deterministic eligibility statuses, rules, traces or profiles are returned.

Health checks configuration, not a live model call. Provider outages can occur even
when health reports configured. API keys are never returned. Browsing remains useful
without a provider, but assistant generation requires one.

## Pydantic validation and evaluation tracing

The existing models now require nonempty/bounded scheme/source identifiers,
distinct scheme filters, integer `top_k` (not strings or booleans), nonempty answers,
HTTP(S) source URLs without embedded credentials and consistent answer statuses.
Successful responses require citations with excerpts; failed/off-domain responses
have no scheme citations, and only failed responses carry an error object. Invalid
request bodies retain the existing structured HTTP 400 handling.

The existing source Chunk is a frozen Pydantic dataclass that checks content,
section and exact citation/chunk identity before index use. No eligibility facts
are encoded by these validators. The generated backend/schemas/assistant_response_schema.json and
OpenAPI schema are updated; cross-field checks are also enforced at runtime.

An optional internal `query(..., trace=...)` argument lets the offline evaluator
capture actual retrieval output and timings. It changes neither public API fields
nor source-link routing. RAGAS is never imported or invoked by the API.


`LLM_QUOTA_EXHAUSTED` distinguishes an exhausted daily provider quota from a
transient `LLM_RATE_LIMITED` response. Both retain the existing HTTP 503 error
contract. Returned invalid factual output is not regenerated; transient requests
retry within bounded phase/time limits, with all attempted calls audited.


Deployment probes return Cache-Control: no-store. /api/health/live returns 200
with status ok. /api/health/ready returns status ready (200) or unavailable (503),
database/vector_index/embedding_model checks and fixed sanitized error codes.
Readiness loads the local model and validates the vector bundle without calling
Gemini; it does not establish provider availability. These probes bypass API
authentication/throttling and retain Django host/HTTPS middleware checks.
