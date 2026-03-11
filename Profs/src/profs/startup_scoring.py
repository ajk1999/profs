from __future__ import annotations

from profs.models import FacultyProfile
from profs.utils import normalize_whitespace


DEFAULT_STARTUP_KEYWORDS = [
    "founder of",
    "co-founder of",
    "founded",
    "co-founded",
    "cofounded",
    "founder",
    "cofounder",
    "spinout",
    "spun out",
    "started a company",
    "launched a company",
    "ceo of",
    "cto of",
]

DEFAULT_RESEARCH_KEYWORDS = [
    "machine learning",
    "systems",
    "databases",
    "security",
    "ai",
    "computer vision",
    "natural language",
    "nlp",
    "llm",
    "distributed",
    "compiler",
]


def score_profile(profile: FacultyProfile, config: dict) -> FacultyProfile:
    startup_keywords = config.get("scoring", {}).get("startup_keywords", DEFAULT_STARTUP_KEYWORDS)
    research_keywords = config.get("scoring", {}).get("research_keywords", DEFAULT_RESEARCH_KEYWORDS)
    combined_text = normalize_whitespace(
        " ".join([profile.raw_profile_text, profile.raw_personal_site_text, profile.research_text])
    ).lower()

    has_signal, evidence = detect_startup_signal(combined_text, startup_keywords)
    score = 0

    title_lower = profile.title.lower()
    if "assistant professor" in title_lower:
        score += 2
    elif "associate professor" in title_lower:
        score += 1

    if any(keyword.lower() in combined_text for keyword in research_keywords):
        score += 2

    if has_signal:
        score += 5

    profile.startup_signal_hard = has_signal
    profile.startup_evidence_hard = evidence
    profile.dealflow_score = min(score, 10)
    return profile


def detect_startup_signal(text: str, keywords: list[str]) -> tuple[bool, str]:
    if not text:
        return False, ""

    lowered = text.lower()
    for keyword in keywords:
        index = lowered.find(keyword.lower())
        if index == -1:
            continue
        start = max(0, index - 30)
        end = min(len(text), index + len(keyword) + 30)
        return True, normalize_whitespace(text[start:end])[:100]
    return False, ""
