from profs.profile_parser import parse_profile_html


def test_profile_parser_uses_safe_fallbacks():
    html = """
    <html>
      <head><title>Jane Doe | Example University</title></head>
      <body>
        <p>Associate Professor of Computer Science</p>
        <p>Contact: jane@example.edu</p>
      </body>
    </html>
    """

    profile = parse_profile_html(
        profile_url="https://example.edu/faculty/jane-doe",
        html=html,
        university="Example University",
        department="Computer Science",
        config={"titles": {"aliases": {"Associate Professor": ["associate professor"]}}},
    )

    assert profile.name == "Jane Doe"
    assert profile.first_name == "Jane"
    assert profile.title == "Associate Professor"
    assert profile.email == "jane@example.edu"
    assert profile.personal_website == ""
    assert profile.research_text == ""
