"""Measure the actual local classifier, section retrieval and context budgets."""

# ruff: noqa: E402
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from apps.navigator.models import AgentExecution
from core import corpus
from core.rag.query import classify_query
from core.rag.retrieval import index_status, load_store, retrieve


def main():
    baseline_path = ROOT / "var/optimization_baseline.json"
    baseline = (
        json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else []
    )
    before = {row["question"]: row for row in baseline}
    cases = json.loads((ROOT / "evaluation/demo_cases.json").read_text(encoding="utf-8"))
    cases.extend(
        {"id": str(i), "question": q, "status": ["out_of_scope"]}
        for i, q in enumerate(
            [
                "Who is the president?",
                "Tell me a joke.",
                "What is the weather today?",
                "Pragati write a Python program",
                "Explain cricket match scores.",
            ]
        )
    )
    results = []
    for case in cases:
        started = time.perf_counter()
        plan = classify_query(case["question"])
        expected_outside = case["status"] == ["out_of_scope"]
        retrieval = {"chunks": [], "metrics": {}, "warnings": []}
        if not plan["out_of_scope"]:
            retrieval = retrieve(case["question"], intent=plan["intent"], sections=plan["sections"])
        chunks = retrieval["chunks"]
        sections = {c.section for c in chunks}
        intended = {
            "demo_pragati_benefits": "benefits",
            "demo_amount": "benefits",
            "demo_saksham_documents": "documents_required",
            "demo_yasasvi_eligibility": "eligibility",
            "demo_pragati_apply": "application",
            "demo_saksham_steps": "application",
        }.get(case["id"])
        expected_intent = {
            "demo_pragati_benefits": "benefits",
            "demo_amount": "benefits",
            "demo_saksham_documents": "documents",
            "demo_yasasvi_eligibility": "eligibility",
            "demo_pragati_apply": "application",
            "demo_saksham_steps": "application",
            "demo_compare": "comparison",
            "demo_ambiguous": "clarification",
        }.get(case["id"])
        checks = {
            "target_intent": not expected_intent or plan["intent"] == expected_intent,
            "domain": plan["out_of_scope"] == expected_outside,
            "target_section": not intended or intended in sections,
            "no_retrieval_failure": not retrieval["warnings"],
            "context_budget": sum(len(c.text) for c in chunks)
            <= int(os.getenv("RAG_CONTEXT_MAX_CHARS", "10000")),
            "unique_chunks": len(chunks) == len({c.chunk_id for c in chunks}),
        }
        old = before.get(case["question"])
        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "plan": plan,
                "checks": checks,
                "passed": all(checks.values()),
                "chunks": [c.chunk_id for c in chunks],
                "retrieved_characters": sum(len(c.text) for c in chunks),
                "baseline": old,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
        print(
            case["id"],
            "PASS" if all(checks.values()) else "FAIL",
            plan["intent"],
            len(chunks),
            sum(len(c.text) for c in chunks),
            flush=True,
        )
    state = index_status()
    store = load_store(state["version"])
    corpus_ids = {s["scheme_id"] for s in corpus.records()}
    indexed_ids = {c.scheme_id for c in store.chunks}
    application_ids = {c.scheme_id for c in store.chunks if c.section == "application"}
    integrity = {
        "all_16_indexed": indexed_ids == corpus_ids,
        "all_16_application_sections": application_ids == corpus_ids,
        "source_ids_match": all(c.citation["scheme_id"] == c.scheme_id for c in store.chunks),
    }
    old = (
        AgentExecution.objects.filter(request_id="acceptance-pragati_amount")
        .order_by("-id")
        .first()
    )
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "local_domain_and_context",
        "corpus_sha256": corpus.fingerprint(),
        "index": state,
        "integrity": integrity,
        "baseline_amount_usage": list(
            old.llm_calls.values("phase", "input_tokens", "output_tokens", "latency_ms")
        )
        if old
        else None,
        "results": results,
        "passed": sum(row["passed"] for row in results),
        "total": len(results),
        "limitations": "Semantic classifier examples are an evaluation sample, not universal domain accuracy. Character counts are exact; token estimates are not measured model tokens. No LLM calls in this local benchmark.",
    }
    (ROOT / "evaluation/reports/efficiency.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        str(report["passed"])
        + "/"
        + str(report["total"])
        + " local cases passed; integrity "
        + str(integrity)
    )
    return 0 if report["passed"] == report["total"] and all(integrity.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
