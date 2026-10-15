# Scholarship RAG architecture

```mermaid
flowchart TD
    UI[Existing React workspace] --> API[Django API and validation]
    API --> Domain[Local semantic domain and intent check]
    Domain -->|Unrelated| Redirect[Scholarship-only guidance: zero provider calls]
    Domain -->|Relevant or uncertain| Query[Names and conversation references]
    Corpus[16-scheme JSON dataset] --> Chunks[139 section-aware chunks]
    Chunks --> Embeddings[MiniLM embeddings]
    Embeddings --> FAISS[Existing persisted FAISS store]
    Query --> Retriever[Section-aware semantic retrieval]
    FAISS --> Retriever
    Retriever --> Context[Deduplicated bounded evidence and recent history]
    Context --> Gemini[Gemini natural-language generation]
    Gemini --> Checks[Schema, evidence and URL validation]
    Checks --> Review[Selective semantic grounding review]
    Review --> Response[Actual generated answer and verified sources]
    Response --> UI
    UI --> Detail[View Full Scheme: existing internal detail route]
    Redirect --> UI
    API --> SQL[Sessions, metadata, audit and usage: SQLite or MySQL]
```

RAG remains the factual engine: JSON -> embeddings/vector retrieval -> actual
retrieved text -> LLM -> answer/sources. Domain descriptions and section constraints
route information needs; they encode no scholarship eligibility rules or answers.
Existing API shapes, provider/model configuration, dataset and vector files remain.
Profile collection/matching remains removed. Application sections and source IDs
are preserved. Current verification and limits are in DEMO_READINESS.md.
