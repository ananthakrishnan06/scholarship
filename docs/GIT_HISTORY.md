# Git repository and history audit

Audited on 2026-10-01. The actual source repository is
`D:\social-hackthon\social-hackthon`; its parent `D:\social-hackthon` contains only
this project folder. The user chose to keep the existing repository here.
No second repository was initialized, no history was rewritten, and nothing was pushed.

## Project inventory

| Component | Tracked paths |
|---|---|
| Backend and API | `backend/config`, `backend/api`, `backend/apps/navigator` |
| RAG, agent and Gemini integration | `backend/core/rag`, `backend/core/agent`, `backend/core/llm.py` |
| Dataset and provenance | `data/scholarship_dataset_ready.json`, `.jsonl`, QA report, `data/combined_scholarship_schemes_cleaned.json` |
| Frontend | `frontend/src`, `frontend/e2e`, package manifests, Vite/TypeScript configuration |
| Tests and evaluation | `tests`, `evaluation`, saved reproducible reports |
| Configuration templates | `.env.example`, `deploy/production.env.example` |
| Documentation | `README.md`, `docs`; the supplied eligibility-engine README is now `docs/history/ELIGIBILITY_ENGINE.md` |
| Deployment and tooling | Dockerfiles, Compose, `deploy/nginx.conf`, dependency locks, `scripts` |

## Safety and verification

- The working tree was clean before this audit. Existing commits are meaningful
  implementation stages and remain unchanged, including the historical rule-engine
  implementation and its subsequent removal. No fabricated stages were added.
- All 17 existing commits and 223 unique reachable file blobs were scanned for
  recognizable Gemini/OpenAI, GitHub, AWS and Slack credentials and private-key
  headers. No matches or prohibited generated/private paths were found. This is
  a pattern-based scan, not proof that every possible credential format is absent.
  An additional exact-value check found no configured private credentials in those
  historical blobs; no secret values were printed.
- `git fsck --full` passed. No configured remote exists. The largest historical blob
  is the 217390-byte supplied dataset; no oversized dependency or model blobs were found.
- The private `.env`, runtime `var`, dependencies and caches remain ignored.
  Ignore rules now also cover other environment-file names, credentials, virtual
  environments, generated packaging/build output, IDE files and temporary files.
  Both committed environment templates retain empty secret values.
- Before the audit commit, repository/source/schema verification passed for all
  122 staged files and 16 records. Ignore assertions passed for 61 private/generated
  paths, 13 source/template paths and every staged file; sensitive fields in both
  templates are empty. `git diff --cached --check` passed. No application code,
  dataset, dependencies or runtime behavior changes in this audit, so application
  tests need no rerun.

## Existing commits and their changed files

The following is a historical Git snapshot. Paths here intentionally retain their
names at the time of those commits; current paths are listed in the inventory
above and [the cleanup audit](REPOSITORY_CLEANUP.md).

Entries are chronological and include additions, modifications and deletions
(`A`, `M`, `D`); a deleted historical file is not a file in the current checkout.
These are the real existing commits, not newly reconstructed development stages.

### 6653d09 Initial commit

```text
A	.gitattributes
```

### d3fa3e6 chore: initialize scholarship navigator architecture

```text
A	.env.example
A	.gitignore
A	README.md
A	backend/apps/__init__.py
A	backend/config/__init__.py
A	backend/core/__init__.py
A	backend/manage.py
A	docs/AUDIT.md
A	pyproject.toml
A	requirements.txt
A	tests/test_foundation.py
```

### 38597ab feat: preserve scholarship corpus and add validated profile schemas

```text
A	README (1).md
A	backend/core/corpus.py
A	backend/core/schemas.py
A	combined_scholarship_schemes_cleaned.json
A	eligibility_engine.py
A	scholarship_dataset_QA_report.json
A	scholarship_dataset_ready.json
A	scholarship_dataset_ready.jsonl
A	student_profile_schema.json
```

### 358b64d feat: implement conservative generic eligibility rules

```text
A	backend/core/eligibility.py
A	docs/ELIGIBILITY_ENGINE.md
```

### 4343ea4 test: cover missing values contradictions and rule operators

```text
A	tests/test_eligibility.py
```

### 54b263d feat: add Django APIs MySQL models and private session memory

```text
M	.env.example
A	backend/api/__init__.py
A	backend/api/common.py
A	backend/api/urls.py
A	backend/api/views.py
A	backend/apps/navigator/__init__.py
A	backend/apps/navigator/admin.py
A	backend/apps/navigator/management/__init__.py
A	backend/apps/navigator/management/commands/__init__.py
A	backend/apps/navigator/management/commands/seed_scholarships.py
A	backend/apps/navigator/migrations/0001_initial.py
A	backend/apps/navigator/migrations/__init__.py
A	backend/apps/navigator/models.py
A	backend/config/settings.py
A	backend/config/urls.py
A	backend/config/wsgi.py
A	backend/core/memory.py
A	backend/core/observability.py
M	backend/manage.py
A	docs/API.md
A	tests/test_api.py
```

### c621563 feat: index provenance-preserving scholarship chunks in FAISS

```text
A	backend/apps/navigator/management/commands/ingest_scholarships.py
A	backend/core/rag/__init__.py
A	backend/core/rag/documents.py
A	backend/core/rag/embeddings.py
A	backend/core/rag/retrieval.py
A	backend/core/rag/vector_store.py
A	docs/RAG.md
A	tests/test_rag.py
```

### 0c0e414 feat: add bounded grounded agent with validated provider fallbacks

```text
M	.env.example
A	backend/api/assistant.py
M	backend/api/urls.py
A	backend/core/agent/__init__.py
A	backend/core/agent/tools.py
A	backend/core/agent/workflow.py
A	backend/core/llm.py
A	docs/AGENT.md
A	tests/test_agent.py
```

### 4df5aa9 fix: harden source integrity uncertainty session access and API schemas

```text
M	.env.example
M	backend/api/common.py
M	backend/api/views.py
A	backend/apps/navigator/management/commands/purge_sessions.py
M	backend/config/settings.py
M	backend/core/agent/tools.py
M	backend/core/agent/workflow.py
M	backend/core/corpus.py
M	backend/core/eligibility.py
M	backend/core/memory.py
M	backend/core/rag/embeddings.py
M	backend/core/rag/retrieval.py
M	backend/core/schemas.py
M	docs/API.md
M	docs/ELIGIBILITY_ENGINE.md
M	student_profile_schema.json
M	tests/test_agent.py
M	tests/test_api.py
M	tests/test_eligibility.py
```

### b909c08 feat: build React scholarship workspace with tested browser flows

```text
M	.gitignore
A	frontend/Dockerfile
A	frontend/e2e/navigator.spec.ts
A	frontend/index.html
A	frontend/package-lock.json
A	frontend/package.json
A	frontend/playwright.config.ts
A	frontend/src/App.tsx
A	frontend/src/Assistant.tsx
A	frontend/src/ProfileForm.tsx
A	frontend/src/api.ts
A	frontend/src/components.test.tsx
A	frontend/src/components.tsx
A	frontend/src/main.tsx
A	frontend/src/style.css
A	frontend/src/test-setup.ts
A	frontend/src/types.ts
A	frontend/src/vite-env.d.ts
A	frontend/tsconfig.json
A	frontend/vite.config.ts
A	scripts/install_node.py
```

### f043784 test: add reproducible scholarship RAG evaluation and latency report

```text
A	docs/EVALUATION.md
A	evaluation/expected_results.json
A	evaluation/profiles.json
A	evaluation/questions.json
A	evaluation/reports/latest.json
A	evaluation/run_eval.py
```

### 12d3d58 chore: add Docker deployment and tested dependency locks

```text
A	.dockerignore
M	.gitattributes
A	Dockerfile
A	backend/entrypoint.sh
A	deploy/nginx.conf
A	deploy/production.env.example
A	docker-compose.yml
A	docs/DEPLOYMENT.md
A	requirements.lock
A	scripts/lock_dependencies.py
```

### d108f1a refactor: split scholarship workspace into focused screen components

```text
M	frontend/src/App.tsx
A	frontend/src/Dashboard.tsx
A	frontend/src/ScholarshipDetail.tsx
A	frontend/src/ScholarshipList.tsx
A	frontend/src/Workspace.tsx
A	frontend/src/navigation.ts
```

### d8698e6 docs: record architecture setup and verified acceptance status

```text
M	README.md
A	docs/ARCHITECTURE.md
A	docs/DATASET.md
A	docs/SECURITY.md
A	docs/VERIFICATION.md
A	scripts/verify_repository.py
```

### a33fe6c fix: send compatible Gemini JSON schema and report provider failures

```text
M	backend/core/llm.py
M	docs/AGENT.md
A	tests/test_llm.py
```

### 2f14299 refactor: deliver conversational RAG answers and remove profile rules

```text
M	.env.example
M	README.md
A	assistant_response_schema.json
M	backend/api/assistant.py
A	backend/api/renderers.py
M	backend/api/urls.py
M	backend/api/views.py
A	backend/apps/navigator/migrations/0002_remove_profiles_and_track_llm_phase.py
M	backend/apps/navigator/models.py
M	backend/config/settings.py
M	backend/core/agent/tools.py
M	backend/core/agent/workflow.py
M	backend/core/corpus.py
D	backend/core/eligibility.py
M	backend/core/llm.py
M	backend/core/memory.py
M	backend/core/rag/retrieval.py
M	backend/core/schemas.py
M	deploy/production.env.example
M	docs/AGENT.md
M	docs/API.md
M	docs/ARCHITECTURE.md
M	docs/AUDIT.md
M	docs/DATASET.md
M	docs/DEPLOYMENT.md
D	docs/ELIGIBILITY_ENGINE.md
M	docs/EVALUATION.md
M	docs/RAG.md
A	docs/RAG_REFACTOR.md
M	docs/SECURITY.md
M	docs/VERIFICATION.md
D	eligibility_engine.py
D	evaluation/profiles.json
A	evaluation/rag_cases.json
A	evaluation/reports/focused_rag.json
M	evaluation/reports/latest.json
A	evaluation/reports/live_browser.json
A	evaluation/reports/live_rag.json
M	evaluation/run_eval.py
M	frontend/e2e/navigator.spec.ts
M	frontend/playwright.config.ts
M	frontend/src/App.tsx
M	frontend/src/Assistant.tsx
M	frontend/src/Dashboard.tsx
D	frontend/src/ProfileForm.tsx
M	frontend/src/ScholarshipDetail.tsx
M	frontend/src/ScholarshipList.tsx
M	frontend/src/Workspace.tsx
M	frontend/src/api.ts
M	frontend/src/components.test.tsx
M	frontend/src/components.tsx
M	frontend/src/types.ts
M	frontend/vite.config.ts
M	scripts/verify_repository.py
D	student_profile_schema.json
A	tests/conftest.py
M	tests/test_agent.py
M	tests/test_api.py
D	tests/test_eligibility.py
M	tests/test_llm.py
M	tests/test_rag.py
```

### 41f5892 feat: optimize scholarship RAG and add semantic domain and source navigation

```text
M	.env.example
M	README.md
M	backend/core/agent/tools.py
M	backend/core/agent/workflow.py
M	backend/core/llm.py
M	backend/core/observability.py
A	backend/core/quantities.py
M	backend/core/rag/embeddings.py
A	backend/core/rag/query.py
M	backend/core/rag/retrieval.py
M	backend/core/schemas.py
M	deploy/production.env.example
M	docs/AGENT.md
M	docs/API.md
M	docs/ARCHITECTURE.md
A	docs/DEMO_READINESS.md
M	docs/DEPLOYMENT.md
M	docs/EVALUATION.md
M	docs/RAG.md
M	docs/RAG_REFACTOR.md
M	docs/SECURITY.md
M	docs/VERIFICATION.md
A	evaluation/check_retrieval_efficiency.py
A	evaluation/demo_cases.json
M	evaluation/rag_cases.json
A	evaluation/reports/demo_browser.json
A	evaluation/reports/demo_focused.json
A	evaluation/reports/demo_initial.json
A	evaluation/reports/demo_live.json
A	evaluation/reports/efficiency.json
A	evaluation/reports/grounding_replay.json
A	evaluation/reports/retrieval_optimized.json
M	evaluation/run_eval.py
M	frontend/e2e/navigator.spec.ts
M	frontend/src/ScholarshipDetail.tsx
M	frontend/src/ScholarshipList.tsx
M	frontend/src/components.test.tsx
M	frontend/src/components.tsx
M	frontend/src/navigation.ts
M	frontend/src/types.ts
M	tests/conftest.py
M	tests/test_agent.py
A	tests/test_quantities.py
A	tests/test_query.py
M	tests/test_rag.py
```

## Audit changes added after that history

One commit, `chore: harden Git ignore rules and document repository audit`, includes
only these real changes:

- `.gitignore`: extend private/generated/IDE exclusions while keeping templates tracked.
- `docs/GIT_HISTORY.md`: this inventory, history/file listing, safety findings and next steps.

There are no empty commits, history rewrites, project moves or application changes.
For the current graph and working-tree status, run from the actual repository:

```powershell
git status
git log --oneline --decorate --graph
git log --reverse --format="%h %s" --name-status
```

## Before a future GitHub push

- No repository-hygiene blocker was found by this audit; run
  `python scripts/verify_repository.py` again after future changes.
- No Git remote is configured. The owner still needs to choose a GitHub repository,
  access/visibility and license or redistribution permissions for the supplied data.
  Dataset provenance is retained, but this audit is not a licensing determination.
- Keep the real `.env` and local runtime files private. A scanner can miss unfamiliar
  formats; GitHub secret scanning or an independent scan can supplement this check.
- MySQL/Docker production runtime validation remains pending as documented in
  `docs/DEPLOYMENT.md`. This is a deployment limitation, not a blocker to sharing
  the source repository.
- Pushing is not authorized by this request; no push was performed.
