# Hugging Face Docker Space

The same backend Docker image targets Render first and can run in a Docker Space.
React is deployed separately on Vercel. The image includes the existing corpus,
reviewed FAISS bundle and pinned CPU embedding model. Gemini logic is unchanged.

## Port and configuration

README metadata selects `sdk: docker` and `app_port: 8000`. The entrypoint uses
`PORT` when provided and otherwise binds `0.0.0.0:8000`; keep the Space port and
PORT consistent. See [Docker Space configuration](https://huggingface.co/docs/hub/spaces-sdks-docker).

Configure runtime Secrets/Variables from [huggingface.env.example](../deploy/huggingface.env.example).
DJANGO_SECRET_KEY is required with DJANGO_DEBUG=false. GEMINI_API_KEY is needed
for generated answers, not model packaging or the health probes. Keep all secrets
out of build arguments, source control and VITE_* variables.

The image defaults to DB_ENGINE=mysql. An intentional DB_ENGINE=sqlite override
supports a single-instance demo, with no MYSQL_* credentials. SQLite defaults to
`/app/var/dev.sqlite3`; optional SQLITE_PATH selects a different location.
Do not change DJANGO_DEBUG to enable SQLite.

For MySQL, provide MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST and
MYSQL_PORT for the actual provider. Spaces' outbound-port restrictions can prevent
conventional MySQL connectivity on 3306; verify provider connectivity and TLS
requirements separately. Changing only the configured port does not tunnel MySQL.
[Space networking](https://huggingface.co/docs/hub/spaces-overview#networking).

Set ALLOWED_HOSTS to the actual assigned Space hostname plus localhost,127.0.0.1.
Set CORS_ALLOWED_ORIGINS to the exact Vercel HTTPS origin. The existing
x-session-token and x-request-id headers are allowed. Configure
CSRF_TRUSTED_ORIGINS for cookie/session authenticated cross-origin POSTs.
Keep SECURE_SSL_REDIRECT=true and TRUST_PROXY_HEADERS=true behind the trusted
Space ingress; direct public access to a backend trusting proxy headers is unsafe.

## Deterministic model and FAISS packaging

The model is sentence-transformers/all-MiniLM-L6-v2 at immutable commit
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. The reviewed index is
`faac7d4df3034bafae61db8e52553481`, containing 139 chunks in 384 dimensions.
The four index files total 363,705 bytes; the 11 model files total 91,578,415 bytes.

scripts/provision_rag_assets.py verifies the corpus, index, metadata, pinned
revision and every model SHA-256. It publishes the offline main reference only
after validation. The build then performs a real local embedding and FAISS search.
The index and manifest hashes are preserved; no ingestion runs at ordinary startup.

The locked Hugging Face client can create a Linux symlink chain from a model
snapshot through its repository blobs into the Hub's shared Xet blob store.
The last target lies outside the model repository. The existing safety check
correctly rejects this layout even when the weight checksum matches.

The CLI and Docker environment select HF_HUB_DISABLE_SHARED_BLOBS=1 so downloads
use repository-local blobs. This retains symlinks, Xet downloads, immutable
revision checks, SHA-256 checks and the existing path-containment requirement.
It changes cache placement only. See [Hub cache layout](https://huggingface.co/docs/huggingface_hub/guides/manage-cache#shared-blobs-across-repos).

HF_HOME=/opt/huggingface and HF_HUB_CACHE=/opt/huggingface/hub keep the model
outside /app/var, owned by navigator. Provisioning explicitly selects this cache
and rejects a snapshot from another location, so download and check share exactly
one layout. Public download uses token=False; HF_HUB_DISABLE_IMPLICIT_TOKEN=1
also prevents implicit credentials. No HF_TOKEN is needed. The build temporarily
sets HF_HUB_OFFLINE=0 and TRANSFORMERS_OFFLINE=0 for downloading; runtime restores
both to 1. Request-time model loading continues using local_files_only=True.
The Docker build installs the locked PyTorch version's CPU wheel rather than
CUDA libraries, and pins Gunicorn in requirements.lock. mysqlclient is retained
for MySQL mode. Compilation dependencies are removed after installation; the
MySQL and numerical runtime libraries remain available.

## Commands and probes

Run from the project root with Docker available:

```powershell
docker build --load -t scholarship-rag-hf .
docker run --rm --network none --entrypoint python scholarship-rag-hf scripts/provision_rag_assets.py --check-model
```

For local startup, copy the example to an ignored .env.hf and fill deployment
values privately. Include localhost,127.0.0.1 in ALLOWED_HOSTS. For an SQLite demo,
set DB_ENGINE=sqlite and omit MYSQL_* values.

```powershell
docker run --rm --name scholarship-rag-hf --env-file .env.hf -p 127.0.0.1:8002:8000 scholarship-rag-hf
curl.exe --fail -H "X-Forwarded-Proto: https" http://127.0.0.1:8002/health/live
curl.exe --fail -H "X-Forwarded-Proto: https" http://127.0.0.1:8002/health/ready
```

The entrypoint migrates, seeds existing operational metadata and collects static
files before executing Gunicorn. Default concurrency is one worker/two threads;
GUNICORN_WORKERS and GUNICORN_THREADS support measured deployment overrides.
WhiteNoise serves collected Django admin static files.

Both /health/live and /health/ready have no trailing slash. The existing
/api/health/live and /api/health/ready aliases are retained. Liveness returns
without a database/model/provider check. Readiness checks SELECT 1, the index
loader and the cached local model dimension; it performs no embedding or Gemini
request. The first readiness call can load assets into the worker. It returns
fixed error codes and HTTP 503 when dependencies are unavailable.
The Docker probe uses liveness; inspect readiness separately.

## Frontend and persistence

Vercel settings: root directory frontend, framework Vite, build npm run build,
output dist. Set VITE_API_BASE to the actual backend HTTPS origin with no trailing
slash or /api suffix. Rebuild after changing it. The frontend adds /api itself.

SQLite stores Django users/sessions, conversation messages, operational metadata,
execution/LLM usage records and evaluation runs. Ephemeral disk loses these
records on restart/redeploy. The corpus/index/model are packaged files rather
than SQL data. Persist the database directory when retaining those records matters.
Do not mount an empty disk over /app/var or /opt/huggingface, which hides packaged
assets. See [Space storage](https://huggingface.co/docs/hub/spaces-storage).

## Verification limits

Current commands and local results are recorded in [DEPLOYMENT_AUDIT.md](DEPLOYMENT_AUDIT.md).
A local Linux image test does not verify a hosted Space or Render deployment,
remote MySQL TLS/connectivity, hosted credentials or sustained Gemini quota.
A single local Linux API/Gemini acceptance query passed; see the audit for scope.
Validate the actual hosted service before announcing it ready.
