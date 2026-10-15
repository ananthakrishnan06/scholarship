# Repository cleanup audit

This cleanup preserves the existing Django/React/LangGraph/MiniLM/FAISS/Gemini
application. API contracts, frontend source navigation, generation/validation
behavior, evaluation calculations, dependency versions, the 16-scheme dataset
and existing index are unchanged from the verified pre-cleanup working state.

## Starting state and audit

The actual repository is `D:/social-hackthon/social-hackthon`, on `main`. It already
had Git history and a remote. Status, branch, the last ten commits, every tracked
path, all non-generated workspace paths and root entries were inspected first.
No additional repository was initialized and no existing history was rewritten.

There were 22 modified files plus reliability documentation, a comparison script
and real evaluation artifacts left from the previous task. Those changes were
verified separately and preserved in commit `74a020b` before this cleanup. The
cleanup commit contains only organization, file-reference and documentation changes.
A full comparable reliability rerun remains a separate task; its previous quota
report is retained honestly, as described in [QUALITY_FIX.md](QUALITY_FIX.md).

Nonempty tracked files and the pending report directory were grouped by SHA-256.
References to every root data/schema file, configuration template, dependency
manifest and evaluation fixture were searched across backend, frontend, scripts,
tests, evaluation, Docker, deployment and documentation before moving files.

## Files moved without content changes

Every original working-copy hash below still matches the destination. Git-normalized
content also matches the pre-cleanup commit. Git's existing text normalization can
make its stored LF bytes differ from a Windows working copy; the moves themselves
do not change file bytes.

| Previous path | Current path | Original SHA-256 |
|---|---|---|
| `scholarship_dataset_ready.json` | `data/scholarship_dataset_ready.json` | `805a64250c4e33f7d6e116d40cc2b054cb557fe6a69a6314d179a300929042ea` |
| `scholarship_dataset_ready.jsonl` | `data/scholarship_dataset_ready.jsonl` | `418250461189ebccf5e4dde463fe10e51bc26abf308fab4a567c6e86ba430d49` |
| `combined_scholarship_schemes_cleaned.json` | `data/combined_scholarship_schemes_cleaned.json` | `206416eeb61194a0b9d0086e8e2a81beb47484bb433fe69f2824a1e793a56d92` |
| `scholarship_dataset_QA_report.json` | `data/scholarship_dataset_QA_report.json` | `e4fe8ad4d6f05fd5b13d986282353004291024a490110aa9e10c3e473bff41c6` |
| `assistant_response_schema.json` | `backend/schemas/assistant_response_schema.json` | `d4719452d73286ebf63e0cd2e3061fe32c8936cbbc8b1b625d73e1207e708053` |
| `README (1).md` | `docs/history/ELIGIBILITY_ENGINE.md` | `6f0e454f383f4ac2b33a64c8fd8a093a37c3ce7d93876e21e26fde2d6376fdbb` |

The two runtime corpora are different representations: the ready JSON supplies
records/sections; the source JSON verifies original-record provenance. The JSONL
projection and QA report are useful preserved data-stage artifacts. None were
deduplicated or rewritten. The QA report's dataset basename remains unchanged and
identifies the neighboring file in `data/`. [DATASET.md](DATASET.md) lists consumers.

`README (1).md` is not a duplicate of the current README. It describes the retired
profile/rule engine and includes unique examples. Its exact contents are archived
under `docs/history/`; README.md links it explicitly as historical documentation.
Its old import/path examples remain historical examples, not current instructions.

The response JSON schema is a generated, versioned contract snapshot consumed by
`scripts/verify_repository.py`. Runtime API and LLM validation still use Pydantic
models in `backend/core/schemas.py`; those validators were not replaced or weakened.

## Duplicate artifacts removed

Only these untracked backup copies were removed, after byte-for-byte equality with
the retained canonical artifacts was checked:

- `evaluation/reports/quality_fix/quota_exhausted/ragas_results.json`
- `evaluation/reports/quality_fix/quota_exhausted/RAG_EVALUATION_REPORT.md`

The identical empty backup directory was removed afterward. The original full run,
its failures, comparison, targeted checks and baseline remain in `evaluation/reports/`.
No unique source, dataset, report or historical document was deleted.

## Retained structure and reasons

| Location | Contents and reason |
|---|---|
| `backend/` | Django settings, API, database models/migrations, agent, RAG pipeline and Pydantic validation; Python package structure unchanged. |
| `backend/schemas/` | Public assistant-response JSON schema snapshot, checked against runtime models. |
| `frontend/` | React UI, API client, detail/source navigation, Vite configuration, package locks, component and browser tests; no frontend code changes. |
| `data/` | All four supplied scholarship data/QA artifacts, required for reproducibility. |
| `evaluation/` | Existing scripts, fixture JSON, optional RAGAS adapters and dependency locks. Existing command paths remain valid. |
| `evaluation/reports/` | Submitted results and historical evidence; generated but intentionally retained, not ignored. |
| `docs/` | Architecture, API, RAG, security, dataset, deployment, evaluation and historical documentation. Existing flat structure is already understandable. |
| `scripts/`, `tests/` | Existing installation/verification tools and regression suites. |
| `deploy/` | Reverse-proxy configuration and empty production environment template. |
| Root Dockerfiles/Compose | Required build/deployment entry points; backend COPY sources now point into `data/`. |
| Root dependency manifests | `requirements.lock` pins tested/Docker dependencies; `requirements.txt` gives supported ranges; `pyproject.toml` configures pytest/Ruff. No versions changed. |
| Root `.env.example` | Existing empty configuration template. Private `.env` retained locally and untouched. |
| Ignored `var/` | SQLite, model/index caches, logs, diagnostic captures and temporary verification output; local application state preserved. |

No unnecessary evaluation/module/document-directory moves were made. Root project
configuration and README.md remain the main entry points.

## Ignore and reference changes

`.gitignore` already excludes environment/secrets/credentials, virtual environments,
Python caches, node_modules, build/browser artifacts, IDE files, local logs and
runtime/index artifacts under `var/`. It required no changes. Fresh smoke results
are written under `var/repository-cleanup/`. Assertions confirmed ten required
source/data/report/template paths remain visible and seven representative private
or generated paths remain ignored. No broad data/report/document exclusions added.

`.dockerignore` now also excludes other private environment/credential names,
private keys, development virtual environments, IDE files and local logs. Important
environment templates remain allowed.

The runtime corpus loader, foundation test, repository schema verifier and backend
Docker COPY instruction now use the new paths. README and current dataset/API/audit/
deployment/RAG integration documentation were updated. Existing evaluation commands,
index directory, environment-variable names and API routes are unchanged. Old paths
remain only in original QA metadata, the archived old README and the explicitly
historical Git inventory. Searches found no stale operational paths. All backend
Docker COPY source paths exist.

## Verification executed

| Check | Actual result |
|---|---|
| `python -m pytest -q` | 107 passed, 8 optional evaluation tests skipped. |
| Optional eval-venv pytest | 115 passed, including offline RAGAS adapters, metric calls and retry tests. |
| Ruff check and format check | Passed. |
| Django system check | No issues. |
| Django `makemigrations --check --dry-run` | No changes detected. |
| Django OpenAPI `spectacular --validate` | Passed; output in ignored `var/repository-cleanup/openapi.yaml`. |
| Repository source/schema/secret-pattern verifier | Passed; 16-record provenance and response schema match. Repeated after staging. |
| Frontend TypeScript lint and production build | Passed. |
| Frontend Vitest | 7 passed. |
| Headless Edge/Playwright | 5 passed; real API startup, scheme detail/source navigation, mobile layout and error handling. Browser model answers are controlled offline. |
| Existing retrieval evaluation | 30/30 cases passed; original 139-chunk index reused. |
| Running API/frontend | Health and UI HTTP 200; SQLite connected; 16/16 detail routes return application sections. |
| Invalid and out-of-domain API requests | Empty question HTTP 400 INVALID_INPUT; joke HTTP 200 out_of_scope with zero sources. |
| One live production/RAGAS case | Successful sourced Gemini answer, all behavior/provenance checks pass; all four RAGAS metrics score successfully. |
| Corpus/benchmark/submitted report integrity | Corpus hash/index identity unchanged; benchmark and baseline reports preserved. |

The initial HTTP domain probe's 25-second timeout expired during the restarted
backend's cold embedding load. Repeating with a 90-second allowance succeeded.
No application changes were made to address this startup timing.

## Real evaluation smoke results

The existing command was executed without modifying its evaluation logic:

```powershell
python evaluation/run_eval.py --output var/repository-cleanup/retrieval.json
.\var\eval-venv\Scripts\python.exe evaluation/run_eval.py --ragas --live --only scheme_1 --delay 0 --judge-delay 4 --output var/repository-cleanup/ragas_smoke.json
```

Live run ID: `9a1046b03fb84c71a6c80abeaf4b023b`. Exactly one question was scored; this is a
path/integration smoke check, not a new full benchmark or proof of quality gains.

| Metric | Actual value | Scored/errors/skipped |
|---|---:|---|
| faithfulness | 1.0000 | 1/0/0 |
| answer_relevancy | 0.8774 | 1/0/0 |
| context_precision | 1.0000 | 1/0/0 |
| context_recall | 1.0000 | 1/0/0 |

Retrieval latency was 808.42 ms; end-to-end
application time was 65503.687 ms, including provider
retry/grounding review. All six behavioral/source checks passed, with two exact
source chunks citing one scholarship and its stable internal detail identifier.

Actual application usage: `{"calls": 3, "input_tokens": 1966, "output_tokens": 340, "calls_missing_usage": 1}`.
Actual evaluator usage: `{"calls": 10, "input_tokens": 7181, "output_tokens": 1276, "calls_missing_usage": 2}`.
Transient provider HTTP 503 responses recovered through the existing bounded retry
policy. Failed requests and unavailable usage remain explicitly recorded. Unknown
usage is not converted into invented token or price measurements.

Precision and latency are still measurable by the existing retrieval/live/RAGAS
commands. Failure counts and per-case results remain explicit. Per-query application
usage and nullable `LLMUsageLog.estimated_cost` remain available; monetary cost needs
configured input/output rates per million tokens and real provider usage. No rate
or cost was fabricated. Optional RAGAS remains outside normal application startup.

## Remaining recommendations and limits

- Docker is unavailable in this Windows environment; COPY inputs were verified,
  but a Docker/MySQL runtime build must be checked on a configured host before deployment.
- A complete final-code 27-question quality comparison remains separate from this
  one-case cleanup smoke run. Preserved reports retain their original limitations.
- Keep local exploratory results under `var/`, and retain deliberate submission
  evidence under `evaluation/reports/`. Do not overwrite baselines for smoke checks.
- Pattern and configured-secret checks are verification aids, not proof against
  every possible secret format.

Existing history was preserved. Two normal local commits separate previously
pending reliability work from repository cleanup. No reset, rebase or push was used.
