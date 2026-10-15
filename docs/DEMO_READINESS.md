# Scholarship RAG demo readiness

Verified on 2026-10-01 in the existing Windows/SQLite workspace using the configured
Gemini model `gemini-3.5-flash-lite`. Local demo flows are verified. Production
MySQL/container runtime acceptance remains pending.

## Files changed

- `.env.example`
- `README.md`
- `backend/core/agent/tools.py`
- `backend/core/agent/workflow.py`
- `backend/core/llm.py`
- `backend/core/observability.py`
- `backend/core/quantities.py`
- `backend/core/rag/embeddings.py`
- `backend/core/rag/query.py`
- `backend/core/rag/retrieval.py`
- `backend/core/schemas.py`
- `deploy/production.env.example`
- `docs/AGENT.md`
- `docs/API.md`
- `docs/ARCHITECTURE.md`
- `docs/DEMO_READINESS.md`
- `docs/DEPLOYMENT.md`
- `docs/EVALUATION.md`
- `docs/RAG.md`
- `docs/RAG_REFACTOR.md`
- `docs/SECURITY.md`
- `docs/VERIFICATION.md`
- `evaluation/check_retrieval_efficiency.py`
- `evaluation/demo_cases.json`
- `evaluation/rag_cases.json`
- `evaluation/reports/demo_browser.json`
- `evaluation/reports/demo_focused.json`
- `evaluation/reports/demo_initial.json`
- `evaluation/reports/demo_live.json`
- `evaluation/reports/efficiency.json`
- `evaluation/reports/grounding_replay.json`
- `evaluation/reports/retrieval_optimized.json`
- `evaluation/run_eval.py`
- `frontend/e2e/navigator.spec.ts`
- `frontend/src/ScholarshipDetail.tsx`
- `frontend/src/ScholarshipList.tsx`
- `frontend/src/components.test.tsx`
- `frontend/src/components.tsx`
- `frontend/src/navigation.ts`
- `frontend/src/types.ts`
- `tests/conftest.py`
- `tests/test_agent.py`
- `tests/test_quantities.py`
- `tests/test_query.py`
- `tests/test_rag.py`

No files were removed in this update. All 16 scholarship records, source/QA JSON,
original provenance, provider/model/key configuration, database models and existing
139 vector chunks are preserved. Profile/rule matching remains removed.

## Architecture changes

API -> local semantic domain/information-need check -> corpus-name/conversation
processing -> MiniLM embedding and FAISS retrieval -> bounded relevant evidence ->
Gemini natural language -> schema/source/quantity checks -> selective review ->
actual answer and source links. No LLM call rewrites/classifies every query.

The domain/section classifier compares embeddings with cached information-need
and domain descriptions. These contain no scholarship facts or eligibility rules.
Uncertain queries proceed to RAG. Ambiguous recommendations use a constrained
clarification schema (insufficient_evidence, empty supports) and a natural optional
question, not a profile questionnaire or a fabricated recommendation.

## Retrieval optimization

Semantic section metadata narrows focused queries. Names are derived from the
corpus, with multiple named schemes preserved and generic prefixes excluded.
Matched name words are normalized only for section classification; the actual
search query retains the name. Broad discovery has a bounded diversified shortlist;
comparisons/discovery include the selected schemes' criteria, benefits and procedures.
Important notes preserve uncertainty and conflicting statements.

Whole evidence chunks are deduplicated by scheme/section/content, never rewritten.
Identical facts in distinct schemes keep separate provenance. Default budgets are
10000 source-text characters, four recent messages and 2000 history characters,
within the existing 24000-character total provider input limit. Broad discovery may
need more evidence than before to support useful comparisons; normal queries never
send complete raw records or the entire 16-scheme dataset.

All 16 schemes and all 16 application sections were verified in the existing index.
No rebuild is required: stable IDs/section metadata already support these changes.
A missing/stale index uses `python backend/manage.py ingest_scholarships`.
Corpus SHA-256: `805a64250c4e33f7d6e116d40cc2b054cb557fe6a69a6314d179a300929042ea`.
Index version: `faac7d4df3034bafae61db8e52553481`; 139 unchanged chunks.

## Token optimization and grounding

Concise prompts request relevant facts and minimal exact quotes. Default
LLM_GROUNDING_REVIEW=auto uses one generation for simple benefits/documents/procedure
lookups and clarification. Conflicts, criteria, comparisons, missing facts, multiple
schemes and suggested numbers retain a separate review. Set always for review on
every generation. Review receives cited evidence and cautionary notes. One bounded
repair receives specific feedback. Every attempted provider call is counted.

Manual review caught an income figure overstated by a factor of ten that model
review had approved. A generic quantity normalizer now rejects numeric values
absent from cited text, including lakh/crore and digit-grouping conversions. This
checks factual quantities and encodes no scheme-specific eligibility thresholds.
Invalid quotes now receive actionable feedback identifying the noncontiguous span.
These checks reduce errors; they cannot prove every qualitative claim or unit relationship.

| Focused request | Before retrieved characters | Current characters |
|---|---:|---:|
| Pragati benefits | 3076 | 593 |
| Saksham documents | 2110 | 459 |
| Pragati application | 2976 | 198 |

For the same 'How much does Pragati provide?' question, the earlier live response
used 3849 input tokens across two calls; the corrected focused run used 1147
in one call, 70.2% fewer measured input tokens. This is one observed comparison
with the same model, not a guarantee for every query. Failed output/repairs consume
tokens: the real browser procedure check used two generation calls (one rejected
quote, one successful repair), both recorded in demo_browser.json.

Metrics include query fingerprint/length, domain scores, retrieved chunk/text counts,
final context characters, clearly labeled estimated context tokens, actual provider
input/output tokens, phase and latency. RAG_LOG_QUERY_TEXT=true optionally logs query
text with common credentials redacted; default false keeps text private. No API
keys, full prompts or raw provider exceptions reach the frontend.

## Out-of-domain handling

Arithmetic, sports, coding, weather, political-leader and joke samples redirect to
scholarship help without answering the unrelated request. The local semantic gate
returns a brief domain-boundary message with out_of_scope and no sources; no
retrieval tool or provider call runs. This is not hardcoded scholarship answer
construction. The true browser arithmetic check audited zero retrieval/LLM calls.
The first encoder load still costs startup time; subsequent queries reuse caches.

## Source-link implementation

Source cards derive View Full Scheme from the verified retrieved scheme_id and
existing route `#/scholarships/{encoded_scheme_id}`. They open the matching page
on this website, never a generic homepage. Existing stable IDs make new slugs,
dataset edits and index changes unnecessary. Official HTTP(S) links are additional;
missing official links do not prevent internal navigation. Only used verified sources
are shown, deduplicated by scheme.

Detail pages preserve design and show target groups, criteria, benefits, documents,
application procedure, exclusions, selection/renewal and scheme notes. All 16
internal detail routes passed browser checks. A real Gemini answer's source opened
its matching page, then its unchanged conversation restored when navigating back.

## Application procedures

All existing mode, portal, registration/login/upload/submission, institution
verification and payment/DBT fields remain indexed where supplied. The model
explains actual steps, not invented procedures. Saksham's registration/login/upload/
submission steps passed live testing. Pragati provides online NSP application and
PFMS tracking; no detailed registration sequence was invented. Relevant conflicting
application notes are retained and require disclosure, not silent selection of one side.

## Tests performed and actual results

| Check | Result |
|---|---|
| Backend pytest | 59 passed |
| Frontend TypeScript/lint, production build | Passed |
| Vitest | 7 passed |
| Automated Edge browser checks | 5 passed, including all 16 scheme pages |
| Separate true Gemini browser/source-navigation/restored-chat check | Passed |
| Local domain/intent/context/index checks | 19/19 passed |
| Persisted FAISS retrieval questions | 30/30 passed |
| Corrected full live run after manual numeric review | 12/14 passed |
| Final focused amount/girls/comparison run | 3/3 passed |
| Latest result of each live scenario across those runs | All 14 passed |
| All 14 real responses replayed through final deterministic grounding | 14/14 passed |
| Ruff, Django check, migration drift and OpenAPI | Passed |
| Repository hygiene and data/schema integrity | Passed |

The first live run (10/14) is preserved in demo_initial.json. The next run initially
scored 13/14 automatically; manual inspection found a comparison numeric error,
which is explicitly marked failed, correcting it to 12/14. After fixes, the separate
focused run passed all three cases. This is not a claim that one final full live run
passed 14/14. All 14 latest real answers then passed source/quote/numeric/schema replay
without additional model calls. Quantity tests also reject the tenfold error directly.

| Live scenario | Actual calls | Actual input tokens | Latest result |
|---|---:|---:|---|
| demo_pragati_benefits | 1 | 934 | PASS |
| demo_amount | 1 | 1147 | PASS |
| demo_saksham_documents | 1 | 804 | PASS |
| demo_yasasvi_eligibility | 2 | 1642 | PASS |
| demo_pragati_apply | 1 | 834 | PASS |
| demo_apply_followup | 1 | 942 | PASS |
| demo_girls | 2 | 5424 | PASS |
| demo_compare | 2 | 4939 | PASS |
| demo_math | 0 | 0 | PASS |
| demo_cricket | 0 | 0 | PASS |
| demo_code | 0 | 0 | PASS |
| demo_deadline | 2 | 1524 | PASS |
| demo_ambiguous | 1 | 955 | PASS |
| demo_saksham_steps | 1 | 784 | PASS |

Reports: [local efficiency](../evaluation/reports/efficiency.json),
[optimized retrieval](../evaluation/reports/retrieval_optimized.json),
[full live](../evaluation/reports/demo_live.json),
[focused live](../evaluation/reports/demo_focused.json),
[grounding replay](../evaluation/reports/grounding_replay.json),
[true browser](../evaluation/reports/demo_browser.json).
Screenshots: ignored var/demo-assistant-live.png and var/demo-scheme-source.png.

## Running and configuration

Existing servers were verified at http://127.0.0.1:8000 and
http://127.0.0.1:5173/#/assistant. Keep the working ignored .env and configured key/model.
No new dependencies, database migration, model download or vector rebuild are needed here.

Backend terminal:

```powershell
cd D:\social-hackthon\social-hackthon
python backend/manage.py runserver 127.0.0.1:8000
```

Frontend terminal:

```powershell
cd D:\social-hackthon\social-hackthon
$env:PATH = "$PWD\var\tools\node-v24.21.0-win-x64;" + $env:PATH
npm.cmd --prefix frontend run dev
```

New settings in .env.example: RAG_CONTEXT_MAX_CHARS=10000,
RAG_HISTORY_MAX_CHARS=2000, LLM_GROUNDING_REVIEW=auto and RAG_LOG_QUERY_TEXT=false.
Existing LLM_PROVIDER=gemini, LLM_MODEL and GEMINI_API_KEY are preserved.

## Remaining issues

- MySQL/container runtime, production TLS/hosts/backups/retention require the actual
  deployment environment. Local SQLite demo verification is not full production acceptance.
- The dataset snapshot lacks some URLs/dates and includes contradictions. Internal
  source pages work; current details still require official verification.
- English semantic classification is fallible; 19 test samples are not universal
  accuracy. Broad discovery is a shortlist, not guaranteed complete enumeration.
- Schema, quote, numeric and optional model checks can miss a semantic error or
  reject a valid paraphrase. Numeric matching alone cannot prove every period,
  currency, relationship or eligibility interpretation. Always review costs more
  and also remains fallible.
- Quotas/network/model errors are explicit; rejected output and repairs cost tokens.
  No fake AI answer is substituted. Multilingual quality and independent deployment/
  dependency-security acceptance are unverified. No remote is configured; nothing was pushed.
