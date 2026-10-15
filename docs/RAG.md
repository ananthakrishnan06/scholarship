# Retrieval, domain detection and grounded generation

The 16-record authoritative JSON, 139 section chunks, original-record provenance,
MiniLM CPU embeddings, FAISS IndexFlatIP, checksums/versioned CURRENT pointer and
explicit ingestion are retained unchanged. Every scheme has indexed application
information. No index rebuild is needed for this change: existing scheme IDs and
section metadata already support section retrieval and internal navigation.

The API first embeds the raw question locally and compares it with cached domain
and information-need descriptions. This has no scheme eligibility rules, topic
if/else rejection list, generated scholarship facts or provider calls. Confident
unrelated requests return out_of_scope with scholarship guidance, no sources, no
retrieval tool, no Gemini calls. Uncertain requests proceed to bounded RAG. A missing
local model returns an explicit error; it is never downloaded during a request.

Corpus-derived names and explicit categories constrain candidates. For information
need classification, matched name words are normalized without changing the search
question. Section routing combines the existing semantic classifier with a small set of
information-need cues for compound requests. These cues contain no scheme facts,
thresholds or eligibility decisions. Full-name matches outrank shared name words;
remaining abbreviated names and explicit category filters stay supported.
Focused requests search relevant sections, such as benefits, documents or application.
Comparisons retrieve the sections actually requested from each named scheme.
Named-section continuations remain in their original order. Discovery preserves
scheme identity and checks explicit audiences against corpus target-group metadata.
Criteria retain restrictions and notes; narrow lookups retain related notes and
flagged contradictions. The context budget still bounds all selected evidence.

Context preparation deduplicates whole chunks by scheme, section and content, so
identical amounts from distinct schemes remain separate sources. It does not rewrite
facts or quotes. Notes are prioritized before enforcing RAG_CONTEXT_MAX_CHARS (10000).
Recent history is bounded to four messages and RAG_HISTORY_MAX_CHARS (2000). The
existing total LLM input/output limits still apply. No complete raw scheme records
or entire dataset is passed to the provider in a normal query.

Gemini returns answer/status/supports. Natural answer text reaches React unchanged;
exact quotes identify evidence separately. Schema, exact membership, generic numeric and URL checks
apply to every scholarship generation. LLM_GROUNDING_REVIEW=auto adds a separate
semantic review for uncertainty/complexity; simple lookups need one call. always
reviews every generation. Review receives cited evidence and important notes, not
all irrelevant retrieved chunks. Every supplied important note must be examined;
unknown note IDs are rejected. Factual/schema/quote rejections stop without a new
answer attempt. Only transient provider failures retry, within the same phase;
daily exhaustion stops immediately. All attempted calls remain counted.
Request-local source aliases reduce repeated identifier tokens and expand back to
the original IDs before strict validation. They never alter quotes or answer text.
Procedure list labels and verified counts of cited schemes are distinguished from
factual amounts/durations; unsupported numeric facts remain rejected.

Source cards always offer an internal View Full Scheme link based on the verified
scheme ID and existing #/scholarships/{id} route. An available official link is
additional; a missing external link never prevents internal source navigation.

Semantic classification and grounding are fallible. English-only quality is tested;
multilingual quality, complete discovery and universal factual correctness are not
established. See DEMO_READINESS.md for measured results and acceptance limits.
