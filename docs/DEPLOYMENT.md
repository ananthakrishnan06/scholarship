# Deployment

Local (Python 3.10+, Node 24 LTS):
1. Create a virtual environment and install `requirements.lock` for the tested pinned dependencies. `requirements.txt` records the supported dependency ranges for development; it is the input to `scripts/lock_dependencies.py`.
2. Copy .env.example to .env. Use DJANGO_DEBUG=true / DB_ENGINE=sqlite for local work.
3. Create var/; migrate; seed; ingest the corpus explicitly.
4. Run the Django development server and npm run dev from frontend/.

For MySQL deployments, configure an application database/user in MySQL 8+, utf8mb4
and strict SQL mode. Run the same migrations and ingestion with DB_ENGINE=mysql.
Use python backend/manage.py createsuperuser for authorized ingestion/usage/admin access.
See [Django MySQL guidance](https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes).

Docker: set .env using .env.example, add MYSQL_ROOT_PASSWORD, and set nonempty separate
MYSQL_PASSWORD and DJANGO_SECRET_KEY. Run docker compose up --build -d. The backend
waits for MySQL readiness, migrates and seeds operational metadata. Index explicitly:
docker compose exec backend python backend/manage.py ingest_scholarships.
UI: http://localhost:8080. MySQL and backend are reachable only inside the Docker network.
Persist mysql_data and app_data, which includes the vector index. The pinned model
cache is baked into the image at /opt/huggingface, outside the app_data mount.
Never rebuild the index on ordinary requests.

Production settings are illustrated in deploy/production.env.example; copy values
into a private .env, never commit filled examples. DJANGO_DEBUG=false requires
an explicit DB_ENGINE=mysql or DB_ENGINE=sqlite and a generated secret. Omitting
DB_ENGINE still selects SQLite in debug mode and fails in production. Unknown
engine values fail explicitly. Use a TLS reverse proxy in front of the
loopback-bound frontend and configure the trusted ingress path.

The provided nginx config listens on HTTP for local use and sets forwarded protocol
from its own scheme. For production either terminate TLS in this nginx and configure
its certificate/listener, or replace the protocol header from a strictly trusted
TLS ingress. Set TRUST_PROXY_HEADERS=true only after restricting backend access to
that proxy. Never trust forwarded headers from arbitrary clients. Ensure the health
check is HTTPS-aware (HTTPS URL or trusted forwarded-proto header) when SSL redirect
is enabled. Configure CSRF_TRUSTED_ORIGINS and ALLOWED_HOSTS for the real domain.

Gunicorn serves the API; static Django admin assets are collected into a dedicated
static_data volume and served by nginx. Frontend assets are built into nginx.
Back up MySQL and vector volumes. Restrict admin ingress, schedule session retention,
and run tests/evaluation and deployment health checks before accepting traffic.

Local checks and their exact scope are recorded in DEPLOYMENT_AUDIT.md.
SQLite tests do not establish remote MySQL or hosted-service readiness.
Live LLM setup is optional: LLM_PROVIDER=gemini and GEMINI_API_KEY in private .env.
Measured LLM performance requires credentials and an explicit evaluation run.


Assistant generation requires LLM_PROVIDER=gemini, an available LLM_MODEL and a
backend-only GEMINI_API_KEY. The default example uses gemini-3.5-flash-lite. A normal
answer includes a second grounding-review call. Plan token budgets and provider
quotas accordingly. Index/provider failures return HTTP 503 instead of fake answers.
Migration 0002 removes the legacy personal-profile table and old profile/rule traces.
Existing corpus/vector volumes are retained; source eligibility text remains indexed.

Current demo efficiency defaults are RAG_CONTEXT_MAX_CHARS=10000,
RAG_HISTORY_MAX_CHARS=2000, LLM_GROUNDING_REVIEW=auto and RAG_LOG_QUERY_TEXT=false.
Use always review when stronger semantic scrutiny is preferred over single-call
simple lookups. No vector schema/database migration is needed for domain checks or
internal source links. Ingestion remains the documented command for a missing/stale
index; all 16 application sections are retained. See DEMO_READINESS.md.

## Render demo with SQLite

Use a Render **Docker web service**, with the repository Dockerfile and the project
root as the build context. Leave Render's custom Build Command and Docker Command
empty: the Dockerfile builds the image and its CMD starts the existing entrypoint.
The local equivalents are `docker build --load -t scholarship-rag-hf .` and
`sh /app/backend/entrypoint.sh`. See [Render Docker deployment](https://render.com/docs/docker).
Hosted Render behavior remains unverified until the actual service is redeployed.

Set runtime variables from [render.env.example](../deploy/render.env.example):

```dotenv
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<generated-private-secret>
DB_ENGINE=sqlite
ALLOWED_HOSTS=<actual-render-host>,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=https://<actual-vercel-host>
CSRF_TRUSTED_ORIGINS=https://<actual-vercel-host>
TRUST_PROXY_HEADERS=true
SECURE_SSL_REDIRECT=true
DJANGO_SERVE_STATIC=true
LLM_PROVIDER=gemini
GEMINI_API_KEY=<private-provider-key>
LLM_MODEL=gemini-3.5-flash-lite
GUNICORN_WORKERS=1
GUNICORN_THREADS=2
```

Render supplies PORT (normally 10000). The entrypoint binds `0.0.0.0:$PORT`, or
uses 8000 when PORT is absent for local Docker/Spaces. It migrates, seeds existing
scholarship metadata and collects static files before Gunicorn starts.
The image runs as UID 1000; a custom SQLite directory must be writable by that user.
Keep TLS redirect enabled and trust forwarded HTTPS headers only through the
platform's restricted ingress. ALLOWED_HOSTS cannot be empty or contain * in
production. CORS permits only configured origins; custom session/request headers
remain supported. CSRF_TRUSTED_ORIGINS applies to cookie/session authenticated POSTs.
[Render port binding](https://render.com/docs/web-services#port-binding).

SQLite retains `BASE_DIR / "var" / "dev.sqlite3"`, with the parent created
automatically. Optional SQLITE_PATH accepts project-relative or absolute paths.
MYSQL_* variables are unused in SQLite mode. The image defaults to mysql, so
explicitly set DB_ENGINE=sqlite. No MySQL-to-SQLite fallback is performed.

Set the Render health check path to **/health/live**, with no trailing slash.
It checks Django responsiveness without database, model, Gemini or network access.
Check **/health/ready** separately for SELECT 1, verified index loading and cached
model dimensions. Readiness does no embedding/provider request; the first call
can load assets into its worker. Existing /api/health/live and /api/health/ready
remain valid. [Render health checks](https://render.com/docs/health-checks).

The image builds and verifies the model once using the immutable revision and
SHA-256 values in deploy/rag-assets.json. HF_HUB_DISABLE_SHARED_BLOBS=1 keeps
Linux blob targets inside the existing model path boundary. Runtime
HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 retain local-only model loading;
Gemini still requires HTTPS access. The FAISS bundle is packaged without rebuilding.

SQLite stores Django users and sessions, private conversation messages,
scholarship metadata, execution/usage logs and evaluation runs. An ephemeral
filesystem loses those records on redeploy/restart, while packaged corpus/index/
model files remain in the image. This is acceptable for a disposable hackathon
demo only if losing those records is understood. For persistence, mount a disk
at `/app/var/sqlite` and set `SQLITE_PATH=/app/var/sqlite/db.sqlite3`; ensure it is
writable by UID 1000. Do not mount an empty disk over the entire /app/var, which
would hide the FAISS bundle. Migrate at service startup because Render disks are
available only at runtime, not build/pre-deploy.
[Render persistent disks](https://render.com/docs/disks).

Use one service instance for SQLite. Retain MySQL for multi-instance deployments
or workloads needing more concurrent writes; the MySQL settings and Compose
database service remain supported. Remote MySQL/provider TLS needs separate
validation against the actual endpoint.

## Vercel frontend

Configure Vercel with root directory `frontend`, framework `Vite`, build command
`npm run build` and output directory `dist`. Install using the committed lockfile
(`npm ci`). Set the public build variable:

```dotenv
VITE_API_BASE=https://<actual-render-service>.onrender.com
```

Use the backend origin with no trailing slash or /api suffix; frontend/src/api.ts
adds /api. Configure that frontend HTTPS origin in backend CORS_ALLOWED_ORIGINS.
Rebuild/redeploy after changing VITE_API_BASE. Never put Django, MySQL or Gemini
secrets in VITE_* variables. See [frontend/.env.example](../frontend/.env.example).
The frontend uses hash routes, so no server-side SPA rewrite is needed.

## Optional offline evaluation

RAGAS dependencies are isolated in `evaluation/requirements.lock`; they are not
added to the normal image or startup command. `docker compose up` retains its
existing application behavior. Run the explicit host evaluation command documented
in [EVALUATION.md](EVALUATION.md) with the existing private Gemini configuration,
normal database and persisted FAISS index. No Docker/MySQL runtime acceptance is
claimed by the Windows/SQLite evaluation.


## Hugging Face Docker Space with Vercel

See [HUGGING_FACE.md](HUGGING_FACE.md) for the backend-only image, pinned model and
FAISS assets, runtime Secrets/Variables, separate Vercel configuration and exact
acceptance commands. The image defaults to MySQL; explicit DB_ENGINE=sqlite is
also supported for demos. Spaces outbound port restrictions block conventional
MySQL on 3306; resolve connectivity and provider TLS requirements when choosing
MySQL. The Space image
serves collected Django static files through WhiteNoise when DJANGO_SERVE_STATIC=true.
