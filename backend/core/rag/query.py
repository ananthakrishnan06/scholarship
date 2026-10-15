"""Local semantic domain and section classification, never scholarship decisions."""

import re
from functools import lru_cache

from core import corpus
from core.rag.embeddings import embed_local_texts, embed_query, model_name

# These describe information needs, not scheme facts, eligibility rules or answers.
DOMAIN_EXAMPLES = (
    "What scholarship schemes are available and which might suit my studies?",
    "What are the benefits and scholarship amounts?",
    "Which documents are required for a scholarship application?",
    "How do I apply for a scholarship and submit the documents?",
    "What are the eligibility criteria, income limits and exclusions?",
    "Compare education scholarships for girls, disabled students, SC ST and postgraduate students.",
    "When is the scholarship deadline and how do I renew it?",
    "How much does it provide?",
    "What documents are required?",
    "How can I apply for it?",
    "Tell me about education scholarship schemes.",
    "Who qualifies for financial assistance for postgraduate study?",
)
OTHER_EXAMPLES = (
    "Solve an arithmetic calculation or mathematical equation.",
    "Answer questions about political leaders, elections or government office holders.",
    "Tell a joke or write a funny story.",
    "Write computer code or help debug a Python program.",
    "Give the weather forecast today.",
    "Discuss cricket match results and sports scores.",
    "Explain cooking recipes and food.",
    "Explain general science, history or geography unrelated to education funding.",
    "Discuss movies, games and entertainment.",
    "Give personal medical or investment advice.",
)
INTENTS = {
    "benefits": (
        "What is the scholarship amount, financial benefits, monthly payment and duration?",
        "How much does it provide?",
        "What are the benefits?",
        "What are the benefits of a scholarship?",
    ),
    "documents": (
        "What documents, certificates and proofs are required for the scholarship?",
        "Which papers must I upload?",
        "What documents are required?",
    ),
    "application": (
        "How do I apply, register, log in, upload and submit a scholarship application?",
        "How can I apply for it?",
        "How do I apply for a scholarship?",
    ),
    "eligibility": (
        "Who is eligible, what are the qualification criteria, income limits and admission requirements?",
        "Do I qualify for this scholarship?",
        "Which scholarships require a qualifying exam?",
        "Who is eligible for the scholarship?",
        "What is the age limit?",
        "What is the income limit?",
    ),
    "exclusions": (
        "Who is excluded or not eligible and what conditions disqualify an applicant?",
        "What are the exclusions?",
    ),
    "renewal": (
        "How do I renew the scholarship and continue receiving it in subsequent years?",
        "What are the renewal requirements?",
    ),
    "deadline": (
        "When is the application deadline or last date to apply?",
        "What is the exact deadline?",
    ),
    "comparison": (
        "Compare two scholarship schemes and explain differences in benefits, criteria and application procedures.",
        "Compare these scholarships.",
    ),
    "discovery": (
        "Which scholarship schemes are available for this category or education level?",
        "Which schemes are available for girl students?",
    ),
    "clarification": ("Which scholarship should I apply for?", "What scholarship should I get?"),
    "general": (
        "Tell me about this scholarship, its purpose, benefits, eligibility and how to apply.",
        "What is this scholarship scheme?",
    ),
}
INTENT_SECTIONS = {
    "benefits": ("benefits",),
    "documents": ("documents_required",),
    "application": ("application",),
    "eligibility": ("eligibility", "exclusions", "target_groups"),
    "exclusions": ("exclusions", "eligibility"),
    "renewal": ("eligibility", "benefits", "exclusions", "application", "selection"),
    "deadline": ("application",),
    "comparison": ("benefits", "eligibility", "application"),
    "clarification": ("target_groups", "objective"),
    "discovery": ("target_groups", "eligibility", "benefits", "objective"),
}
REDIRECT = (
    "I can help with the scholarship schemes in my knowledge base, including "
    "eligibility, benefits, documents, application procedures, and related scheme information."
)


@lru_cache(maxsize=2)
def prototypes(name):
    labels = ["domain"] * len(DOMAIN_EXAMPLES) + ["other"] * len(OTHER_EXAMPLES)
    texts = list(DOMAIN_EXAMPLES + OTHER_EXAMPLES)
    for intent, examples in INTENTS.items():
        texts.extend(examples)
        labels.extend([intent] * len(examples))
    return labels, embed_local_texts(texts)


def classify_query(question: str) -> dict:
    """Nearest semantic descriptions; uncertain queries proceed to grounded RAG."""
    labels, vectors = prototypes(model_name())
    scores = vectors @ embed_query(question)[0]
    best = {
        label: float(max(scores[i] for i, item in enumerate(labels) if item == label))
        for label in set(labels)
    }
    positive, negative = max(best[label] for label in best if label != "other"), best["other"]
    outside = negative - positive > 0.035 or (positive < 0.25 and positive - negative < 0.04)
    if re.search(
        r"\b(obc|sc|st|ebc|dnt|sebc|scholarship|scholarships|fellowship|aicte|ugc|pm-yasasvi|yasasvi|pragati|saksham)\b",
        question,
        re.I,
    ):
        outside = False
    # Scheme/course names can dominate a very short embedding. Remove matched
    # corpus name words for the information-need classifier, never the search query.
    from core.rag.retrieval import filters_for

    normalized = question
    named = filters_for(question).get("scheme_id", [])
    if named:
        keep = {
            "scholarship",
            "scholarships",
            "scheme",
            "schemes",
            "students",
            "student",
            "for",
            "of",
            "the",
            "in",
            "and",
            "to",
        }
        words = {
            term
            for scheme in corpus.records(named)
            for term in re.findall(r"[a-z]+", scheme["name"].lower())
        } - keep
        pattern = (
            r"\b(?:"
            + "|".join(re.escape(word) for word in sorted(words, key=len, reverse=True))
            + r")\b"
        )
        normalized = re.sub(pattern, "scholarship", question, flags=re.I) if words else question
        normalized = re.sub(
            r"(?:scholarship[\s-]+)+scholarship", "scholarship", normalized, flags=re.I
        )
        intent_vector = embed_query(normalized)[0]
        intent_scores = vectors @ intent_vector
        for label in INTENTS:
            best[label] = float(
                max(intent_scores[i] for i, item in enumerate(labels) if item == label)
            )
    ranked = sorted(INTENTS, key=lambda intent: best[intent], reverse=True)
    intent = ranked[0]
    if best[intent] < 0.28:
        intent = "general"
    # Information-need cues route compound requests; they encode no facts.
    cues = {
        "benefits": r"\b(benefits?|amount|financial assistance|payment|how much)\b",
        "documents": r"\b(documents?|papers|proofs|certificates)\b",
        "application": r"\b(how (?:do|can|should) (?:i|we) apply|how to apply|application (?:procedures?|process|methods?|steps)|register|submit)\b",
        "eligibility": r"\b(eligible|eligibility|criteria|conditions|income|admission|disability|qualify|can .+ apply)\b",
        "exclusions": r"\b(excluded|exclusions|disqualify)\b",
    }
    requested = [key for key, pattern in cues.items() if re.search(pattern, normalized, re.I)]
    if (
        intent == "comparison"
        and requested
        and not re.search(r"\b(compare|comparison|versus|vs|differences?)\b", normalized, re.I)
    ):
        intent = max(requested, key=lambda key: best[key])
    if len(requested) == 1 and intent in (
        "benefits",
        "documents",
        "application",
        "eligibility",
        "exclusions",
    ):
        intent = requested[0]
    sections = list(INTENT_SECTIONS.get(intent, ()))
    if requested and intent not in ("discovery", "clarification", "renewal", "deadline"):
        sections = [section for key in requested for section in INTENT_SECTIONS[key]]
    # Mixed requests can retain more than one semantically close section.
    if not requested and intent in (
        "benefits",
        "documents",
        "application",
        "eligibility",
        "exclusions",
    ):
        for other in ranked[1:]:
            if other in INTENT_SECTIONS and best[other] >= best[intent] - 0.045:
                sections.extend(INTENT_SECTIONS[other])
    return {
        "out_of_scope": outside,
        "intent": intent,
        "sections": list(dict.fromkeys(sections)),
        "domain_score": round(positive, 4),
        "other_score": round(negative, 4),
        "intent_score": round(best[intent], 4),
    }
