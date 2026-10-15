# RAG Evaluation Report

Generated from actual evaluation output on 2026-10-01T22:02:55.806243+05:30. Run `76b82e4e4a494a26a7bd413b9926c5a2`.

## Project and dataset

The existing React/Django/LangGraph application retrieves preserved section chunks with MiniLM and FAISS, then generates and validates Gemini answers with traceable sources. No profile or eligibility rule engine is used.

The unchanged knowledge base contains 16 schemes. This run contains 27 questions, expects 16 schemes, retrieves 16 and cites 3 distinct schemes.
References are benchmark labels derived from exact preserved dataset sections; they are never supplied to the application generator. All reference contexts are checked against their stable chunk IDs and corpus fingerprint before the run.

Corpus SHA-256: `805a64250c4e33f7d6e116d40cc2b054cb557fe6a69a6314d179a300929042ea`. Evaluation dataset SHA-256: `441e62c3d97f17ffd579d703ef43687a59aa168aad6775ee67cc166bfb2fa2c6`.

## Methodology and configuration

Each question invokes the existing production query() workflow: local domain classification, normal FAISS retrieval, bounded context, Gemini generation/review, final response validation and source citations. An opt-in trace captures the actual retrieved chunks, FAISS scores, context counts and timings without a second retrieval. Disposable evaluation sessions are deleted. RAGAS runs only afterward in the explicit offline command.

RAGAS `0.4.3`; Pydantic `2.12.5`; Python `3.10.10`; google-genai `1.63.0`.
Application/judge configuration: `{"answer_relevancy_strictness": 3, "application_delay_seconds": 20.0, "application_max_attempts": 3, "application_max_output_tokens": 1800, "application_model": "gemini-3.5-flash-lite", "application_prompt_sha256": "a9a649fc3eb4eec909f7f5c6fe6c721542d2047dae5d59bb73c9b4a04331bbfb", "application_provider": "gemini", "application_retry_base_seconds": 5.0, "application_retry_max_seconds": 20.0, "application_temperature": 0.2, "application_time_budget_seconds": 90.0, "context_max_chars": 10000, "embedding_model": "sentence-transformers/all-MiniLM-L6-v2", "grounding_review": "auto", "history_max_chars": 2000, "judge_delay_seconds": 4.0, "judge_max_output_tokens": 4096, "judge_model": "gemini-3.5-flash-lite", "judge_temperature": 0, "pipeline_revision": "targeted-reliability-v1", "pipeline_sha256": "28a1d9c8dc98f5d14bf33c2819d3b5bedc55f9dccc18c7760aa7db858beff10a"}`.

The installed RAGAS 0.4.3 metrics.collections API builds prompts and computes scores. A structured Gemini adapter supplies judge responses; existing local MiniLM embeddings supply Answer Relevancy similarity. Context Precision uses reference answers. Context Recall measures reference claims covered by the actual retrieved contexts.

## Actual RAGAS measurements

Means use successful numeric measurements only. Errors and skips are shown separately, never assigned fabricated zero/perfect scores. Behavioral redirects and optional clarification have no factual reference contexts and are excluded from these means.

| Metric | Mean | Scored | Errors | Skipped |
|---|---:|---:|---:|---:|
| faithfulness | 1.0000 | 3 | 0 | 24 |
| answer_relevancy | 0.9463 | 2 | 1 | 24 |
| context_precision | 1.0000 | 2 | 1 | 24 |
| context_recall | 1.0000 | 2 | 1 | 24 |

Faithfulness checks claims against retrieved evidence; Answer Relevancy checks question/answer relevance; Context Precision checks ranked context usefulness; Context Recall checks coverage of the reference answer. These are model-judged metrics, not official eligibility decisions or a proof of factual correctness.

## Latency and token usage

Retrieval latency (milliseconds): `{"p50": 45.849, "p95": 151.292, "p99": 345.54}`. End-to-end application latency, including local classification and validation but excluding offline judging: `{"p50": 17816.199, "p95": 45192.547, "p99": 57428.717}`.
Actual application provider usage: `{"calls": 67, "input_tokens": 3958, "output_tokens": 920, "calls_missing_usage": 63}`.
Actual offline evaluator provider usage: `{"calls": 24, "input_tokens": 15265, "output_tokens": 3174, "calls_missing_usage": 6}`.
Unknown usage is counted explicitly; token sums contain only available provider measurements. Cold-start samples are included. Per-metric judging latency and each attempted provider call appear in the JSON results.

## Per-question results

| ID | Category | Status | Behavior | Faithfulness | Relevancy | Precision | Recall | Retrieval ms | Total ms |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| scheme_1 | direct | success | PASS | 1.0000 | 0.9012 | 1.0000 | 1.0000 | 400.8 | 17816.2 |
| scheme_2 | documents | success | PASS | 1.0000 | 0.9914 | 1.0000 | 1.0000 | 35.2 | 3033.6 |
| scheme_3 | application | success | PASS | 1.0000 | unavailable | unavailable | unavailable | 79.3 | 3461.3 |
| scheme_4 | eligibility | error | FAIL | unavailable | unavailable | unavailable | unavailable | 19.3 | 17348.0 |
| scheme_5 | benefits | error | FAIL | unavailable | unavailable | unavailable | unavailable | 88.7 | 20286.0 |
| scheme_6 | documents | error | FAIL | unavailable | unavailable | unavailable | unavailable | 18.8 | 17234.8 |
| scheme_7 | application | error | FAIL | unavailable | unavailable | unavailable | unavailable | 34.5 | 18448.9 |
| scheme_8 | eligibility | error | FAIL | unavailable | unavailable | unavailable | unavailable | 84.7 | 17288.0 |
| scheme_9 | benefits | error | FAIL | unavailable | unavailable | unavailable | unavailable | 51.0 | 17416.6 |
| scheme_10 | documents | error | FAIL | unavailable | unavailable | unavailable | unavailable | 20.8 | 18425.4 |
| scheme_11 | application | error | FAIL | unavailable | unavailable | unavailable | unavailable | 27.9 | 18727.8 |
| scheme_12 | eligibility | error | FAIL | unavailable | unavailable | unavailable | unavailable | 51.8 | 18591.0 |
| scheme_13 | benefits | error | FAIL | unavailable | unavailable | unavailable | unavailable | 46.8 | 17880.5 |
| scheme_14 | documents | error | FAIL | unavailable | unavailable | unavailable | unavailable | 98.7 | 17348.3 |
| scheme_15 | application | error | FAIL | unavailable | unavailable | unavailable | unavailable | 44.4 | 17183.1 |
| scheme_16 | eligibility | error | FAIL | unavailable | unavailable | unavailable | unavailable | 48.4 | 17326.2 |
| pragati_income | eligibility | error | FAIL | unavailable | unavailable | unavailable | unavailable | 43.2 | 23860.1 |
| saksham_conditions | multi_condition | error | FAIL | unavailable | unavailable | unavailable | unavailable | 44.9 | 58885.1 |
| indira_apply_documents | multi_chunk | error | FAIL | unavailable | unavailable | unavailable | unavailable | 44.2 | 22696.1 |
| compare_pragati_saksham | multi_scheme | error | FAIL | unavailable | unavailable | unavailable | unavailable | 160.6 | 53283.7 |
| girls_discovery | multi_scheme | error | FAIL | unavailable | unavailable | unavailable | unavailable | 41.5 | 26313.3 |
| pragati_source | provenance | error | FAIL | unavailable | unavailable | unavailable | unavailable | 59.4 | 21838.5 |
| missing_deadline | unavailable | error | FAIL | unavailable | unavailable | unavailable | unavailable | 82.0 | 19956.9 |
| ambiguous_choice | ambiguous | error | FAIL | unavailable | unavailable | unavailable | unavailable | 28.3 | 17813.7 |
| math | out_of_domain | out_of_scope | PASS | unavailable | unavailable | unavailable | unavailable | 0.0 | 285.8 |
| joke | out_of_domain | out_of_scope | PASS | unavailable | unavailable | unavailable | unavailable | 0.0 | 375.0 |
| politics | out_of_domain | out_of_scope | PASS | unavailable | unavailable | unavailable | unavailable | 0.0 | 317.3 |

## Invalid queries and source/provenance checks

- ambiguous_choice: `error`, retrieval calls 1, application LLM calls 3, judge calls 0; checks `{"expected_status": false, "expected_scheme_retrieved": true, "expected_scheme_cited": true, "provenance_traceable": true, "off_domain_zero_calls": true, "clarification_without_sources": true}`.
- math: `out_of_scope`, retrieval calls 0, application LLM calls 0, judge calls 0; checks `{"expected_status": true, "expected_scheme_retrieved": true, "expected_scheme_cited": true, "provenance_traceable": true, "off_domain_zero_calls": true, "clarification_without_sources": true}`.
- joke: `out_of_scope`, retrieval calls 0, application LLM calls 0, judge calls 0; checks `{"expected_status": true, "expected_scheme_retrieved": true, "expected_scheme_cited": true, "provenance_traceable": true, "off_domain_zero_calls": true, "clarification_without_sources": true}`.
- politics: `out_of_scope`, retrieval calls 0, application LLM calls 0, judge calls 0; checks `{"expected_status": true, "expected_scheme_retrieved": true, "expected_scheme_cited": true, "provenance_traceable": true, "off_domain_zero_calls": true, "clarification_without_sources": true}`.

All behavioral/source checks pass for 6/27 questions. Source checks compare each displayed citation's ID, name, source URL/name, original record key and exact excerpt with an actually captured chunk. Sources retain stable IDs for the existing `#/scholarships/{id}` frontend route. No official URLs are fabricated when absent in the supplied dataset.

## Failure cases

- scheme_3/answer_relevancy: `RAGAS_METRIC_FAILED`; Metric evaluation failed (RuntimeError). No score was substituted.
- scheme_3/context_precision: `RAGAS_METRIC_FAILED`; Metric evaluation failed (RuntimeError). No score was substituted.
- scheme_3/context_recall: `RAGAS_METRIC_FAILED`; Metric evaluation failed (RuntimeError). No score was substituted.
- scheme_4: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_5: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_6: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_7: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_8: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_9: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_10: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_11: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_12: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_13: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_14: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_15: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- scheme_16: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- pragati_income: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- saksham_conditions: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- indira_apply_documents: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- compare_pragati_saksham: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_NETWORK_ERROR`.
- girls_discovery: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- pragati_source: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- missing_deadline: failed checks ['expected_status', 'expected_scheme_cited']; response error `LLM_RATE_LIMITED`.
- ambiguous_choice: failed checks ['expected_status']; response error `LLM_RATE_LIMITED`.

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
