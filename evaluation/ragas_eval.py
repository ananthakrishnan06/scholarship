"""Extend run_eval.py with real production capture and explicit offline RAGAS scoring."""

import asyncio
import hashlib
import importlib.metadata
import json
import math
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from apps.navigator.models import AgentExecution, EvaluationRun
from core import corpus, memory
from core.agent.workflow import query
from core.llm import REVIEW_PROMPT, SYSTEM_PROMPT
from core.rag.documents import prepare_documents
from core.rag.embeddings import model_name
from core.rag.retrieval import index_status
from core.schemas import QueryRequest

from evaluation.schemas import (
    METRICS,
    EvaluationDataset,
    EvaluationReport,
    EvaluationResult,
    MetricResult,
    ProviderUsage,
    context_text,
)

ROOT = Path(__file__).resolve().parents[1]


def load_dataset(path):
    dataset = EvaluationDataset.model_validate_json(Path(path).read_text(encoding="utf-8"))
    if dataset.corpus_sha256 != corpus.fingerprint():
        raise ValueError("Evaluation references are stale for the scholarship corpus.")
    documents = {c.chunk_id: c for c in prepare_documents()}
    for sample in dataset.samples:
        corpus.records(sample.expected_scheme_ids)
        if (
            sample.score_ragas
            and sample.category != "unavailable"
            and sample.reference != "\n\n".join(sample.reference_contexts)
        ):
            raise ValueError(
                "Factual reference answers must match their verified dataset section snapshots."
            )
        for cid, text in zip(sample.reference_chunk_ids, sample.reference_contexts):
            if cid not in documents or text != context_text(documents[cid]):
                raise ValueError("Reference context does not match the preserved corpus chunk.")
            if documents[cid].scheme_id not in sample.expected_scheme_ids:
                raise ValueError("Reference chunks must belong to expected schemes.")
    return dataset


def provenance_checks(response, chunks):
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    for source in response.sources:
        chunk = by_id.get(source.retrieved_from)
        if chunk is None or not source.excerpt or source.excerpt not in chunk.text:
            return False
        if any(
            getattr(source, field) != chunk.citation.get(field)
            for field in (
                "scheme_id",
                "scheme_name",
                "source_name",
                "source_url",
                "original_record_key",
            )
        ):
            return False
    return response.status != "success" or bool(response.sources)


def collect(sample, run_id):
    session, _ = memory.create_session()
    request_id = f"ragas-{run_id[:8]}-{hashlib.sha256(sample.id.encode()).hexdigest()[:16]}-{uuid.uuid4().hex[:8]}"
    trace = {}
    try:
        started = time.perf_counter()
        response = query(
            QueryRequest(question=sample.question, top_k=sample.top_k),
            request_id,
            session,
            trace=trace,
        )
        latency = (time.perf_counter() - started) * 1000
        execution = AgentExecution.objects.get(request_id=request_id)
        usage = [
            ProviderUsage.model_validate(row)
            for row in execution.llm_calls.values(
                "provider",
                "model",
                "phase",
                "status",
                "input_tokens",
                "output_tokens",
                "latency_ms",
            )
        ]
        calls = execution.tools.count()
        chunks = trace.get("chunks", [])
        retrieved_ids = {chunk.scheme_id for chunk in chunks}
        cited_ids = {source.scheme_id for source in response.sources}
        checks = {
            "expected_status": response.status in sample.expected_statuses,
            "expected_scheme_retrieved": not sample.expected_scheme_ids
            or bool(retrieved_ids & set(sample.expected_scheme_ids)),
            "expected_scheme_cited": not sample.expected_scheme_ids
            or bool(cited_ids & set(sample.expected_scheme_ids)),
            "provenance_traceable": provenance_checks(response, chunks),
            "off_domain_zero_calls": sample.category != "out_of_domain"
            or (not calls and not usage and not chunks and not response.sources),
            "clarification_without_sources": sample.category != "ambiguous" or not response.sources,
        }
        return EvaluationResult(
            id=sample.id,
            category=sample.category,
            question=sample.question,
            reference=sample.reference,
            expected_scheme_ids=sample.expected_scheme_ids,
            reference_contexts=sample.reference_contexts,
            response=response,
            retrieved_chunks=chunks,
            retrieved_contexts=[context_text(c) for c in chunks],
            retrieval_scores=trace.get("scores", {}),
            top_k=sample.top_k,
            retrieval_metrics=trace.get("retrieval_metrics", {}),
            retrieval_latency_ms=trace.get("timings_ms", {}).get("retrieval_total", 0),
            total_latency_ms=latency,
            llm_usage=usage,
            llm_diagnostics=trace.get("llm_diagnostics", []),
            retrieval_calls=calls,
            checks=checks,
            metrics={
                name: MetricResult(status="skipped", explanation="Not scored yet.")
                for name in METRICS
            },
        )
    finally:
        session.delete()


async def score_result(result, sample, metrics, judge, on_progress=None):
    from evaluation.ragas_adapter import metric_arguments

    if (
        not sample.score_ragas
        or result.response.status in ("out_of_scope", "error")
        or not result.retrieved_contexts
    ):
        reason = (
            "Separate domain/clarification behavior check."
            if not sample.score_ragas
            else "Pipeline failed or produced no retrieved evidence."
        )
        result.metrics = {
            name: MetricResult(status="skipped", explanation=reason) for name in METRICS
        }
        return
    offset = len(judge.usage)
    for name in METRICS:
        if result.metrics[name].status == "ok":
            continue
        started = time.perf_counter()
        judgment_offset = len(getattr(judge, "judgments", []))
        try:
            measured = await metrics[name].ascore(**metric_arguments(name, result))
            if not math.isfinite(float(measured.value)):
                raise ArithmeticError("RAGAS_SCORE_UNDEFINED")
            result.metrics[name] = MetricResult(
                status="ok",
                score=float(measured.value),
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        except Exception as exc:
            result.metrics[name] = MetricResult(
                status="error",
                latency_ms=(time.perf_counter() - started) * 1000,
                error={
                    "code": "RAGAS_SCORE_UNDEFINED"
                    if isinstance(exc, ArithmeticError)
                    else "RAGAS_METRIC_FAILED",
                    "message": "Metric evaluation failed ("
                    + type(exc).__name__
                    + "). No score was substituted.",
                },
            )
        print(
            f"  {result.id}/{name}: {result.metrics[name].status}"
            + (
                f" {result.metrics[name].score:.4f}"
                if result.metrics[name].score is not None
                else ""
            ),
            flush=True,
        )
        result.judge_diagnostics[name] = getattr(judge, "judgments", [])[judgment_offset:]
        result.evaluator_usage.extend(judge.usage[offset:])
        offset = len(judge.usage)
        if on_progress is not None:
            on_progress()


def summarize(report):
    from evaluation.run_eval import percentiles

    rows = report.results
    means = {}
    for name in METRICS:
        scores = [r.metrics[name].score for r in rows if r.metrics[name].status == "ok"]
        means[name] = {
            "mean": sum(scores) / len(scores) if scores else None,
            "scored": len(scores),
            "errors": sum(r.metrics[name].status == "error" for r in rows),
            "skipped": sum(r.metrics[name].status == "skipped" for r in rows),
        }

    def tokens(field):
        calls = [call for row in [*rows, *report.previous_attempts] for call in getattr(row, field)]
        return {
            "calls": len(calls),
            "input_tokens": sum(c.input_tokens or 0 for c in calls),
            "output_tokens": sum(c.output_tokens or 0 for c in calls),
            "calls_missing_usage": sum(
                c.input_tokens is None or c.output_tokens is None for c in calls
            ),
        }

    return {
        "questions": len(rows),
        "previous_failed_attempts": len(report.previous_attempts),
        "expected_schemes": len({sid for row in rows for sid in row.expected_scheme_ids}),
        "retrieved_schemes": len({c.scheme_id for row in rows for c in row.retrieved_chunks}),
        "cited_schemes": len({c.scheme_id for row in rows for c in row.response.sources}),
        "behavior_passed": sum(all(row.checks.values()) for row in rows),
        "pipeline_errors": sum(row.response.status == "error" for row in rows),
        "metrics": means,
        "retrieval_latency_ms": percentiles(
            [row.retrieval_latency_ms for row in rows if row.retrieval_calls]
        ),
        "total_latency_ms": percentiles([row.total_latency_ms for row in rows]),
        "application_usage": tokens("llm_usage"),
        "evaluator_usage": tokens("evaluator_usage"),
    }


def markdown_report(report, summary):
    def number(value):
        return "unavailable" if value is None else f"{value:.4f}"

    lines = [
        "# RAG Evaluation Report",
        "",
        f"Generated from actual evaluation output on {report.created_at.astimezone(ZoneInfo('Asia/Calcutta')).isoformat()}. Run `{report.run_id}`.",
        "",
        "## Project and dataset",
        "",
        "The existing React/Django/LangGraph application retrieves preserved section chunks with MiniLM and FAISS, then generates and validates Gemini answers with traceable sources. No profile or eligibility rule engine is used.",
        "",
        f"The unchanged knowledge base contains {len(corpus.records())} schemes. This run contains {summary['questions']} questions, expects {summary['expected_schemes']} schemes, retrieves {summary['retrieved_schemes']} and cites {summary['cited_schemes']} distinct schemes.",
        "References are benchmark labels derived from exact preserved dataset sections; they are never supplied to the application generator. All reference contexts are checked against their stable chunk IDs and corpus fingerprint before the run.",
        "",
        f"Corpus SHA-256: `{report.corpus_sha256}`. Evaluation dataset SHA-256: `{report.dataset_sha256}`.",
        "",
        "## Methodology and configuration",
        "",
        "Each question invokes the existing production query() workflow: local domain classification, normal FAISS retrieval, bounded context, Gemini generation/review, final response validation and source citations. An opt-in trace captures the actual retrieved chunks, FAISS scores, context counts and timings without a second retrieval. Disposable evaluation sessions are deleted. RAGAS runs only afterward in the explicit offline command.",
        "",
        f"RAGAS `{report.package_versions['ragas']}`; Pydantic `{report.package_versions['pydantic']}`; Python `{report.package_versions['python']}`; google-genai `{report.package_versions['google-genai']}`.",
        f"Application/judge configuration: `{json.dumps(report.configuration, sort_keys=True)}`.",
        "",
        "The installed RAGAS 0.4.3 metrics.collections API builds prompts and computes scores. A structured Gemini adapter supplies judge responses; existing local MiniLM embeddings supply Answer Relevancy similarity. Context Precision uses reference answers. Context Recall measures reference claims covered by the actual retrieved contexts.",
        "",
        "## Actual RAGAS measurements",
        "",
        "Means use successful numeric measurements only. Errors and skips are shown separately, never assigned fabricated zero/perfect scores. Behavioral redirects and optional clarification have no factual reference contexts and are excluded from these means.",
        "",
        "| Metric | Mean | Scored | Errors | Skipped |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, data in summary["metrics"].items():
        lines.append(
            f"| {name} | {number(data['mean'])} | {data['scored']} | {data['errors']} | {data['skipped']} |"
        )
    lines += [
        "",
        "Faithfulness checks claims against retrieved evidence; Answer Relevancy checks question/answer relevance; Context Precision checks ranked context usefulness; Context Recall checks coverage of the reference answer. These are model-judged metrics, not official eligibility decisions or a proof of factual correctness.",
        "",
        "## Latency and token usage",
        "",
        f"Retrieval latency (milliseconds): `{json.dumps(summary['retrieval_latency_ms'])}`. End-to-end application latency, including local classification and validation but excluding offline judging: `{json.dumps(summary['total_latency_ms'])}`.",
        f"Actual application provider usage: `{json.dumps(summary['application_usage'])}`.",
        f"Actual offline evaluator provider usage: `{json.dumps(summary['evaluator_usage'])}`.",
        "Unknown usage is counted explicitly; token sums contain only available provider measurements. Cold-start samples are included. Per-metric judging latency and each attempted provider call appear in the JSON results.",
        "",
        "## Per-question results",
        "",
        "| ID | Category | Status | Behavior | Faithfulness | Relevancy | Precision | Recall | Retrieval ms | Total ms |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.results:
        scores = [number(row.metrics[name].score) for name in METRICS]
        lines.append(
            f"| {row.id} | {row.category} | {row.response.status} | {'PASS' if all(row.checks.values()) else 'FAIL'} | "
            + " | ".join(scores)
            + f" | {row.retrieval_latency_ms:.1f} | {row.total_latency_ms:.1f} |"
        )
    lines += ["", "## Invalid queries and source/provenance checks", ""]
    for row in report.results:
        if row.category in ("out_of_domain", "ambiguous"):
            lines.append(
                f"- {row.id}: `{row.response.status}`, retrieval calls {row.retrieval_calls}, application LLM calls {len(row.llm_usage)}, judge calls {len(row.evaluator_usage)}; checks `{json.dumps(row.checks)}`."
            )
    lines += [
        "",
        f"All behavioral/source checks pass for {summary['behavior_passed']}/{summary['questions']} questions. Source checks compare each displayed citation's ID, name, source URL/name, original record key and exact excerpt with an actually captured chunk. Sources retain stable IDs for the existing `#/scholarships/{{id}}` frontend route. No official URLs are fabricated when absent in the supplied dataset.",
        "",
        "## Failure cases",
        "",
    ]
    failures = []
    for row in report.results:
        if not all(row.checks.values()) or row.response.status == "error":
            failures.append(
                f"- {row.id}: failed checks {[key for key, value in row.checks.items() if not value]}; response error `{row.response.error.code if row.response.error else 'none'}`."
            )
        for name, metric in row.metrics.items():
            if metric.status == "error":
                failures.append(f"- {row.id}/{name}: `{metric.error.code}`; {metric.error.message}")
    if report.previous_attempts:
        lines.append(
            f"Transient application failures retried: {len(report.previous_attempts)}. Previous failed attempts remain in JSON and all token/call totals; metrics describe the latest real result per question."
        )
        lines.extend(
            f"- Earlier {row.id}: `{row.response.error.code}`; application calls {len(row.llm_usage)}."
            for row in report.previous_attempts
        )
    if report.resume_history:
        lines.append(
            "Resume/pacing history: `" + json.dumps(report.resume_history, sort_keys=True) + "`."
        )
    lines.extend(
        failures
        or [
            "No execution/behavior failures were recorded. Lower metric scores still indicate retrieval/generation quality limitations; they are not treated as test-suite failures."
        ]
    )
    lines += ["", "## Limitations", ""] + ["- " + item for item in report.limitations]
    lines += [
        "",
        "## Reproduction",
        "",
        "```powershell",
        "python -m venv --system-site-packages var/eval-venv",
        r".\var\eval-venv\Scripts\python.exe -m pip install -r evaluation/requirements.lock",
        f".\\var\\eval-venv\\Scripts\\python.exe evaluation/run_eval.py --ragas --live --delay {report.configuration['application_delay_seconds']:g} --judge-delay {report.configuration['judge_delay_seconds']:g}",
        "```",
        "",
        "Use --resume to reuse validated real captures and completed metrics after an interrupted run; only incomplete metrics are requested again. Pacing may be increased and is recorded. --retry-failed retries only transient application failures, retaining earlier attempts and all costs; rejected factual output is not retried for a better score. --only ID selects a smaller run and should use a separate --output. Full reproduction may change scores because the external judge is stochastic even at temperature zero. See docs/EVALUATION.md.",
        "",
    ]
    return "\n".join(lines)


def save_report(report, output):
    summary = summarize(report)
    data = report.model_dump(mode="json")
    data["summary"] = summary
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, ensure_ascii=True, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    output.with_name("RAG_EVALUATION_REPORT.md").write_text(
        markdown_report(report, summary), encoding="utf-8", newline="\n"
    )
    return summary


def transient_failure(result):
    return bool(
        result.response.status == "error"
        and result.response.error
        and result.response.error.code
        in ("LLM_RATE_LIMITED", "LLM_TIMEOUT", "LLM_NETWORK_ERROR", "LLM_PROVIDER_UNAVAILABLE")
    )


def run(args):
    os.environ["RAGAS_DO_NOT_TRACK"] = "true"
    os.environ["LANGSMITH_TRACING"] = "false"
    import platform

    from evaluation.ragas_adapter import GeminiJudge, build_metrics

    path = ROOT / (args.cases or "evaluation/ragas_cases.json")
    dataset = load_dataset(path)
    samples = dataset.samples
    if args.only:
        samples = [sample for sample in samples if sample.id in args.only]
        if len(samples) != len(set(args.only)):
            raise ValueError("Unknown RAGAS sample ID.")
    key = os.getenv("GEMINI_API_KEY", "")
    if os.getenv("LLM_PROVIDER") != "gemini" or not key:
        raise ValueError(
            "Live RAGAS evaluation requires the configured Gemini provider and private key."
        )
    state = index_status()
    if not state.get("ready"):
        raise ValueError(
            "Production FAISS index is unavailable or stale; run normal ingestion first."
        )
    configuration = {
        "application_provider": os.getenv("LLM_PROVIDER"),
        "application_model": os.getenv("LLM_MODEL"),
        "judge_model": args.judge_model or os.getenv("RAGAS_JUDGE_MODEL") or os.getenv("LLM_MODEL"),
        "embedding_model": model_name(),
        "judge_temperature": 0,
        "answer_relevancy_strictness": 3,
        "judge_max_output_tokens": 4096,
        "judge_delay_seconds": args.judge_delay,
        "application_delay_seconds": args.delay,
        "grounding_review": os.getenv("LLM_GROUNDING_REVIEW", "auto"),
        "context_max_chars": int(os.getenv("RAG_CONTEXT_MAX_CHARS", "10000")),
        "history_max_chars": int(os.getenv("RAG_HISTORY_MAX_CHARS", "2000")),
        "application_time_budget_seconds": float(os.getenv("LLM_TOTAL_TIMEOUT_SECONDS", "90")),
        "application_max_attempts": int(os.getenv("LLM_MAX_ATTEMPTS", "3")),
        "application_retry_base_seconds": float(os.getenv("LLM_RETRY_BASE_SECONDS", "5")),
        "application_retry_max_seconds": float(os.getenv("LLM_RETRY_MAX_SECONDS", "20")),
        "application_max_output_tokens": int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2400")),
        "application_temperature": 0.2,
        "pipeline_revision": "targeted-reliability-v1",
        "pipeline_sha256": hashlib.sha256(
            b"".join(
                (ROOT / name).read_bytes()
                for name in (
                    "backend/core/llm.py",
                    "backend/core/quantities.py",
                    "backend/core/rag/query.py",
                    "backend/core/rag/retrieval.py",
                    "backend/core/agent/workflow.py",
                    "backend/core/schemas.py",
                )
            )
        ).hexdigest(),
        "application_prompt_sha256": hashlib.sha256(
            (SYSTEM_PROMPT + REVIEW_PROMPT).encode()
        ).hexdigest(),
    }
    versions = {
        name: importlib.metadata.version(name)
        for name in ["ragas", "pydantic", "google-genai", "instructor", "langchain-community"]
    }
    versions["python"] = platform.python_version()
    output = ROOT / (args.output or "evaluation/reports/ragas_results.json")
    report = EvaluationReport(
        run_id=uuid.uuid4().hex,
        created_at=datetime.now(timezone.utc),
        corpus_sha256=corpus.fingerprint(),
        dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        index=state,
        package_versions=versions,
        configuration=configuration,
        results=[],
        limitations=[
            "Small curated corpus and benchmark; expected scheme coverage is not evidence of exhaustive retrieval or generalization.",
            "Reference answers are exact section snapshots, not independent official annotations; missing data and contradictions remain in the unchanged corpus.",
            "The configured Gemini model also judges answers: correlated model bias is possible. Local MiniLM similarity is recorded as the Answer Relevancy embedding configuration.",
            "No metric runs for domain redirects, optional clarification, pipeline errors or empty retrieved contexts; those are behavioral checks with explicit skips.",
            "Model/network/quota/schema failures remain explicit; measured errors are never converted into fabricated scores.",
            "Prompt/model/library versions and budgets are recorded but remote outputs can vary. Optional evaluation dependencies are isolated; normal Docker startup does not import or run RAGAS.",
            "Source provenance and excerpts are checked structurally; they do not establish every qualitative interpretation or current official deadline.",
        ],
    )
    previous = {}
    if args.resume and output.exists():
        raw = json.loads(output.read_text(encoding="utf-8"))
        raw.pop("summary", None)
        prior = EvaluationReport.model_validate(raw)
        if (
            prior.corpus_sha256,
            prior.dataset_sha256,
            prior.index,
            {
                k: v
                for k, v in prior.configuration.items()
                if k not in ("application_delay_seconds", "judge_delay_seconds")
            },
            prior.package_versions,
        ) != (
            report.corpus_sha256,
            report.dataset_sha256,
            report.index,
            {
                k: v
                for k, v in report.configuration.items()
                if k not in ("application_delay_seconds", "judge_delay_seconds")
            },
            report.package_versions,
        ):
            raise ValueError("Resume inputs/configuration/index differ from the saved run.")
        report.run_id, report.created_at = prior.run_id, prior.created_at
        report.previous_attempts = prior.previous_attempts
        report.resume_history = prior.resume_history + [
            {
                "resumed_at": datetime.now(timezone.utc).isoformat(),
                "previous_pacing": {
                    k: v for k, v in prior.configuration.items() if k.endswith("delay_seconds")
                },
                "current_pacing": {
                    k: v for k, v in report.configuration.items() if k.endswith("delay_seconds")
                },
                "retry_transient_failures": args.retry_failed,
            }
        ]
        known_samples = {sample.id: sample for sample in dataset.samples}
        documents = {chunk.chunk_id: chunk for chunk in prepare_documents()}
        for row in [*prior.results, *prior.previous_attempts]:
            sample = known_samples.get(row.id)
            if sample is None or (
                row.question,
                row.reference,
                row.expected_scheme_ids,
                row.reference_contexts,
                row.category,
                row.top_k,
            ) != (
                sample.question,
                sample.reference,
                sample.expected_scheme_ids,
                sample.reference_contexts,
                sample.category,
                sample.top_k,
            ):
                raise ValueError("Saved evaluation row does not match the benchmark sample.")
            if any(
                chunk.chunk_id not in documents
                or chunk.to_dict() != documents[chunk.chunk_id].to_dict()
                for chunk in row.retrieved_chunks
            ):
                raise ValueError("Saved captured context does not match the preserved corpus.")
        previous = {row.id: row for row in prior.results}
    judge = GeminiJudge(configuration["judge_model"], key, delay=args.judge_delay)
    metrics = build_metrics(judge)
    try:
        for index, sample in enumerate(samples):
            old = previous.get(sample.id)
            retry = bool(args.retry_failed and old and transient_failure(old))
            if (
                (old is None or retry)
                and index
                and args.delay
                and sample.category != "out_of_domain"
            ):
                time.sleep(min(args.delay, 60))
            if retry:
                report.previous_attempts.append(old)
            result = collect(sample, report.run_id) if old is None or retry else old
            report.results.append(result)
            save_report(report, output)
            print(
                f"{sample.id}: production={result.response.status}, chunks={len(result.retrieved_chunks)}, calls={len(result.llm_usage)}",
                flush=True,
            )
            asyncio.run(
                score_result(result, sample, metrics, judge, lambda: save_report(report, output))
            )
            save_report(report, output)
        summary = save_report(report, output)
        EvaluationRun.objects.create(report=json.loads(output.read_text(encoding="utf-8")))
        print(json.dumps(summary, indent=2), flush=True)
        print("Report: " + str(output.with_name("RAG_EVALUATION_REPORT.md")), flush=True)
        return (
            1
            if summary["pipeline_errors"]
            or summary["behavior_passed"] != summary["questions"]
            or any(m["errors"] for m in summary["metrics"].values())
            else 0
        )
    finally:
        judge.close()
