from profs.directory_discovery import discover_from_html


def test_discovery_deduplicates_urls():
    html = """
    <html>
      <body>
        <a href="/faculty/jane-doe">Jane Doe</a>
        <a href="https://example.edu/faculty/jane-doe">Profile</a>
        <a href="/faculty/john-smith">John Smith</a>
      </body>
    </html>
    """

    config = {
        "discovery": {
            "profile_link_regexes": [r"/faculty/"],
            "profile_link_hints": ["faculty"],
        }
    }

    discoveries = discover_from_html("https://example.edu/directory", html, config)
    urls = sorted(item.profile_url for item in discoveries)

    assert urls == [
        "https://example.edu/faculty/jane-doe",
        "https://example.edu/faculty/john-smith",
    ]
