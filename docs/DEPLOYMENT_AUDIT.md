# Deployment audit

Audit date: 2026-10-02 (Asia/Calcutta). Local Linux acceptance passed. The actual
Render and Hugging Face services have not been deployed by this audit.

## Latest Render model provisioning verification

This narrower follow-up changes exactly these five repository files:

- scripts/provision_rag_assets.py
- Dockerfile
- tests/test_deployment.py
- docs/HUGGING_FACE.md
- docs/DEPLOYMENT_AUDIT.md

The earlier audit changes below remain in the workspace. Database settings,
health endpoints, startup, private .env, pinned manifest/index and every RAG
module were compared with their pre-follow-up SHA-256 values and are unchanged.

Fresh Linux reproduction with shared blobs enabled downloaded all 11 files,
verified that every SHA-256 still matches the unchanged manifest, then reproduced:
`ValueError: Unsafe model asset path: model.safetensors`. Its target is in the
cache-wide shared blob store, outside the model repository. This confirms the
exact failure rather than inferring a checksum mismatch from the generic log.
The original handler omitted the reason; current diagnostics include it safely.

Shared blobs remain disabled before Hub imports. The downloader now explicitly
selects the same Hub cache used by --check-model, passes token=False for the public
model, and rejects any returned snapshot outside that exact revision/cache
location before publishing refs/main. Docker explicitly sets
HF_HUB_CACHE=/opt/huggingface/hub and HF_HUB_DISABLE_IMPLICIT_TOKEN=1. All eleven
resolved files and their snapshot are owned by navigator (UID 1000), and every
resolved file remains inside the model repository. No HF_TOKEN is needed.

Latest actual results:

| Check | Result |
| --- | --- |
| Fresh local download with Docker-equivalent online flags, no HF_TOKEN | Passed |
| Local --check-model with offline flags in the same fresh cache | Passed |
| docker build --progress=plain --load -t scholarship-rag-hf . | Completed successfully, exit 0 |
| Both Linux Docker provisioning RUN stages | Executed freshly and passed |
| Image --check-model with --network none | Passed; 139 chunks, 384 dimensions |
| All 11 image checksums, repo containment, navigator ownership and offline cache/flags | Passed |
| Production container startup on PORT=10000; /health/live | Passed; HTTP 200 |
| /health/ready, /api aliases, static files, sessions, CORS and real offline retrieval | Passed; 2 evidence chunks |
| Real Linux RAG API/Gemini request | HTTP 200, success, 2 supporting sources |
| Focused database/deployment tests | 53 passed, 3 Windows skips |
| python -m pytest -q | 160 passed, 11 skipped |
| Full Linux image suite | 163 passed, 8 optional evaluation skips |
| Ruff, hygiene and diff whitespace | Passed |

The eight optional evaluation cases were already covered by the earlier separate
evaluation environment. The three Windows symlink/shell skips execute on Linux.
Frontend files were untouched in this follow-up, so frontend tests/build were not
rerun; their earlier passing results remain recorded below.

The Docker secret-name heuristic warns about the boolean
HF_HUB_DISABLE_IMPLICIT_TOKEN flag; its value is 1 and contains no credential.
Runtime keeps HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1, and the entrypoint has
no model download. The pinned revision, every manifest checksum and FAISS/RAG
logic remain unchanged.

The supplied Render log still prints only the exception type and refers to the
older Dockerfile location. It is consistent with the old handler/build source.
Render must receive and deploy the changed source revision; an actual hosted
Render rebuild remains UNVERIFIED. No commit or push was performed.
The exact changes for this follow-up are saved in ignored
var/render-model-fix.patch, relative to the pre-follow-up working tree.

## Root cause and preserved integrity

The locked huggingface-hub 1.33.0 / hf-xet 1.6.0 client creates a Linux snapshot
symlink chain through repository blobs into the cache-wide shared Xet blob store.
The model.safetensors target escapes the existing model-repository boundary.
The original exception is **ValueError: Unsafe model asset path.** It is a cache
layout failure, not a checksum mismatch. Windows copies the files when symlink
privileges are unavailable, explaining the successful local checks.

A clean Linux reproduction confirmed this failure and compared all 11 actual
SHA-256 values with deploy/rag-assets.json: every value matched. Public upstream
metadata confirmed the immutable revision and weight digest. The CLI and Docker
image now set HF_HUB_DISABLE_SHARED_BLOBS=1 before Hub imports, selecting
repository-local blobs while preserving Xet transport and every original
checksum, revision and path-containment check. Diagnostics expose the validation
reason and filename while redacting configured credentials, tokens and URLs.
See [the Hub cache documentation](https://huggingface.co/docs/huggingface_hub/guides/manage-cache#shared-blobs-across-repos).

Preserved assets:

- Model: sentence-transformers/all-MiniLM-L6-v2.
- Immutable revision: 1110a243fdf4706b3f48f1d95db1a4f5529b4d41.
- Weight SHA-256: 53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db.
- Index: faac7d4df3034bafae61db8e52553481; 139 chunks, 384 dimensions.
- Four FAISS/index assets: 363,705 bytes; 11 model assets: 91,578,415 bytes.
- Committed corpus and all four committed index blobs match the manifest exactly.
- No index regeneration, manifest change, model revision change or core RAG change.

## Changes

Production SQLite support already existed at the start of this broader audit and
remains intact. DB_ENGINE=sqlite uses var/dev.sqlite3 without MYSQL_* variables;
SQLITE_PATH supports relative/absolute overrides and creates the parent directory.
Production requires a secret and an explicit database engine. MySQL keeps its
existing credentials, utf8mb4, strict SQL mode and connection lifetime without
falling back to SQLite.

The audit additionally fixes production host/origin parsing, rejects wildcard or
empty production hosts, and accepts case-insensitive TRUST_PROXY_HEADERS values.
Existing authentication and custom CORS headers remain supported. Root health
aliases preserve the existing /api routes. Liveness has no database/model/provider
dependency; readiness performs no embedding or Gemini request, but can load local
assets on its first call.

Gunicorn respects PORT, defaults to 8000 for Spaces, and supports worker/thread
configuration. Migrations, seeding and static collection precede its exec. Compose
retains port 8000 and probes lightweight liveness with the internal HTTPS header.
The backend image retains the locked PyTorch base version 2.14.1 using its CPU
wheel, avoiding CUDA downloads. Gunicorn is pinned to 23.0.0. Other dependency
versions are unchanged. HTTPS apt downloads replaced failing local HTTP transfers;
C compilation dependencies are removed after mysqlclient installation while
necessary runtime libraries remain. No Node.js or private environment is copied.

Changed files (21):

- .dockerignore; .env.example; Dockerfile; docker-compose.yml; requirements.lock.
- backend/config/settings.py; backend/config/urls.py; backend/entrypoint.sh.
- scripts/provision_rag_assets.py; scripts/verify_repository.py.
- tests/test_database_settings.py; tests/test_deployment.py.
- deploy/render.env.example; deploy/production.env.example; deploy/huggingface.env.example.
- frontend/.env.example.
- README.md; docs/DEPLOYMENT.md; docs/HUGGING_FACE.md; docs/SECURITY.md; docs/DEPLOYMENT_AUDIT.md.

## Earlier complete audit verification

| Check | Result |
| --- | --- |
| python backend/manage.py check | Passed, no issues |
| Focused database/deployment tests | 52 passed, 3 Windows skips |
| python -m pytest -q (standard Windows environment) | 159 passed, 11 skipped |
| Full suite with optional evaluation environment | 167 passed, 3 Windows skips |
| Full Linux image suite, networking disabled | 162 passed, 8 optional evaluation skips |
| python scripts/provision_rag_assets.py --check-model | Passed, real embedding and FAISS evidence |
| python scripts/provision_rag_assets.py --download-model | Passed, pinned files verified |
| Strict Django --deploy --fail-level WARNING, SQLite and MySQL | Passed on host and Linux |
| Docker build, including both model provisioning stages | Passed, exit 0 |
| docker run --rm --network none --entrypoint python scholarship-rag-hf scripts/provision_rag_assets.py --check-model | Passed |
| Production SQLite, networking disabled, PORT=10000, no MySQL variables | Migrations, seed, static collection and Gunicorn passed |
| Root and /api liveness/readiness; /api/health; admin CSS | All HTTP 200 |
| Real offline retrieval in the image | 2 evidence chunks, no warnings |
| Session creation/protection/deletion; search; off-domain query | Passed |
| CORS custom-header preflight, denied origins, hosts and HTTPS redirect | Passed |
| Dynamic-port Docker healthcheck | Healthy |
| Real isolated MySQL 8.4 server | Migrations, 16 seeded records, Gunicorn, readiness/API and strict checks passed |
| One real Linux API/Gemini query | HTTP 200, success, 4 supporting source excerpts |
| Non-root UID, CPU torch, mysqlclient library import, image hygiene | Passed |
| Frontend lint and production build with configured Render origin | Passed |
| Frontend component suite | 7 passed |
| docker compose config --quiet | Passed with temporary generated database secrets |
| Repository hygiene, configured-secret scan, Ruff and diff whitespace | Passed |

The Windows skips are missing symlink privileges and two Linux shell cases; the
Linux suite executes those three cases successfully. The eight optional RAGAS
cases run successfully in the separate host evaluation environment. No live
provider is called by the unit suites. The separate acceptance query used the
existing private Gemini configuration through runtime environment variables;
only sanitized status/count results were retained.

Two verification harness defects were corrected: a real unsafe POST is rejected
by production CSRF with 403 before the view's 405 method guard, and the Linux
suite needs a read-only mount of the test-only lock_dependencies helper. The
application's CSRF protection and runtime image were unchanged for these fixes.

## Render and Vercel configuration

Use a Render Docker web service at the project root. Leave custom Build Command
and Docker Command blank, allowing Dockerfile and CMD to run. Local equivalent:
`docker build --load -t scholarship-rag-hf .`; image start:
`sh /app/backend/entrypoint.sh`. Render supplies PORT. Set health path /health/live.

Copy runtime variable names from [render.env.example](../deploy/render.env.example).
Supply DJANGO_DEBUG=false, a generated private DJANGO_SECRET_KEY, DB_ENGINE=sqlite,
actual ALLOWED_HOSTS, actual HTTPS CORS_ALLOWED_ORIGINS/CSRF_TRUSTED_ORIGINS,
TRUST_PROXY_HEADERS=true, SECURE_SSL_REDIRECT=true, DJANGO_SERVE_STATIC=true,
LLM_PROVIDER=gemini, private GEMINI_API_KEY and the configured LLM_MODEL.
Use GUNICORN_WORKERS=1 and GUNICORN_THREADS=2. Model/index/offline paths and flags
are already set in the image. No MYSQL_* variables are required for SQLite.

Vercel: root frontend; Vite; npm ci; npm run build; output dist. Set
`VITE_API_BASE=https://<actual-render-service>.onrender.com`, without a trailing
slash or /api. Put that exact frontend HTTPS origin in the backend CORS setting.

SQLite stores users/sessions, conversations, operational metadata, execution/usage
records and evaluation state. Ephemeral storage loses these on restart/redeploy.
For persistence, mount /app/var/sqlite, ensure UID 1000 can write, and set
SQLITE_PATH=/app/var/sqlite/db.sqlite3. Avoid covering the packaged var/index.

## Remaining verification limits

- **UNVERIFIED:** actual hosted Render/Space/Vercel deployment and public ingress.
- **UNVERIFIED:** remote MySQL provider connectivity/TLS; local MySQL compatibility passed.
- **UNVERIFIED:** persistent-disk ownership, backup/restore and restart behavior on the actual service.
- **UNVERIFIED:** full Compose/nginx stack; configuration and standalone MySQL acceptance passed.
- **UNVERIFIED:** production load, peak memory and sustained Gemini quota/capacity.
  A warm one-worker SQLite backend measured approximately 452 MiB locally; this
  is not a peak-memory or target-service capacity guarantee.

There is no outstanding local acceptance failure. Hosted acceptance must still
be performed with actual hostnames, secrets and service resources. Nothing is
staged, committed or pushed; Git history and the private .env are unchanged.
