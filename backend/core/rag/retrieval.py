"""Semantic retrieval, diverse results, and evidence for source contradictions."""

import os
import re
import time
from functools import lru_cache
from pathlib import Path

from core import corpus
from core.rag.embeddings import embed_query, model_name
from core.rag.query import classify_query
from core.rag.vector_store import FAISSVectorStore

COMMON = {
    "with",
    "and",
    "to",
    "in",
    "from",
    "at",
    "who",
    "which",
    "does",
    "is",
    "are",
    "me",
    "about",
    "scholarship",
    "scholarships",
    "scheme",
    "for",
    "of",
    "the",
    "students",
    "student",
    "post",
    "graduate",
    "what",
    "how",
    "do",
    "i",
    "can",
    "apply",
    "required",
    "documents",
}


def index_dir() -> Path:
    path = Path(os.getenv("VECTOR_INDEX_DIR", "var/index"))
    return path if path.is_absolute() else corpus.ROOT / path


def index_status() -> dict:
    try:
        directory = index_dir()
        version = (directory / "CURRENT").read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[0-9a-f]{32}", version):
            raise ValueError("Invalid pointer")
        import json

        metadata = json.loads((directory / version / "metadata.json").read_text(encoding="utf-8"))
        ready = (
            metadata["corpus_hash"] == corpus.fingerprint()
            and metadata["embedding_model"] == model_name()
        )
        return {
            "ready": ready,
            "version": version,
            "chunks": metadata["chunk_count"],
            "reason": None if ready else "Corpus or embedding model changed; re-ingest.",
        }
    except (OSError, ValueError, KeyError):
        return {"ready": False, "reason": "Index unavailable; run ingest_scholarships."}


@lru_cache(maxsize=4)
def load_store(version: str):
    store, metadata = FAISSVectorStore.load(index_dir())
    if (
        metadata["corpus_hash"] != corpus.fingerprint()
        or metadata["embedding_model"] != model_name()
    ):
        raise ValueError("Index is stale; run ingestion.")
    return store


def filters_for(question, scheme_ids=None, category=None):
    if scheme_ids is not None:
        corpus.records(scheme_ids)  # Validate even an empty list.
        return {"scheme_id": scheme_ids}
    if category:
        return {"scheme_id": [s["scheme_id"] for s in corpus.search(category=category, top_k=16)]}
    # Full names outrank shared anchors and category words inside names.
    normalized = " ".join(re.findall(r"[a-z0-9]+", question.lower()))
    exact = [
        s["scheme_id"]
        for s in corpus.records()
        if " " + " ".join(re.findall(r"[a-z0-9]+", s["name"].lower())) + " "
        in " " + normalized + " "
    ]
    # Remove full-name spans before resolving remaining abbreviated mentions.
    # A comparison may mix a complete name with a short name.
    remaining = " " + normalized + " "
    for scheme in corpus.records(exact):
        name = " ".join(re.findall(r"[a-z0-9]+", scheme["name"].lower()))
        remaining = remaining.replace(" " + name + " ", " ")
    # Explicit category tokens are a corpus filter, never inferred profile facts.
    categories = [
        code
        for code in ("OBC", "EBC", "DNT", "SC", "ST", "SEBC")
        if re.search(r"\b" + code + r"\b", question, re.I)
    ]
    if categories and not exact:
        return {
            "scheme_id": list(
                dict.fromkeys(
                    s["scheme_id"]
                    for code in categories
                    for s in corpus.search(category=code, top_k=16)
                )
            )
        }
    query_terms = set(re.findall(r"[a-z]+", remaining)) - COMMON
    scored = [
        (len(query_terms & (set(re.findall(r"[a-z]+", s["name"].lower())) - COMMON)), s)
        for s in corpus.records()
    ]
    # Distinctive corpus name terms resolve multiple explicitly named schemes.
    # This is metadata routing; no scheme facts or eligibility decisions are encoded.
    generic = COMMON | {
        "pm",
        "girl",
        "girls",
        "technical",
        "degree",
        "diploma",
        "matric",
        "pre",
        "scheduled",
        "caste",
        "tribe",
        "disabilities",
        "doctoral",
        "fellowship",
        "national",
        "single",
        "child",
    }
    name_terms = [
        (s, set(re.findall(r"[a-z]+", s["name"].lower())) - generic) for s in corpus.records()
    ]
    frequency = {
        term: sum(term in terms for _, terms in name_terms)
        for _, terms in name_terms
        for term in terms
    }
    anchors = {term for term in query_terms if frequency.get(term, 99) <= 3}
    named = [s["scheme_id"] for s, terms in name_terms if terms & anchors]
    if named:
        qualifiers = query_terms & {"degree", "diploma"}
        if len(qualifiers) == 1:
            qualified = [
                s["scheme_id"]
                for s in corpus.records(named)
                if qualifiers & set(re.findall(r"[a-z]+", s["name"].lower()))
            ]
            named = qualified or named
        return {"scheme_id": list(dict.fromkeys([*exact, *named]))}
    if exact:
        return {"scheme_id": exact}
    best = max(score for score, _ in scored)
    if best >= 2 or any(
        t in query_terms for t in ("gate", "ceed", "yasasvi", "pragati", "saksham", "icar")
    ):
        return {"scheme_id": [s["scheme_id"] for score, s in scored if score == best and score]}
    return {}


def select_diverse(hits, top_k, scoped):
    """Keep nearest evidence; broad discovery gives distinct schemes a first turn."""
    if scoped:
        return [chunk for chunk, _ in hits[:top_k]]
    groups = {}
    for chunk, score in hits:
        groups.setdefault(chunk.scheme_id, []).append((chunk, score))
    selected = []
    while groups and len(selected) < top_k:
        for sid in list(groups):
            selected.append(groups[sid].pop(0)[0])
            if not groups[sid]:
                del groups[sid]
            if len(selected) == top_k:
                break
    return selected


def compact_chunks(chunks, max_chars):
    """Deduplicate whole evidence chunks without rewriting facts or source quotes."""
    unique, seen = [], set()
    for chunk in chunks:
        key = (chunk.scheme_id, chunk.section, chunk.text)
        if key not in seen:
            unique.append(chunk)
            seen.add(key)
    # Preserve cautionary notes first, then semantic ranking and scheme diversity.
    ordered = sorted(unique, key=lambda c: c.section != "important_notes")
    selected, used = [], 0
    for chunk in ordered:
        if used + len(chunk.text) <= max_chars:
            selected.append(chunk)
            used += len(chunk.text)
    ids = {c.chunk_id for c in selected}
    return [c for c in unique if c.chunk_id in ids]


def retrieve(
    question: str, scheme_ids=None, category=None, top_k=8, intent=None, sections=None
) -> dict:
    started = time.perf_counter()
    filters = filters_for(question, scheme_ids, category)
    embed_ms = vector_ms = 0.0
    warnings, chunks = [], []
    metrics = {}
    scores = {}
    state = index_status()
    try:
        if not state["ready"]:
            raise ValueError(state["reason"])
        classification = classify_query(question) if intent is None else {}
        intent = intent or classification.get("intent", "general")
        sections = sections if sections is not None else classification.get("sections", [])
        store = load_store(state["version"])
        t = time.perf_counter()
        vector = embed_query(question)
        embed_ms = (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        search_filters = dict(filters)
        if sections:
            search_filters["section"] = sections
        focused = intent in ("benefits", "documents", "application", "deadline")
        scheme_count = len(filters.get("scheme_id", []))
        effective_k = (
            min(top_k, max(2, scheme_count * 2))
            if focused and scheme_count
            else (min(top_k, 2) if intent == "clarification" else min(top_k, 6))
        )
        hits = store.search(vector, min(64, top_k * 4), search_filters)
        hits = [(chunk, score) for chunk, score in hits if score >= 0.20]
        if intent == "discovery" and hits:
            floor = max(0.20, hits[0][1] - 0.15)
            hits = [(chunk, score) for chunk, score in hits if score >= floor]
        scores.update((c.chunk_id, score) for c, score in hits)
        chunks = select_diverse(hits, effective_k, scheme_count == 1)
        # Keep requested named-section continuations rather than truncate by k.
        if scheme_count and sections:
            requested_hits = store.search(vector, 64, search_filters)
            scores.update((c.chunk_id, score) for c, score in requested_hits)
            chunks = [c for c, score in requested_hits if score >= 0.20]
        if intent == "discovery":
            # Explicit audience words must occur in corpus audience metadata.
            audience = (
                set(re.findall(r"[a-z]+", question.lower()))
                - COMMON
                - {"knowledge", "base", "support", "available", "there", "any", "get"}
            )
            matching = {
                s["scheme_id"]
                for s in corpus.records()
                if audience & set(re.findall(r"[a-z]+", str(s.get("target_groups", [])).lower()))
            }
            if matching:
                chunks = [c for c in chunks if c.scheme_id in matching]
            shortlist = list(dict.fromkeys(c.scheme_id for c in chunks))[:4]
            chunks = [c for c in chunks if c.scheme_id in shortlist]
        ids = list(dict.fromkeys(c.scheme_id for c in chunks))
        # Comparisons need benefits and criteria for EACH named candidate, not
        # only whichever section has the strongest name similarity.
        required_sections = (
            tuple(sections)
            if intent == "comparison" and sections
            else (
                ("benefits", "eligibility", "application")
                if intent == "discovery"
                else ("application",)
            )
        )
        if ids and intent in ("discovery", "comparison", "general"):
            for section in required_sections:
                additions = store.search(vector, 32, {"scheme_id": ids, "section": [section]})
                present = {c.chunk_id for c in chunks}
                scores.update((c.chunk_id, score) for c, score in additions)
                for chunk, _ in additions:
                    if chunk.chunk_id not in present:
                        chunks.append(chunk)
                        present.add(chunk.chunk_id)
        if ids:
            notes = store.search(vector, 32, {"scheme_id": ids, "section": ["important_notes"]})
            scores.update((c.chunk_id, score) for c, score in notes)
            for chunk, _ in notes:
                # Narrow fact requests retain notes about that same semantic need;
                # broad/criteria/procedure requests retain all candidate scheme notes.
                note_need = classify_query(chunk.text)
                conflicting = bool(
                    re.search(
                        r"\b(conflict|contradict|inconsisten|discrepanc|different limits)",
                        chunk.text,
                        re.I,
                    )
                )
                if (
                    conflicting
                    or intent in ("eligibility", "exclusions", "renewal", "general")
                    or note_need["intent"] == "general"
                    or bool(set(note_need["sections"]) & set(sections))
                ):
                    chunks.append(chunk)
        vector_ms = (time.perf_counter() - t) * 1000
        before = sum(len(c.text) for c in chunks)
        count = len(chunks)
        chunks = compact_chunks(chunks, int(os.getenv("RAG_CONTEXT_MAX_CHARS", "10000")))
        groups = list(dict.fromkeys((c.scheme_id, c.section) for c in chunks))
        # Explicit information needs rank ahead of ancillary audience/restriction
        # sections. Within a section preserve its original continuation order.
        groups.sort(
            key=lambda group: sections.index(group[1]) if group[1] in sections else len(sections)
        )
        chunks.sort(
            key=lambda c: (
                groups.index((c.scheme_id, c.section)),
                int(c.chunk_id.rsplit(":", 1)[-1]),
            )
        )
        metrics = {
            "intent": intent,
            "requested_sections": sections,
            "candidate_count": len(hits),
            "effective_top_k": effective_k,
            "before_compression_chunks": count,
            "before_compression_characters": before,
            "retrieved_chunk_count": len(chunks),
            "retrieved_characters": sum(len(c.text) for c in chunks),
        }
    except Exception as exc:
        from core.observability import event

        event("vector_retrieval_failure", error_type=type(exc).__name__)
        chunks = []
        warnings.append(
            {
                "code": "VECTOR_UNAVAILABLE",
                "message": "Scholarship search is unavailable. Rebuild the scholarship index and try again.",
            }
        )
    return {
        "chunks": chunks,
        "warnings": warnings,
        "scores": {c.chunk_id: scores[c.chunk_id] for c in chunks if c.chunk_id in scores},
        "metrics": metrics,
        "timings_ms": {
            "embedding": embed_ms,
            "vector_retrieval": vector_ms,
            "retrieval_total": (time.perf_counter() - started) * 1000,
        },
    }
