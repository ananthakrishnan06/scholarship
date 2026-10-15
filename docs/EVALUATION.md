# Evaluation

`python evaluation/run_eval.py` evaluates 30 manually annotated retrieval questions
against the actual persisted FAISS index and sentence-transformer model. The report
in `evaluation/reports/latest.json` measures scheme/section hits and retrieval timing.
It does not call a language model or claim answer correctness from retrieved quotes.

`python evaluation/run_eval.py --live --delay 20` runs 16 acceptance cases against
configured Gemini, including the requested 10 examples, a second contradiction case,
and postgraduate/SC-ST/PhD/monthly/disability discovery. Conversation setup turns
precede follow-up, deadline and unsupported-amount questions. The live report records
actual generated answers, statuses, sources/excerpts, checks and measured latency.
Use `--only CASE_ID` for a focused rerun and `--output` for a separate report.

Checks include requested status, expected fact patterns, relevant source prefixes,
multiple sources for discovery, exact excerpt provenance, absence of off-topic
citations, and successful conversation setup. The checks use test facts, not a
production question-answer lookup. Model grounding review adds semantic scrutiny but
neither it nor the spot-check patterns prove all factual paraphrases correct.

Rate limits can fail acceptance cases even when the implementation is correct;
those failures remain visible in reports. Pace calls rather than conceal them with
fallback excerpts. Live runs consume provider tokens. Test sessions are deleted
at the end of each case, while content-free execution/usage audit rows remain.

Backend pytest uses mocked providers/embeddings where needed. It verifies the actual
generated answer reaches the API, evidence checks, malformed outputs, grounding
rejection without regeneration, input rejection, tool bounds, model errors, conversation history,
source contradictions, index integrity, and removal of profile routes. Frontend tests
verify natural-text rendering, source names, absent profiles and clear provider errors.
Browser tests on isolated ports mock provider responses; real provider acceptance
is measured separately. The previous profile evaluation and 96.7% combined legacy
score are obsolete and are not claimed for the conversational application.

## Current demo and efficiency checks

`python evaluation/check_retrieval_efficiency.py` checks actual local domain/intent
embeddings, focused sections, context budgets and all-16 indexed/application coverage.
`python evaluation/run_eval.py --live --cases evaluation/demo_cases.json --delay 15 --output evaluation/reports/demo_live.json`
runs 14 current demo scenarios, including benefits, documents, eligibility, application,
follow-up, comparison/discovery, missing dates, ambiguity and out-of-domain requests.
It records each actual model phase, tokens, latency and retrieval-call count; the
fixtures enforce zero calls outside the domain and one for simple lookups.
`--cases` selects fixtures; `--only` allows a focused rerun. Original 16-case fixtures
remain, with their old arithmetic expectation changed to scholarship-only redirection.

`retrieval_optimized.json` records the current 30-question retrieval run;
`efficiency.json` records local classifier/context measurements; `demo_initial.json`
preserves the first live run's failures; `demo_live.json` records the corrected run.
See DEMO_READINESS.md for actual results, measured savings and limits.

## RAGAS extension of the existing evaluator

The evaluator introduced in commit `f043784` remains `evaluation/run_eval.py`.
Existing retrieval-only and live acceptance modes remain available. The new
`--ragas --live` mode delegates only its offline scoring/capture logic to
`evaluation/ragas_eval.py`; this is not a parallel application or a new retriever.

Production flow: QueryRequest -> existing local semantic domain handling ->
LangGraph retrieval tool -> MiniLM/FAISS -> actual bounded section chunks ->
configured Gemini generation/validation/review -> ScholarshipAnswer.
An opt-in in-process trace records final retrieved chunks, their metadata/scores,
requested/effective top-k, context sizes and retrieval timing from that very
execution. The public API response stays unchanged. Normal queries import no
RAGAS code and incur no evaluator/judge cost.

Offline flow: the same production flow -> actual answer/contexts -> RAGAS metric
judges -> validated results -> JSON plus generated Markdown. Each question has a
new disposable session, deleted after capture. Anonymous execution/token audit
rows remain; no session token, API key or raw provider exception is exported.
RAGAS telemetry and LangSmith tracing are disabled for the offline run.

### Tested dependency/API versions

| Component | Version / policy |
|---|---|
| Python workspace | 3.10.10 |
| Pydantic | 2.12.5, preserved |
| google-genai | 1.63.0, preserved |
| RAGAS | 0.4.3, optional offline environment |
| Instructor | 1.14.5, compatible with existing SDK/requests |
| LangChain Community | 0.4.1; 0.4.2 removed the VertexAI module imported by RAGAS 0.4.3 |
| rich | 14.3.4 in evaluation environment; application remains 15.0.0 |

`evaluation/requirements.txt` extends the project's requirements; its independent
`requirements.lock` captures the 142-package tested closure with provider extras.
Runtime `requirements.txt`, `requirements.lock`, Dockerfiles and Compose are
unchanged. The existing dependency-lock script now accepts input/output paths,
handles included requirement files and resolves optional extras; it rejects
installed versions that violate requirements.

```powershell
python -m venv --system-site-packages var/eval-venv
.\var\eval-venv\Scripts\python.exe -m pip install -r evaluation/requirements.lock
.\var\eval-venv\Scripts\python.exe scripts/lock_dependencies.py --requirements evaluation/requirements.txt --output evaluation/requirements.lock
.\var\eval-venv\Scripts\python.exe -m pytest -q
.\var\eval-venv\Scripts\python.exe evaluation/run_eval.py --ragas --live --delay 20 --judge-delay 4
```

For an independent machine, install the normal runtime lock first, then the
optional evaluation lock in its isolated environment. `var` is ignored. A normal
Docker image remains the application image and does not start evaluation.

The installed `ragas.metrics.collections` classes use `ascore` with explicit
`user_input`, `response`, `retrieved_contexts`, and/or `reference` arguments. The
adapter implements the installed `InstructorBaseRagasLLM` interface with the
existing Google SDK and strict JSON Schema, avoiding the typed-schema/safety-settings
issues seen with SDK adapters. RAGAS itself supplies metric prompts and computes
the scores; the adapter never assigns scores. Local cached MiniLM implements the
installed BaseRagasEmbedding interface, so Answer Relevancy has no paid embedding
calls. Strictness is the RAGAS default of three generated questions.

[Official Gemini guide](https://docs.ragas.io/en/stable/howtos/integrations/gemini/)
and [versioned metric source](https://github.com/vibrantlabsai/ragas/tree/v0.4.3/src/ragas/metrics/collections)
provide upstream references; implementation/tests use the installed 0.4.3 signatures.

### Benchmark and validation

`evaluation/ragas_cases.json` has 27 questions and exact reference section snapshots
covering the 16 supplied schemes. Categories include direct facts, criteria,
benefits, procedures, documents, multiple conditions/chunks/schemes, missing dates,
clarification, provenance and three off-domain requests. The source JSON/JSONL,
QA report and existing FAISS index remain unchanged.

`EvaluationSample` validates the question through existing QueryRequest, aligned
reference IDs/contexts, categories and expected response statuses. Loading checks
corpus fingerprint, known scheme IDs, exact chunk/reference text and factual
reference answers. Reference generation uses the source dataset only to establish
benchmark labels. During answering, no reference answer/context is passed to the
application; retrieval happens through normal FAISS search, not a dataset lookup.

`EvaluationResult` reuses existing ScholarshipAnswer, Citation and the existing
Chunk type (now a validated frozen Pydantic dataclass). It checks captured context
alignment, unique chunks, finite/bounded retrieval scores, positive timings and
explicit metric states. Failed/undefined metrics carry errors and null scores;
there are no fabricated zero/perfect substitutes. A successful answer must have
supporting source excerpts. Every citation is checked against an actually captured
chunk, including original record identity, source metadata and exact excerpt.
Internal source links continue to use the same verified scheme ID/detail route.

### Metrics and interpretation

| Metric | Actual inputs | Interpretation |
|---|---|---|
| Faithfulness | Question, answer, captured contexts | Answer claims supported by retrieved evidence |
| Answer Relevancy | Question, answer; local embeddings | Relevance based on judge-generated questions and similarity |
| Context Precision | Question, reference, ranked captured contexts | Relevant contexts appearing earlier |
| Context Recall | Question, reference, captured contexts | Reference claims covered by retrieved evidence |

Out-of-domain redirects and ambiguous clarification lack factual reference contexts
and are excluded from all four metric means. Their statuses, sources and tool/model
counts are tested separately. Clear unrelated requests must have zero retrieval,
application provider and judge calls. Application failures/empty contexts are
explicit skips, with failures retained in the denominator of behavior checks.

Reports show successful numeric-score denominators plus errors/skips. Means are
not averaged with fabricated scores and no combined accuracy score is claimed.
A small self-judged corpus benchmark can miss errors, and retrieved shortlist
coverage does not imply exhaustive discovery. References retain dataset limitations
and conflicting source statements; external official details were not refreshed.

### Results, costs and resume

- `evaluation/reports/ragas_results.json`: validated raw answers, actual captured
  chunks, references, IDs, metadata, scores, requested/effective top-k, provider
  attempts, tokens, timings, checks, per-metric values/errors and generated summary.
- `evaluation/reports/RAG_EVALUATION_REPORT.md`: generated solely from those results.
- `evaluation/reports/ragas_initial.json`: preserved first full run, including rate
  failures and rejected generated outputs; scores are not manually edited.

Per-query end-to-end latency includes normal domain/retrieval/generation/validation,
not offline metric judging. Retrieval percentiles exclude queries that skip it.
Per-metric judge latency is separate. Actual application and evaluator token/call
usage are separate, include all attempts, and explicitly count unavailable usage.
Top-k is the requested primary retrieval limit; relevant supporting sections/notes
may add chunks before the existing context budget is applied.

Checkpoints save real captures before judging and progress after each metric.
`--resume` reuses completed work only after corpus/index, dataset, package versions,
model/configuration, benchmark identity and captured source text validation. Pacing
can change and is recorded in resume history. No API response or fabricated source
is constructed to improve scores.

```powershell
.\var\eval-venv\Scripts\python.exe evaluation/run_eval.py --ragas --live --resume --retry-failed --delay 20 --judge-delay 4
```

`--retry-failed` retries only transient rate, network, timeout or server failures;
it never reruns rejected factual output to select a better score. Prior failed
attempts are retained and included in token/call totals. Unfinished/error metric
judging may retry the same already captured real answer; completed scores stay
unchanged. Both the initial report and previous-attempt list remain inspectable.
Pacing reduces bursts but cannot guarantee quota availability. A nonzero exit code
means a recorded pipeline/behavior/metric error; low valid metric values alone are
not an execution error. Use `--only ID --output var/focused.json` for isolated runs.


## Targeted reliability and quota verification

The baseline run `665afa6d748242268576bcfbbe650196` and its report remain unchanged.
The targeted fix retains the same 27 questions, reference snapshots, four RAGAS
metrics, local embeddings and provenance checks. Diagnostic replays keep their
failed attempts; they are application checks, not substitute RAGAS measurements.

New opt-in trace fields record safe rejection reasons, quota type and retry timing.
No raw provider exception, key, prompt or rejected draft is logged by the API.
Offline `judge_diagnostics` retains actual validated RAGAS structured judgments,
including context-precision explanations. Scores still come from RAGAS itself.
Pipeline/prompt fingerprints and retry/output budgets are recorded with each run.

Use a fresh output directory after a code/configuration change; `--resume` deliberately
rejects a saved run from a different pipeline fingerprint. Never overwrite the
baseline. Example once quota is available:

```powershell
.\var\eval-venv\Scripts\python.exe evaluation/run_eval.py --ragas --live --delay 20 --judge-delay 4 --output evaluation/reports/quality_fix/final/ragas_results.json
```

Gemini quota is per project, not per API key; an additional key on the same project
does not restore an exhausted daily quota. See the [official quota documentation](https://ai.google.dev/gemini-api/docs/rate-limits).
The captured provider failure identified the 500-request daily free-tier quota.
Daily quota failures are not treated as transient retries; no score is substituted.
See [QUALITY_FIX.md](QUALITY_FIX.md) for measured results and remaining work.
