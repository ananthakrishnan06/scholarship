# Bounded scholarship assistant

The existing LangGraph DAG now has an early conditional exit:
plan/domain check -> (out-of-scope guidance OR semantic retrieval -> answer).
There is no profile, eligibility tool or model-based query rewrite. Graph iteration
limits, validated retrieval arguments, four worker slots, bounded timeouts/retry and
private conversation references remain. Unrelated turns preserve the last useful
scheme reference and create no retrieval/provider usage rows.

All scholarship facts still require retrieved text. Gemini uses response_json_schema
and returns the actual natural answer, status and exact support references. Ambiguous
recommendations use a constrained clarification schema: insufficient_evidence,
empty supports, optional natural-language clarification, no personal questionnaire.

LLM_GROUNDING_REVIEW=auto uses one generation for simple lookups. Conflicts, criteria,
comparisons, deadlines, multi-scheme complexity and suggested numbers trigger review.
The always option retains review for every answer. A separate review is a safeguard,
not proof; skipping it trades some scrutiny for lower cost/latency. Provider requests
never select or change deterministic eligibility rules because there are none.

Malformed or unsupported returned output stops immediately, including across
fallback providers. Transient 429/network/timeout/5xx errors retry only their failed
phase, at most three attempts with exponential backoff (5/10 seconds by default).
Server RetryInfo is respected; a delay exceeding the configured cap stops the call.
Daily QuotaFailure is reported as LLM_QUOTA_EXHAUSTED without repeating the request.
Generation and review share a 90-second budget under the default 30-second timeout.
A configured secondary provider may handle provider failures, never rejected facts.
Failures return HTTP 503 and safe operational codes; no quote dump replaces an AI answer.
Input/output budgets apply to all calls. Each actual call has provider/model/phase,
input/output tokens, status and latency records. Runtime logs add domain scores,
query fingerprint and source/context size. Raw query text is opt-in and credential
patterns are redacted; keys, raw exceptions and full prompts are never logged.
