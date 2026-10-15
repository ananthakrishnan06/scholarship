# RAGAS integration verification

Verified on 2026-10-01 in the existing Windows/SQLite application. No application rebuild, dataset edit, FAISS re-ingestion, provider/model change or Git-history rewrite was performed.

## Files created

- `evaluation/ragas_adapter.py`
- `evaluation/ragas_cases.json`
- `evaluation/ragas_eval.py`
- `evaluation/reports/RAG_EVALUATION_REPORT.md`
- `evaluation/reports/ragas_initial.json`
- `evaluation/reports/ragas_results.json`
- `evaluation/requirements.lock`
- `evaluation/requirements.txt`
- `evaluation/schemas.py`
- `tests/test_evaluation.py`
- `tests/test_validation.py`
- `docs/RAGAS_INTEGRATION.md` (this verification manifest).

## Files modified

- `README.md`
- `backend/schemas/assistant_response_schema.json`
- `backend/core/agent/workflow.py`
- `backend/core/rag/documents.py`
- `backend/core/rag/retrieval.py`
- `backend/core/schemas.py`
- `docs/API.md`
- `docs/DEPLOYMENT.md`
- `docs/EVALUATION.md`
- `evaluation/run_eval.py`
- `scripts/lock_dependencies.py`
- `tests/test_rag.py`

## Existing components reused

- The `f043784` evaluation command and `EvaluationRun` persistence; existing retrieval/live modes remain available.
- Production `query()` graph, retrieval tool, classifier, FAISS store, chunker, MiniLM model/cache, Gemini generation/review and usage audit.
- Existing QueryRequest, Citation and ScholarshipAnswer models; the same Chunk dataclass is now Pydantic-validated, not duplicated.
- All 16 original scheme records/JSONL/provenance/QA files, persisted 139-chunk index, source metadata and existing internal detail routes.
- Existing dependency requirements/lock script, API schema generation, backend/frontend/browser tests and Docker/Compose startup.

## Verification

| Check | Actual result |
|---|---|
| Complete backend suite with optional dependencies | 99 passed |
| Normal environment without RAGAS | 93 passed, 6 optional tests skipped |
| Frontend TypeScript/build | Passed |
| Frontend component tests | 7 passed |
| Existing Edge browser suite | 5 passed, including all 16 detail routes |
| Actual FAISS retrieval regression questions | 30/30 passed |
| Django checks / migration drift / OpenAPI | Passed |
| Ruff / repository/source/schema/secret checks | Passed; all 134 staged files scanned, 16 records/schema verified, private values never printed |

## Actual offline measurements

Metrics and counters below are read programmatically from the actual generated RAGAS report, not manually assigned.

| Measurement | Value |
|---|---|
| questions | 27 |
| expected_schemes | 16 |
| retrieved_schemes | 16 |
| cited_schemes | 13 |
| behavior_passed | 21 |
| pipeline_errors | 6 |
| previous_failed_attempts | 9 |
| faithfulness | 0.959150; 17 scored, 0 errors, 10 skips |
| answer_relevancy | 0.858484; 17 scored, 0 errors, 10 skips |
| context_precision | 0.702941; 17 scored, 0 errors, 10 skips |
| context_recall | 0.970588; 17 scored, 0 errors, 10 skips |

Retrieval latency: `{"p50": 21.894, "p95": 198.948, "p99": 219.669}` milliseconds.
Application end-to-end latency: `{"p50": 5183.963, "p95": 13305.78, "p99": 15939.943}` milliseconds.
Application actual usage, including earlier failed attempts: `{"calls": 63, "input_tokens": 75233, "output_tokens": 17244, "calls_missing_usage": 9}`.
Offline judge actual usage: `{"calls": 154, "input_tokens": 148063, "output_tokens": 20371, "calls_missing_usage": 3}`.

RAGAS 0.4.3 and Pydantic 2.12.5 were verified in the installed evaluation environment. Scores describe the latest real result per question; earlier rate-limit attempts and costs remain recorded. Six rejected generated answers are genuine pipeline failures, not perfect scores or replacement answer text. Three unrelated requests had zero tool/provider/judge calls. Clarification is optional and separate from factual scoring.

## Reports and reproducibility

- [Automatically generated RAG Evaluation Report](../evaluation/reports/RAG_EVALUATION_REPORT.md)
- [Validated results and all provider attempts](../evaluation/reports/ragas_results.json)
- [Preserved first full run](../evaluation/reports/ragas_initial.json)
- [Evaluation setup, API versions, limits and commands](EVALUATION.md)

The live evaluation exits nonzero because six application outputs were rejected; this is not a test-suite or RAGAS-integration failure. Context precision remains lower than the other metrics, including a zero for the source-information request. Missing-information refusals are scored cautiously by factual metrics. Do not interpret scored-subset means as all-question success.

The same configured Gemini model is used as answerer and judge; correlated bias is possible. References are exact dataset snapshots rather than independent official annotations. The dataset has absent URLs/dates and contradictions. Provider rates can still fail; unknown usage is counted explicitly. Production MySQL/Docker runtime validation remains pending. The normal application never runs RAGAS; optional evaluation dependencies are isolated. No secrets, `.env`, environments or runtime cache artifacts are committed. No Git push was performed.
