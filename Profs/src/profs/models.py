from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DiscoveredProfile:
    profile_url: str
    discovery_method: str
    confidence: float
    notes: str = ""


@dataclass
class Publication:
    title: str
    venue: str = ""
    year: int | None = None
    date: str = ""
    url: str = ""
    abstract: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FacultyProfile:
    name: str = ""
    first_name: str = ""
    title: str = ""
    email: str = ""
    personal_website: str = ""
    research_text: str = ""
    profile_url: str = ""
    university: str = ""
    department: str = ""
    startup_signal_hard: bool = False
    startup_evidence_hard: str = ""
    dealflow_score: int = 0
    publications: list[Publication] = field(default_factory=list)
    focus_phrase: str = ""
    is_security_related: bool = False
    alignment_sentence: str = ""
    draft_email: str = ""
    discovery_method: str = ""
    extraction_confidence: float = 0.0
    publication_confidence: float = 0.0
    no_recent_publications: bool = False
    notes: str = ""
    raw_profile_text: str = ""
    raw_personal_site_text: str = ""

    def to_output_row(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "first_name": self.first_name,
            "title": self.title,
            "email": self.email,
            "personal_website": self.personal_website,
            "profile_url": self.profile_url,
            "university": self.university,
            "department": self.department,
            "research_text": self.research_text,
            "startup_signal_hard": self.startup_signal_hard,
            "startup_evidence_hard": self.startup_evidence_hard,
            "dealflow_score": self.dealflow_score,
            "publications_json": [publication.to_dict() for publication in self.publications],
            "focus_phrase": self.focus_phrase,
            "is_security_related": self.is_security_related,
            "alignment_sentence": self.alignment_sentence,
            "draft_email": self.draft_email,
            "discovery_method": self.discovery_method,
            "extraction_confidence": self.extraction_confidence,
            "publication_confidence": self.publication_confidence,
            "no_recent_publications": self.no_recent_publications,
            "notes": self.notes,
        }
