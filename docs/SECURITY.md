# Security and privacy

API keys, database credentials and Django secrets are backend environment variables.
`.env`, runtime databases/indexes/caches are ignored and excluded from Docker builds.
Production requires an explicit DB_ENGINE=mysql or DB_ENGINE=sqlite and a Django
secret. Database selection preserves production security settings. Staff endpoints
require authentication.
Public browsing/chat are throttled and inputs bounded. API errors do not expose stack
traces, raw provider payloads, credential values or model text in logs. Query text is private by default; optional
RAG_LOG_QUERY_TEXT=true logs queries with common credential formats redacted.

Sessions use random capability tokens, with only SHA-256 hashes stored in SQL.
The frontend stores the token in sessionStorage and sends it in a header, never a
URL. The former profile storage/model/routes/forms were removed. Migration 0002 drops
saved profiles and removes historical profile/rule traces from assistant message JSON.
A student may voluntarily mention circumstances in conversation; those messages
are conversation data, not a separately collected or inferred permanent profile.

Provider requests transmit the question, relevant conversation history and retrieved
scholarship evidence. Apply your deployment privacy/retention policy. New conversation
in the UI deletes the previous protected session. The inactivity cleanup command is
`python backend/manage.py purge_sessions --days 30`. Audit records contain no transcript.
Use HTTPS, protect tokens, encrypt backups, and apply appropriate CSP settings.

React renders text, never model HTML. Citation URLs are server-derived and only HTTP(S)
external links render; internal source links use encoded verified scheme IDs. Retrieved/user text is untrusted. Exact evidence/source and generic numeric checks plus selective
grounding review constrain free-form paraphrases, but do not guarantee zero
hallucinations or resistance to every possible prompt injection. The assistant cannot
issue official eligibility/award decisions. Missing dates/links remain missing.

Index/checksum files are writable only by trusted ingestion administrators. Checksums
protect against corruption, not an attacker controlling both index and manifest.
Thread timeouts cannot kill workers; occupied slots bound concurrency. Browser fonts
may contact Google Fonts. See DEPLOYMENT_AUDIT.md for local Docker verification;
remote MySQL TLS/connectivity and hosted proxy settings need deployment-specific checks.

Production rejects empty/wildcard ALLOWED_HOSTS. CORS remains restricted to named
origins, with x-session-token and x-request-id allowed. Proxy protocol headers are
trusted only when TRUST_PROXY_HEADERS=true behind a restricted ingress.

Deployment validation reports safe error reasons with configured credentials,
common API-token formats, authorization headers and remote/signed URLs redacted.
Checksum, immutable-revision and path-containment checks are retained.
HF_HUB_DISABLE_SHARED_BLOBS=1 keeps Linux downloads within the existing allowed
model-cache boundary instead of accepting arbitrary symlink escapes.

SQLite mode preserves all authentication and security behavior. On ephemeral
hosting it loses users, sessions, conversations, SQL metadata, execution/usage
logs and evaluation runs on restart/redeploy. Persist and back up the database
directory when those records matter; the read-only corpus and reviewed FAISS/model
assets are separate packaged files.
