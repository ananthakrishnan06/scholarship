# Targeted RAG reliability verification

The existing architecture, 16-scheme corpus, 139 FAISS chunks, Gemini model,
Pydantic 2.12.5, RAGAS 0.4.3, 27 benchmark questions, reference snapshots and
provenance checks are preserved. No scholarship answers or eligibility rules
were hard-coded. The baseline artifacts were not overwritten.

The ten targeted application checks passed across the recorded corrected stages.
The full fresh run then exhausted the project's daily Gemini quota. Its small
scored subset cannot establish a quality improvement. Final daily-quota/mixed-name
patches are regression-tested; a fresh complete evaluation of the final code is
still required once quota is restored.

## Observed rejection mechanisms

The baseline stored final errors and phase/cost records but not rejected drafts or
review reasons. Therefore no exact original rejection reason can honestly be
assigned retrospectively. Private diagnostic replay captured actual outputs and
validation issues before changing the pipeline. The tracked targeted artifact
retains actual chunks, FAISS scores, timings, calls, checks and rejection details.

| Case | Evidence and limitations | Applied fix and verification |
|---|---|---|
| scheme_3 | Replay review approved the answer but omitted the required note ID. Repair then added unrelated selection quantities without citing their evidence. Baseline also mixed PM-USP, rank-holder and YASASVI application chunks. | Exact-name routing, relevant-note selection, explicit required review IDs, compact validated source aliases, and no factual regeneration. Corrected application replay passed with the two PM-USP continuations and one generation. Full run also passed this application's answer. |
| scheme_11 | Replay rejected inline procedure labels 1 through 6 as unsupported quantities; the next review omitted irrelevant note IDs from other schemes. | Parse presentation labels without removing actual amounts/year ordinals; scope to the named application section. Corrected replay passed with one generation. |
| scheme_14 | Baseline generation passed, verification failed, then repair failed; original detailed issues were not saved. The pre-fix replay passed, so that intermittent rejection was not reproduced. Baseline incorrectly included YASASVI documents. | Remove unrelated scheme chunks and make review note identity explicit and strict. Both document replays passed; exact original cause remains unconfirmed. |
| saksham_conditions | Baseline recorded two rejected generations but not their issues. The pre-fix replay passed with real disability, income and admission evidence, so its original rejection could not be reproduced. | Preserve criteria/exclusions, exact spans and numeric checks; fix the general presentation-number defect and remove invalid-output regeneration. Corrected multi-condition replay passed with generation plus review. No unsupported tenfold income conversion is accepted. |
| indira_apply_documents | Baseline retrieved application/notes but no document section. Replay treated inline labels and discourse First/Second as unsupported quantities and omitted most documents. | Route both explicit needs, preserve their complete chunks/IDs, and distinguish procedural labels from factual ordinals. Corrected replay passed with application, documents and relevant notes, plus review. |
| girls_discovery | Pre-fix replay joined noncontiguous gender/institution fields in a quote; its subsequent review omitted notes. The first corrected replay exposed another false rejection of a count of three cited schemes. | Keep audience metadata distinct, remove the unrelated generic PhD candidate, retain both Indira eligibility continuations, shorten transport IDs, require exact spans/notes, and validate only scheme-count phrases against distinct cited identities. Discovery passed after that code correction; its earlier failure/cost is retained. |

Raw diagnostic model outputs remain in ignored `var/quality_diagnostics_*.json` for
local inspection. API logs retain reason codes, not raw outputs, prompts, keys or
provider exception messages. The application never uses benchmark references.

## Retrieval and runtime changes

Full corpus names outrank shared words such as merit/AICTE. Mixed full/abbreviated
comparisons and explicit category filters remain covered by tests. Explicit
information-need cues complement local semantic classification for compound
requests; "Can a third-year student apply?" routes to criteria, while procedure
questions route to application. Comparisons retrieve the requested sections per
scheme rather than always add eligibility. Named-section continuations remain in
source order; section relevance ranks ahead of ancillary sections, with unchanged
FAISS scores and context budgets. Whole-chunk deduplication/provenance is preserved.

The inspected low-precision cases had the following context changes:

| Case | Baseline context | Corrected targeted context |
|---|---|---|
| scheme_12 | Four criteria/exclusion chunks from GATE and unrelated Saksham | Two GATE criteria/exclusion chunks |
| scheme_16 | Six chunks including unrelated university-rank-holder criteria/exclusions | Four National Means-cum-Merit chunks; restrictions/notes remain |
| compare_pragati_saksham | Six chunks including unrequested eligibility | Four requested benefit/application chunks, both schemes represented |
| pragati_source | Misclassified as comparison; benefits, application and eligibility | One benefits chunk with the same verified citation metadata |
| girls_discovery | Seventeen chunks including a generic PhD candidate; missing the first Indira criteria continuation | Fourteen distinct chunks for the three explicit girl-targeted schemes, both Indira criteria continuations present |

`pragati_source` has a genuine routing defect independent of its zero precision
score: the request asks for benefits/source, not comparison/eligibility/procedures.
The baseline did not save judge explanations, and the quota run never scored this
case. It is not yet possible to determine whether the original zero also reflects
reference/judge design. The new offline adapter retains actual structured judge
explanations; no reference or metric method was changed to improve the score.

Generation/review reuse a request-local Gemini client. Short aliases expand to
original source IDs before strict validation; they change no facts, quotes or
public citation fields. Simple scoped lookups avoid review caused solely by
unrelated notes. Criteria, conflicts, comparisons, numeric challenges, uncertainty
and multiple-scheme complexity still receive review. No query rewrite/provider
classification calls were introduced; RAGAS remains offline only.

Rejected factual, JSON, schema or quote output stops immediately without regeneration
or factual fallback. Transient provider errors retry within the same phase, so a
review timeout does not generate a new answer. Attempts are capped at three with
5/10-second exponential delays, a configured delay cap, server RetryInfo and a
shared default 90-second time budget. Daily QuotaFailure stops without retry.
Every actual failed call remains in usage/audit records; missing usage stays null.
The offline judge uses the same safe quota/transport classification, with two
bounded attempts; daily exhaustion and rejected structured output are not retried.
Judge failure codes are retained in its usage records without changing metrics.

## Actual measurements

The tables below are generated from the preserved report JSON and targeted captures.

<!-- measured-results -->

Baseline run: `665afa6d748242268576bcfbbe650196`. New quota-exhausted run: `76b82e4e4a494a26a7bd413b9926c5a2`.

| Metric | Baseline | Quota-exhausted run (not comparable) |
|---|---:|---:|
| faithfulness | 0.9592 (17 scored, 0 errors, 10 skips) | 1.0000 (3 scored, 0 errors, 24 skips) |
| answer_relevancy | 0.8585 (17 scored, 0 errors, 10 skips) | 0.9463 (2 scored, 1 errors, 24 skips) |
| context_precision | 0.7029 (17 scored, 0 errors, 10 skips) | 1.0000 (2 scored, 1 errors, 24 skips) |
| context_recall | 0.9706 (17 scored, 0 errors, 10 skips) | 1.0000 (2 scored, 1 errors, 24 skips) |

These values are actual successful measurements only. The new run has only three
scored factual answers for faithfulness and two for the other metrics. They must
not be advertised as improvement over the baseline 17-answer means. The two
common scored cases are scheme_1 and scheme_2; neither establishes generalization.

| Outcome | Baseline | Quota-exhausted run |
|---|---:|---:|
| Behavior checks passed | 21 | 6 |
| Pipeline errors | 6 | 21 |
| Application calls | 63 | 67 |
| Application input tokens (known only) | 75233 | 3958 |
| Application output tokens (known only) | 17244 | 920 |
| Application calls with missing usage | 9 | 63 |
| Offline judge calls | 154 | 24 |
| Application 429 failures (including preserved attempts) | 9 | 59 |

The new run produced 21 provider-quota application failures and three offline
metric failures after exhausting the daily quota. It completed all 27 questions.
The 63 failed application requests with no returned usage are explicitly counted;
known token totals do not mean those attempts were free. This run was captured
before the final daily-quota classifier was added. Do not compare its costs or
failed-request latency as ordinary healthy-user performance.

| Timing (ms) | Baseline | Quota-exhausted run |
|---|---:|---:|
| Retrieval P50 | 21.894 | 45.849 |
| Retrieval P95 | 198.948 | 151.292 |
| Retrieval P99 | 219.669 | 345.540 |
| End-to-end P50 | 5183.963 | 17816.199 |
| End-to-end P95 | 13305.780 | 45192.547 |
| End-to-end P99 | 15939.943 | 57428.717 |

Retrieval P50 increased in this run; no FAISS speed improvement is claimed.
The much worse end-to-end latency is dominated by failed provider attempts and
backoff. The final daily-quota policy prevents those repeated requests, but its
healthy/full latency still needs measurement after quota restoration.

### Targeted application evidence (separate from RAGAS costs)

The pre-fix diagnostic replay passed 6/10 checks. The first corrected replay passed
9/10; discovery then passed following the verified-count code correction. All
ten latest targeted outcomes have traceable sources. The discovery failure is
retained rather than replaced silently. No judge scores exist for these replays.

| Targeted measure | Pre-fix replay | Corrected stages including failed discovery |
|---|---:|---:|
| Calls | 25 | 18 |
| Known input tokens | 42712 | 25324 |
| Known output tokens | 10820 | 5417 |
| Missing usage calls | 0 | 0 |

Calls fell in these diagnostic stages while the latest application outcomes
improved, but stages/status mixtures differ and include a separate cold process
for the discovery correction. These measurements do not prove full-set latency
or RAGAS improvement. All before/after/failure call records are retained.

### Verification and remaining work

- Optional-RAGAS Python suite: 115 tests passed, including both offline-judge regression tests.
- Final actual retrieval acceptance: 30/30 passed; the detected q17 regression was corrected.
- Ruff checks/format and Django system/migration checks passed.
- Normal application environment: 107 tests passed, 8 optional evaluation tests skipped.
- Targeted comparisons preserve both schemes; discovery preserves all three cited scheme identities.
- math, joke and politics retained out_of_scope with zero retrieval/application/judge calls in the complete new run.
- Original exact rejection details remain unavailable for intermittent scheme_14 and saksham_conditions; their passing replays are not proof of the original precise cause.
- Full final-code scoring, especially the four low-precision cases, still requires restored quota.
- Same-model judge bias, small corpus, dataset conflicts/missing deadlines/URLs and remote variability remain.

### Artifacts and reproduction

- Baseline: [ragas_results.json](../evaluation/reports/ragas_results.json).
- New full quota run: [raw results](../evaluation/reports/quality_fix/ragas_results.json) and [generated report](../evaluation/reports/quality_fix/RAG_EVALUATION_REPORT.md).
- [Targeted evidence](../evaluation/reports/quality_fix/targeted_checks.json) includes the failed discovery stage.
- [Computed comparison](../evaluation/reports/quality_fix/comparison.json) includes matched-case denominators.

```powershell
python evaluation/compare_runs.py --current evaluation/reports/quality_fix/ragas_results.json --output evaluation/reports/quality_fix/comparison.json
.\var\eval-venv\Scripts\python.exe evaluation/run_eval.py --ragas --live --delay 20 --judge-delay 4 --output evaluation/reports/quality_fix/final/ragas_results.json
```

The next command must run only after quota is restored. Its fresh directory/run ID
keeps the baseline and quota-exhausted run. Resume is appropriate only within an
unchanged pipeline/configuration fingerprint; the completed quota run predates the
final retry-policy patch and must not be resumed as if it measured the final code.

Corpus SHA-256: `805a64250c4e33f7d6e116d40cc2b054cb557fe6a69a6314d179a300929042ea`. Benchmark SHA-256: `441e62c3d97f17ffd579d703ef43687a59aa168aad6775ee67cc166bfb2fa2c6`.
