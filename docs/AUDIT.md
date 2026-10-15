# Repository audit and refactor

The initial repository held the scholarship JSON/JSONL corpus, QA report, a README
reference and a preliminary eligibility engine. The first implementation added
Django, React, an optional Gemini evidence selector, FAISS retrieval, profiles and a
rule engine. That earlier architecture is superseded by this explicit RAG refactor.
The supplied eligibility-engine README is preserved at [docs/history/ELIGIBILITY_ENGINE.md](history/ELIGIBILITY_ENGINE.md) as historical documentation, not current runtime instructions.

Before editing, the frontend, API, schemas, memory, tools, workflow, Gemini adapter,
chunker, embeddings, FAISS persistence, corpus/provenance, migrations, tests, evaluation
and deployment files were inspected. The defect was the quote-only generation contract:
Gemini returned fragments; the server reconstructed the displayed answer from fragments.
Every assistant query also called deterministic eligibility, and the UI centered profiles.

The corrected application retains corpus/semantic retrieval, generates natural answers,
checks support, removes personal-profile matching and shows only relevant sources.
See [RAG refactor report](RAG_REFACTOR.md) for file changes and actual verification.
