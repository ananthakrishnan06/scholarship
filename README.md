---
title: Scholarship Navigator API
sdk: docker
app_port: 8000
---

# Scholarship Navigator

A conversational scholarship assistant powered by retrieval augmented generation.
Ask a question immediately, browse the 16 supplied scholarship records, and read
Gemini-generated explanations with supporting sources. No student profile or
rule-based eligibility matching is required. Eligibility criteria remain in the
unaltered scholarship dataset and are retrieved and explained like other facts.

A local embedding classifier redirects unrelated requests before retrieval or any
provider call. Scholarship questions use sentence-transformer embeddings and the
persisted FAISS index, then send bounded relevant evidence and history to Gemini.
The generated answer is returned directly to React after schema/evidence checks,
with a separate grounding review for complex or uncertain answers. Retrieval/provider failures are explicit errors, never fabricated AI answers.

## Repository layout

```text
backend/       Django API, agent, RAG, validation and schema snapshot
frontend/      React interface, component tests and browser tests
data/          Preserved scholarship corpus, JSONL projection and QA report
evaluation/    Benchmarks, RAGAS adapters, scripts and retained reports
docs/          Architecture, API, data, evaluation and deployment documentation
scripts/       Dependency and repository verification tools
tests/         Backend and evaluation regression tests
deploy/        Reverse proxy and production configuration template
```

The runtime corpus is `data/scholarship_dataset_ready.json`; the original-record
corpus is also retained for provenance checks. [Dataset documentation](docs/DATASET.md)
explains all four preserved data files. The public response-schema snapshot lives
at `backend/schemas/assistant_response_schema.json`; Python Pydantic models remain
the runtime validators. Dockerfiles, Compose and dependency manifests stay at the
root. Install `requirements.lock` for the tested dependency versions;
`requirements.txt` contains the supported development ranges, and `pyproject.toml`
configures the existing test and lint tools. No dependency versions changed.

The supplied `README (1).md` contained unique instructions for the retired
eligibility engine. Its original bytes are retained in
[the historical documentation](docs/history/ELIGIBILITY_ENGINE.md); those examples
refer to the old architecture. This README remains the current entry point.
See [the repository cleanup audit](docs/REPOSITORY_CLEANUP.md) for moves and checks.

## Run this Windows workspace

From `D:\social-hackthon\social-hackthon`, configure the ignored `.env`:

```dotenv
DB_ENGINE=sqlite
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=your_private_key
```

Your existing working key and SQLite configuration can be retained. Never put
credentials in `.env.example`, frontend code, or chat. Other configuration defaults
are documented in [.env.example](.env.example).

Backend terminal:

```powershell
cd D:\social-hackthon\social-hackthon
python backend/manage.py migrate
python backend/manage.py runserver 127.0.0.1:8000
```

Frontend terminal:

```powershell
cd D:\social-hackthon\social-hackthon
$env:PATH = "$PWD\var\tools\node-v24.21.0-win-x64;" + $env:PATH
npm.cmd --prefix frontend run dev
```

Open http://127.0.0.1:5173/#/assistant. API docs: http://127.0.0.1:8000/api/docs.
The migration removes saved personal profiles and strips old rule traces from
historical assistant messages. Conversation questions and sourced answer text remain.

For a fresh checkout: Python 3.10+, install `requirements.lock` in a virtual
environment, create `.env` and `var`, migrate, seed and ingest:

```powershell
python -m pip install -r requirements.lock
python backend/manage.py migrate
python backend/manage.py seed_scholarships
python backend/manage.py ingest_scholarships
npm.cmd --prefix frontend ci
```

Use an installed Node 24 LTS or `python scripts/install_node.py`. The existing
lockfile uses an HTTPS npm mirror because the default registry was unreachable in
this workspace; package integrity hashes are retained.

## Request and response

`POST /api/agent/query` and `/api/rag/query` run the same conversational RAG flow:

```json
{"question":"How much does Pragati provide?"}
```

Responses contain `answer`, `sources`, `status`, optional `error`, and request/session
identifiers. Status is `success`, `out_of_scope`, `insufficient_evidence`, or `error`.
The scholarship answer is generated text; out-of-domain requests get a brief
scholarship-only redirection with no provider call. Source names, URLs and exact supporting excerpts
come from retrieved records, never model-invented citations. Each source has a
View Full Scheme link to its existing internal detail page; missing official links stay missing.
Failures use HTTP 503 and a clear error. Matching/profile endpoints have been removed.

The assistant can explain benefits, criteria, documents, procedures, conflicting
information, and missing deadlines. Follow-up questions use private conversation
history. Voluntarily supplied circumstances may be discussed, but the scholarship
authority makes the final eligibility/award decision.

## Verification

```powershell
python -m pytest -q
python -m ruff check backend tests scripts evaluation
python backend/manage.py check
python backend/manage.py spectacular --validate --file var/openapi.yaml
python scripts/verify_repository.py
python evaluation/run_eval.py
python evaluation/check_retrieval_efficiency.py
python evaluation/run_eval.py --live --cases evaluation/demo_cases.json --delay 15 --output evaluation/reports/demo_live.json
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run e2e
```

Unit/browser tests do not call live Gemini. Browser tests use Edge and isolated
ports 8001/5174. The demo live evaluation covers normal queries, procedures, discovery/comparison,
missing dates, ambiguity and off-topic requests. It records actual tokens and call
budgets; out-of-topic cases make zero provider calls. Original 16-case RAG fixtures
remain available through the default live command.
[Current demo/efficiency report](docs/DEMO_READINESS.md),
[optimized retrieval](evaluation/reports/retrieval_optimized.json),
[live demo](evaluation/reports/demo_live.json), and
[local domain/context checks](evaluation/reports/efficiency.json) record actual results.
The [earlier refactor report](docs/RAG_REFACTOR.md) remains as historical evidence.

## Deployment and limits

With `DJANGO_DEBUG=false`, explicitly select `DB_ENGINE=mysql` or `DB_ENGINE=sqlite`
and provide a Django secret. SQLite supports Render demos using `var/dev.sqlite3`
(or optional `SQLITE_PATH`); its parent directory is created automatically.
Docker Compose keeps MySQL and persists the database, index
and static assets in volumes; the pinned model cache is baked into the image. See [deployment](docs/DEPLOYMENT.md).
See [the deployment audit](docs/DEPLOYMENT_AUDIT.md) for current local Linux verification
and remaining hosted-service/MySQL/provider checks.

Generated language is checked by schema validation, exact evidence membership, generic numeric checks,
and selective model grounding review. Set `LLM_GROUNDING_REVIEW=always` to review
every generation; default `auto` avoids a second call on simple lookups. This reduces unsupported claims but is not
a mathematical guarantee of correct paraphrases or complete discovery. Provider
quotas and network outages return errors. The dataset is a supplied snapshot, not
live official scholarship updates. English embeddings are retained; multilingual
retrieval quality has not been established.

[Architecture](docs/ARCHITECTURE.md) | [RAG](docs/RAG.md) | [API](docs/API.md) |
[Agent](docs/AGENT.md) | [Security](docs/SECURITY.md) | [Evaluation](docs/EVALUATION.md)

## Efficiency settings

`RAG_CONTEXT_MAX_CHARS=10000` bounds deduplicated source text;
`RAG_HISTORY_MAX_CHARS=2000` bounds recent conversation text, within the existing
`LLM_MAX_INPUT_CHARS=24000` total request limit. Local semantic section classification
selects narrow evidence for focused queries and a bounded shortlist for discovery.
`LLM_GROUNDING_REVIEW=auto` uses one generation for simple amount/document/procedure
lookups, with review for conflicts, eligibility, comparisons, missing information,
multiple schemes and user-suggested numbers. `always` provides stronger review at
higher cost. Both policies can still miss unsupported paraphrases.

Metrics record domain scores, query fingerprint, chunk/character counts, final
context size, actual provider input/output tokens and latency. Optional
`RAG_LOG_QUERY_TEXT=true` enables query text with common credentials redacted; keep
it false for normal operation. The configured provider/model/key are unchanged.

## Offline RAGAS evaluation

The existing evaluation command now has an explicit `--ragas --live` mode. It
calls the same production `query()` workflow used by the API, captures actual
FAISS chunks/scores and Gemini answers, then runs RAGAS Faithfulness, Answer
Relevancy, Context Precision and Context Recall. RAGAS never runs during normal
user requests. The existing domain gate skips retrieval/provider calls for clear
unrelated questions; those and clarification are evaluated separately.

Install the optional locked dependencies in an isolated environment; normal
application dependencies and Docker startup remain unchanged:

```powershell
python -m venv --system-site-packages var/eval-venv
.\var\eval-venv\Scripts\python.exe -m pip install -r evaluation/requirements.lock
.\var\eval-venv\Scripts\python.exe evaluation/run_eval.py --ragas --live --delay 20 --judge-delay 4
```

Keep the working private Gemini key/model in the ignored `.env`. This command
makes real application and judge requests and consumes provider tokens. The
27-question benchmark in `evaluation/ragas_cases.json` covers all 16 schemes;
references and context IDs are verified against the unchanged source corpus.
Results are saved to `evaluation/reports/ragas_results.json` and the automatically
generated [RAG Evaluation Report](evaluation/reports/RAG_EVALUATION_REPORT.md).

Use `--resume` to reuse validated captures/completed metrics after interruption.
Pacing can increase; changes are recorded. Add `--retry-failed` to retry transient
rate/network/timeout failures once, preserving prior attempts and all costs.
Rejected factual output is retained as a failure. `--only ID --output var/pilot.json`
selects a focused real run. Scores use successful measurements only; failures,
missing usage and skipped metrics are explicit. Read score denominators and the
failure table before interpreting an average. These measurements are not a proof
of correctness or official eligibility decisions.

Pydantic validates requests, response/status consistency, source URLs/identities,
retrieved chunks, benchmark references and serialized evaluation results. It
encodes no scholarship-specific eligibility rules. See
[the evaluation guide](docs/EVALUATION.md) for versions, methodology and limits.


The targeted reliability verification and the separately preserved quota-exhausted
full run are documented in [docs/QUALITY_FIX.md](docs/QUALITY_FIX.md). The baseline
RAGAS report remains unchanged; a complete comparable rerun requires available
Gemini quota. Daily quota exhaustion is reported immediately and is not retried.


## Hugging Face backend Space

The Docker image packages the reviewed FAISS bundle and a pinned MiniLM snapshot
for offline local embeddings. React remains on Vercel; the image defaults to MySQL,
with explicit SQLite available for single-instance demos.
See [Space setup, variables, commands and blockers](docs/HUGGING_FACE.md).
A normal remote MySQL endpoint on port 3306 is blocked by Spaces networking.
The entrypoint honors Render's PORT and retains port 8000 by default for Spaces.
See [the deployment audit](docs/DEPLOYMENT_AUDIT.md) for tested behavior and limits.

## Render backend and Vercel frontend

Use the repository Dockerfile for a Render Docker web service. Explicitly set
DB_ENGINE=sqlite, keep DJANGO_DEBUG=false, and supply DJANGO_SECRET_KEY and the
actual ALLOWED_HOSTS. Set LLM_PROVIDER=gemini and GEMINI_API_KEY for generated
answers. Configure CORS_ALLOWED_ORIGINS for the real Vercel origin. See
[deploy/render.env.example](deploy/render.env.example) and
[complete deployment instructions](docs/DEPLOYMENT.md#render-demo-with-sqlite).

The entrypoint migrates, seeds metadata, collects static files and binds Gunicorn
to PORT, with 8000 as the Spaces/local default. /health/live is the cheap Render
probe; /health/ready checks database, index and local model availability.
SQLite data needs persistent storage to survive restarts/redeploys.

Vercel: root frontend, build npm run build, output dist. Set
VITE_API_BASE=https://<actual-render-service>.onrender.com without a trailing slash
or /api. No backend secrets belong in frontend variables.

The model build keeps the same immutable revision and all checksum checks.
Repository-local Hub blobs avoid Linux shared-Xet symlink escapes. The image uses
the same pinned PyTorch version's CPU wheel. Current verification and remaining
limits are in [the deployment audit](docs/DEPLOYMENT_AUDIT.md).
