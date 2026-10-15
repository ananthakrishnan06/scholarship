"""Compare preserved real reports without substituting scores or changing references."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="evaluation/reports/ragas_results.json")
    parser.add_argument("--current", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    import django

    django.setup()
    from evaluation.ragas_eval import summarize
    from evaluation.schemas import METRICS, EvaluationReport

    reports = []
    for path in (args.baseline, args.current):
        raw = json.loads((ROOT / path).read_text(encoding="utf-8"))
        raw.pop("summary", None)
        reports.append(EvaluationReport.model_validate(raw))
    baseline, current = reports
    if baseline.run_id == current.run_id:
        raise ValueError("Comparison requires distinct real runs.")
    if (baseline.corpus_sha256, baseline.dataset_sha256) != (
        current.corpus_sha256,
        current.dataset_sha256,
    ):
        raise ValueError("Comparison requires unchanged corpus and reference dataset.")
    summaries = [summarize(report) for report in reports]
    rows = [{row.id: row for row in report.results} for report in reports]
    common = {}
    for metric in METRICS:
        ids = sorted(set(rows[0]) & set(rows[1]))
        ids = [qid for qid in ids if all(row[qid].metrics[metric].status == "ok" for row in rows)]
        common[metric] = {
            "ids": ids,
            "scored": len(ids),
            "before": sum(rows[0][qid].metrics[metric].score for qid in ids) / len(ids)
            if ids
            else None,
            "after": sum(rows[1][qid].metrics[metric].score for qid in ids) / len(ids)
            if ids
            else None,
        }
    data = {
        "baseline_run_id": baseline.run_id,
        "new_run_id": current.run_id,
        "corpus_sha256": baseline.corpus_sha256,
        "dataset_sha256": baseline.dataset_sha256,
        "before": summaries[0],
        "after": summaries[1],
        "common_scored_cases": common,
        "comparison_limit": "Compare denominators and failures before interpreting means; partial/scored-subset means do not establish full-set improvement.",
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"Compared {baseline.run_id} -> {current.run_id}; report: {args.output}")


if __name__ == "__main__":
    main()
