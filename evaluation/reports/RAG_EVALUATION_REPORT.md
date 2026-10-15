# RAG Evaluation Report

Generated from actual evaluation output on 2026-10-01T20:11:10.392120+05:30. Run `665afa6d748242268576bcfbbe650196`.

## Project and dataset

The existing React/Django/LangGraph application retrieves preserved section chunks with MiniLM and FAISS, then generates and validates Gemini answers with traceable sources. No profile or eligibility rule engine is used.

The unchanged knowledge base contains 16 schemes. This run contains 27 questions, expects 16 schemes, retrieves 16 and cites 13 distinct schemes.
References are benchmark labels derived from exact preserved dataset sections; they are never supplied to the application generator. All reference contexts are checked against their stable chunk IDs and corpus fingerprint before the run.

Corpus SHA-256: `805a64250c4e33f7d6e116d40cc2b054cb557fe6a69a6314d179a300929042ea`. Evaluation dataset SHA-256: `441e62c3d97f17ffd579d703ef43687a59aa168aad6775ee67cc166bfb2fa2c6`.

## Methodology and configuration

Each question invokes the existing production query() workflow: local domain classification, normal FAISS retrieval, bounded context, Gemini generation/review, final response validation and source citations. An opt-in trace captures the actual retrieved chunks, FAISS scores, context counts and timings without a second retrieval. Disposable evaluation sessions are deleted. RAGAS runs only afterward in the explicit offline command.

RAGAS `0.4.3`; Pydantic `2.12.5`; Python `3.10.10`; google-genai `1.63.0`.
Application/judge configuration: `{"answer_relevancy_strictness": 3, "application_delay_seconds": 20.0, "application_model": "gemini-3.5-flash-lite", "application_provider": "gemini", "context_max_chars": 10000, "embedding_model": "sentence-transformers/all-MiniLM-L6-v2", "grounding_review": "auto", "history_max_chars": 2000, "judge_delay_seconds": 4.0, "judge_max_output_tokens": 4096, "judge_model": "gemini-3.5-flash-lite", "judge_temperature": 0}`.

The installed RAGAS 0.4.3 metrics.collections API builds prompts and computes scores. A structured Gemini adapter supplies judge responses; existing local MiniLM embeddings supply Answer Relevancy similarity. Context Precision uses reference answers. Context Recall measures reference claims covered by the actual retrieved contexts.

## Actual RAGAS measurements

Means use successful numeric measurements only. Errors and skips are shown separately, never assigned fabricated zero/perfect scores. Behavioral redirects and optional clarification have no factual reference contexts and are excluded from these means.

| Metric | Mean | Scored | Errors | Skipped |
|---|---:|---:|---:|---:|
| faithfulness | 0.9592 | 17 | 0 | 10 |
| answer_relevancy | 0.8585 | 17 | 0 | 10 |
| context_precision | 0.7029 | 17 | 0 | 10 |
| context_recall | 0.9706 | 17 | 0 | 10 |

Faithfulness checks claims against retrieved evidence; Answer Relevancy checks question/answer relevance; Context Precision checks ranked context usefulness; Context Recall checks coverage of the reference answer. These are model-judged metrics, not official eligibility decisions or a proof of factual correctness.

## Latency and token usage

Retrieval latency (milliseconds): `{"p50": 21.894, "p95": 198.948, "p99": 219.669}`. End-to-end application latency, including local classification and validation but excluding offline judging: `{"p50": 5183.963, "p95": 13305.78, "p99": 15939.943}`.
Actual application provider usage: `{"calls": 63, "input_tokens": 75233, "output_tokens": 17244, "calls_missing_usage": 9}`.
Actual offline evaluator provider usage: `{"calls": 154, "input_tokens": 148063, "output_tokens": 20371, "calls_missing_usage": 3}`.
Unknown usage is counted explicitly; token sums contain only available provider measurements. Cold-start samples are included. Per-metric judging latency and each attempted provider call appear in the JSON results.

## Per-question results

| ID | Category | Status | Behavior | Faithfulness | Relevancy | Precision | Recall | Retrieval ms | Total ms |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| scheme_1 | direct | success | PASS | 1.0000 | 0.8705 | 1.0000 | 1.0000 | 205.6 | 16670.2 |
| scheme_2 | documents | success | PASS | 1.0000 | 0.9978 | 1.0000 | 1.0000 | 62.8 | 4462.6 |
| scheme_3 | application | error | FAIL | unavailable | unavailable | unavailable | unavailable | 42.2 | 11558.7 |
| scheme_4 | eligibility | success | PASS | 1.0000 | 0.9102 | 1.0000 | 1.0000 | 18.8 | 5184.0 |
| scheme_5 | benefits | success | PASS | 0.8889 | 0.9583 | 0.8333 | 1.0000 | 85.7 | 10173.9 |
| scheme_6 | documents | success | PASS | 1.0000 | 0.9885 | 1.0000 | 1.0000 | 18.3 | 2782.2 |
| scheme_7 | application | success | PASS | 1.0000 | 0.9695 | 1.0000 | 1.0000 | 223.9 | 13861.6 |
| scheme_8 | eligibility | success | PASS | 0.9167 | 0.9538 | 0.7500 | 1.0000 | 21.7 | 12008.8 |
| scheme_9 | benefits | success | PASS | 1.0000 | 0.9557 | 1.0000 | 1.0000 | 54.2 | 3161.2 |
| scheme_10 | documents | success | PASS | 1.0000 | 0.9891 | 1.0000 | 1.0000 | 29.0 | 2586.2 |
| scheme_11 | application | error | FAIL | unavailable | unavailable | unavailable | unavailable | 25.8 | 8076.1 |
| scheme_12 | eligibility | success | PASS | 1.0000 | 0.9599 | 0.3333 | 1.0000 | 24.9 | 5688.9 |
| scheme_13 | benefits | success | PASS | 1.0000 | 0.8331 | 1.0000 | 1.0000 | 18.4 | 3211.0 |
| scheme_14 | documents | error | FAIL | unavailable | unavailable | unavailable | unavailable | 161.1 | 8323.3 |
| scheme_15 | application | success | PASS | 1.0000 | 0.8241 | 1.0000 | 1.0000 | 19.7 | 5118.2 |
| scheme_16 | eligibility | success | PASS | 1.0000 | 0.9101 | 0.2000 | 1.0000 | 20.1 | 11478.8 |
| pragati_income | eligibility | success | PASS | 1.0000 | 0.9218 | 0.5000 | 1.0000 | 52.3 | 4976.3 |
| saksham_conditions | multi_condition | error | FAIL | unavailable | unavailable | unavailable | unavailable | 21.0 | 5915.0 |
| indira_apply_documents | multi_chunk | error | FAIL | unavailable | unavailable | unavailable | unavailable | 15.8 | 6098.7 |
| compare_pragati_saksham | multi_scheme | success | PASS | 1.0000 | 0.7463 | 0.3333 | 1.0000 | 22.1 | 6245.7 |
| girls_discovery | multi_scheme | error | FAIL | unavailable | unavailable | unavailable | unavailable | 7.6 | 11600.2 |
| pragati_source | provenance | success | PASS | 1.0000 | 0.8056 | 0.0000 | 1.0000 | 18.4 | 4610.2 |
| missing_deadline | unavailable | insufficient_evidence | PASS | 0.5000 | 0.0000 | 0.0000 | 0.5000 | 20.8 | 4272.5 |
| ambiguous_choice | ambiguous | insufficient_evidence | PASS | unavailable | unavailable | unavailable | unavailable | 1.9 | 2614.4 |
| math | out_of_domain | out_of_scope | PASS | unavailable | unavailable | unavailable | unavailable | 0.0 | 267.2 |
| joke | out_of_domain | out_of_scope | PASS | unavailable | unavailable | unavailable | unavailable | 0.0 | 268.6 |
| politics | out_of_domain | out_of_scope | PASS | unavailable | unavailable | unavailable | unavailable | 0.0 | 300.5 |

## Invalid queries and source/provenance checks

- ambiguous_choice: `insufficient_evidence`, retrieval calls 1, application LLM calls 1, judge calls 0; checks `{"expected_status": true, "expected_scheme_retrieved": true, "expected_scheme_cited": true, "provenance_traceable": true, "off_domain_zero_calls": true, "clarification_without_sources": true}`.
- math: `out_of_scope`, retrieval calls 0, application LLM calls 0, judge calls 0; checks `{"expected_status": true, "expected_scheme_retrieved": true, "expected_scheme_cited": true, "provenance_traceable": true, "off_domain_zero_calls": true, "clarification_without_sources": true}`.
- joke: `out_of_scope`, retrieval calls 0, application LLM calls 0, judge calls 0; checks `{"expected_status": true, "expected_scheme_retrieved": true, "expected_scheme_cited": true, "provenance_traceable": true, "off_domain_zero_calls": true, "clarification_without_sources": true}`.
- politics: `out_of_scope`, retrieval calls 0, application LLM calls 0, judge calls 0; checks `{"expected_status": true, "expected_scheme_retrieved": true, "expected_scheme_cited": true, "provenance_traceable": true, "off_domain_zero_calls": true, "clarification_without_sources": true}`.

All behavioral/source checks pass for 21/27 questions. Source checks compare each displayed citation's ID, name, source URL/name, original record key and exact excerpt with an actually captured chunk. Sources retain stable IDs for the existing `#/scholarships/{id}` frontend route. No official URLs are fabricated when absent in the supplied dataset.

## Failure cases

Transient application failures retried: 9. Previous failed attempts remain in JSON and all token/call totals; metrics describe the latest real result per question.
- Earlier scheme_7: `LLM_RATE_LIMITED`; application calls 1.
- Earlier scheme_8: `LLM_RATE_LIMITED`; application calls 1.
- Earlier scheme_9: `LLM_RATE_LIMITED`; application calls 1.
- Earlier scheme_14: `LLM_RATE_LIMITED`; application calls 2.
- Earlier scheme_15: `LLM_RATE_LIMITED`; application calls 1.
- Earlier pragati_income: `LLM_RATE_LIMITED`; application calls 1.
- Earlier saksham_conditions: `LLM_RATE_LIMITED`; application calls 1.
- Earlier girls_discovery: `LLM_RATE_LIMITED`; application calls 1.
- Earlier pragati_source: `LLM_RATE_LIMITED`; application calls 1.
Resume/pacing history: `[{"current_pacing": {"application_delay_seconds": 20.0, "judge_delay_seconds": 4.0}, "previous_pacing": {"application_delay_seconds": 5.0, "judge_delay_seconds": 2.0}, "resumed_at": "2026-10-01T14:56:13.913247+00:00", "retry_transient_failures": true}]`.
- scheme_3: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RESPONSE_REJECTED`.
- scheme_11: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RESPONSE_REJECTED`.
- scheme_14: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RESPONSE_REJECTED`.
- saksham_conditions: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RESPONSE_REJECTED`.
- indira_apply_documents: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RESPONSE_REJECTED`.
- girls_discovery: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RESPONSE_REJECTED`.

## Limitations

- Small curated corpus and benchmark; expected scheme coverage is not evidence of exhaustive retrieval or generalization.
- Reference answers are exact section snapshots, not independent official annotations; missing data and contradictions remain in the unchanged corpus.
- The configured Gemini model also judges answers: correlated model bias is possible. Local MiniLM similarity is recorded as the Answer Relevancy embedding configuration.
- No metric runs for domain redirects, optional clarification, pipeline errors or empty retrieved contexts; those are behavioral checks with explicit skips.
- Model/network/quota/schema failures remain explicit; measured errors are never converted into fabricated scores.
- Prompt/model/library versions and budgets are recorded but remote outputs can vary. Optional evaluation dependencies are isolated; normal Docker startup does not import or run RAGAS.
- Source provenance and excerpts are checked structurally; they do not establish every qualitative interpretation or current official deadline.

## Reproduction

```powershell
python -m venv --system-site-packages var/eval-venv
.\var\eval-venv\Scripts\python.exe -m pip install -r evaluation/requirements.lock
.\var\eval-venv\Scripts\python.exe evaluation/run_eval.py --ragas --live --delay 20 --judge-delay 4
```

Use --resume to reuse validated real captures and completed metrics after an interrupted run; only incomplete metrics are requested again. Pacing may be increased and is recorded. --retry-failed retries only transient application failures, retaining earlier attempts and all costs; rejected factual output is not retried for a better score. --only ID selects a smaller run and should use a separate --output. Full reproduction may change scores because the external judge is stochastic even at temperature zero. See docs/EVALUATION.md.
