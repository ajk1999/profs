from __future__ import annotations

import json
import re
from collections import Counter

from profs.models import FacultyProfile, Publication
from profs.settings import Settings
from profs.utils import STOPWORDS, count_words, normalize_whitespace


SECURITY_KEYWORDS = {
    "security",
    "secure",
    "privacy",
    "cryptography",
    "cybersecurity",
    "cyber",
    "malware",
    "phishing",
    "authentication",
    "authorization",
    "vulnerability",
}

FOCUS_PATTERNS = [
    ("language models", {"language", "model", "models", "llm", "llms"}),
    ("machine learning", {"machine", "learning"}),
    ("computer vision", {"computer", "vision"}),
    ("distributed systems", {"distributed", "systems"}),
    ("database systems", {"database", "databases"}),
    ("network security", {"network", "security"}),
    ("cybersecurity", {"cybersecurity", "security"}),
    ("data systems", {"data", "systems"}),
]


def summarize_research_focus(profile: FacultyProfile, settings: Settings) -> FacultyProfile:
    if not profile.publications:
        profile.focus_phrase = ""
        profile.is_security_related = False
        profile.alignment_sentence = ""
        return profile

    fallback = heuristic_focus_summary(profile.publications, settings.alignment_context)

    if not settings.openai_api_key:
        profile.focus_phrase = fallback["focus_phrase"]
        profile.is_security_related = fallback["is_security_related"]
        profile.alignment_sentence = fallback["alignment_sentence"]
        return profile

    model_result = _model_focus_summary(profile.publications, settings)
    if not model_result:
        profile.focus_phrase = fallback["focus_phrase"]
        profile.is_security_related = fallback["is_security_related"]
        profile.alignment_sentence = fallback["alignment_sentence"]
        return profile

    focus_phrase = validate_focus_phrase(model_result.get("focus_phrase", ""))
    profile.focus_phrase = focus_phrase or fallback["focus_phrase"]
    profile.is_security_related = bool(model_result.get("is_security_related", fallback["is_security_related"]))
    alignment_sentence = normalize_whitespace(model_result.get("alignment_sentence", ""))
    profile.alignment_sentence = alignment_sentence if alignment_sentence else fallback["alignment_sentence"]
    return profile


def call_openai_helper(settings: Settings, instructions: str, prompt: str) -> str:
    """All model calls go through this helper so the SDK usage is isolated."""

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt},
        ],
    )
    return normalize_whitespace(response.output_text)


def validate_focus_phrase(phrase: str) -> str:
    cleaned = normalize_whitespace(phrase)
    if not cleaned:
        return ""
    if count_words(cleaned) > 4:
        return ""
    return cleaned


def heuristic_focus_summary(publications: list[Publication], alignment_context: str = "") -> dict[str, object]:
    combined_text = " ".join(
        f"{publication.title} {publication.abstract}" for publication in publications if publication.title or publication.abstract
    ).lower()

    focus_phrase = _infer_focus_phrase(combined_text)
    security_related = _is_security_related(combined_text)
    alignment_sentence = ""

    if alignment_context and any(keyword in combined_text for keyword in ("data", "ai", "system", "infrastructure", "security")):
        alignment_sentence = (
            "Your work seems tightly connected to the infrastructure challenges that matter most in applied AI."
        )
        if security_related:
            alignment_sentence = (
                "Your work seems tightly connected to the infrastructure and resilience problems that matter in applied AI."
            )

    return {
        "focus_phrase": focus_phrase,
        "is_security_related": security_related,
        "alignment_sentence": alignment_sentence,
    }


def _model_focus_summary(publications: list[Publication], settings: Settings) -> dict[str, object]:
    prompt_payload = [
        {
            "title": publication.title,
            "venue": publication.venue,
            "year": publication.year,
            "abstract": publication.abstract,
        }
        for publication in publications
    ]
    instructions = (
        "Return JSON with keys focus_phrase, is_security_related, alignment_sentence. "
        "focus_phrase must be 1 to 4 words and broad enough to fit all papers. "
        "alignment_sentence should be blank unless clearly warranted."
    )
    prompt = json.dumps(prompt_payload, ensure_ascii=True)

    try:
        raw = call_openai_helper(settings, instructions, prompt)
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _infer_focus_phrase(combined_text: str) -> str:
    for label, required_terms in FOCUS_PATTERNS:
        if required_terms.issubset(set(_tokenize(combined_text))):
            return label

    tokens = [token for token in _tokenize(combined_text) if token not in STOPWORDS]
    counts = Counter(tokens)
    for word, _ in counts.most_common():
        if len(word) >= 4:
            return word
    return ""


def _is_security_related(combined_text: str) -> bool:
    tokens = set(_tokenize(combined_text))
    return any(keyword in tokens or keyword in combined_text for keyword in SECURITY_KEYWORDS)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z]+", text.lower())
