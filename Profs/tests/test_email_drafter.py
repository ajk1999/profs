from profs.email_drafter import render_email
from profs.models import FacultyProfile


def test_email_template_without_optional_sentences():
    profile = FacultyProfile(first_name="Ada", focus_phrase="machine learning")
    email = render_email(profile)

    assert "Hi Ada," in email
    assert "machine learning" in email
    assert "cybersecurity and love investing" not in email
    assert "Would love to chat about your research and how it fits into our investment theses." in email


def test_email_template_with_security_and_alignment():
    profile = FacultyProfile(
        first_name="Grace",
        focus_phrase="network security",
        is_security_related=True,
        alignment_sentence="Your work seems tightly connected to the infrastructure and resilience problems that matter in applied AI.",
    )
    email = render_email(profile)

    assert "Hi Grace," in email
    assert "network security" in email
    assert "We also have a team dedicated to cybersecurity" in email
    assert "infrastructure and resilience problems" in email
