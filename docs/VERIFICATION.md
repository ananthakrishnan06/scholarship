# Current verification

Verified on 2026-10-01 in the existing Windows/SQLite workspace with live Gemini.
[DEMO_READINESS.md](DEMO_READINESS.md) records file changes, architecture, run commands,
measured tokens, actual reports and remaining limits.

- 59 backend, 7 frontend and 5 automated Edge browser tests passed.
- True Gemini browser text identity, correct full-scheme navigation and chat restoration passed.
- All 16 internal detail pages and all 16 indexed application sections verified.
- 30/30 retrieval questions and 19/19 local domain/context cases passed.
- All 14 scenarios have passing latest results across the corrected 12/14 full live
  run and 3/3 focused run; this is not a single final 14/14 full run.
- All 14 latest real answers passed final source/quote/numeric/schema validation replay.
- Off-topic samples had zero retrieval/provider calls. Simple live lookups used one;
  the true browser procedure check needed a bounded repair and recorded both calls.
- Ruff, Django, migration drift, OpenAPI and repository integrity passed.

The data/vector store remain unchanged: 16 schemes, 139 chunks, corpus SHA-256
805a64250c4e33f7d6e116d40cc2b054cb557fe6a69a6314d179a300929042ea.
No profile/rule engine is reintroduced and no database/vector rebuild is needed.
Production MySQL/Docker runtime acceptance remains pending.

Earlier RAG_REFACTOR.md and its original evaluation reports are historical evidence.
Current reports are efficiency.json, retrieval_optimized.json, demo_live.json,
demo_focused.json, grounding_replay.json and demo_browser.json in evaluation/reports.
The failed first run is retained as demo_initial.json. The full-run comparison
failure is explicitly annotated after manual review exposed the tenfold numeric error.
