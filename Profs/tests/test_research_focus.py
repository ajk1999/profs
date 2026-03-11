from profs.models import Publication
from profs.research_focus import heuristic_focus_summary, validate_focus_phrase


def test_validate_focus_phrase_accepts_one_to_four_words():
    assert validate_focus_phrase("machine learning") == "machine learning"
    assert validate_focus_phrase("network security") == "network security"
    assert validate_focus_phrase("very broad phrase with too many words") == ""


def test_heuristic_focus_summary_detects_security():
    publications = [
        Publication(title="Adaptive Network Security for AI Systems", abstract="Security monitoring for AI services."),
        Publication(title="Robust Authentication in Distributed Security Platforms", abstract="Authentication and cybersecurity."),
    ]

    result = heuristic_focus_summary(publications, alignment_context="AI infrastructure")
    assert result["focus_phrase"]
    assert 1 <= len(str(result["focus_phrase"]).split()) <= 4
    assert result["is_security_related"] is True
