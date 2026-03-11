from __future__ import annotations

import re
from collections import deque
from typing import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from profs.browser_client import BrowserClient
from profs.http_client import HttpClient
from profs.models import DiscoveredProfile
from profs.utils import parse_json_ld_people, strip_url_fragment


DEFAULT_PROFILE_HINTS = ("faculty", "people", "person", "profile", "staff", "directory", "/~")
PAGINATION_TEXT = {"next", "older", "more", ">", ">>", "›", "»"}


def discover_faculty_pages(
    directory_url: str,
    http_client: HttpClient,
    config: dict,
    browser_client: BrowserClient | None = None,
    max_pages: int | None = None,
) -> list[DiscoveredProfile]:
    """Discover profile URLs from a directory page using layered strategies."""

    discovery_config = config.get("discovery", {})
    max_pages = max_pages or discovery_config.get("max_pages", 5)
    seen_pages: set[str] = set()
    pages_to_visit = deque([directory_url])
    collected: dict[str, DiscoveredProfile] = {}

    while pages_to_visit and len(seen_pages) < max_pages:
        page_url = pages_to_visit.popleft()
        normalized_page_url = strip_url_fragment(page_url)
        if normalized_page_url in seen_pages:
            continue
        seen_pages.add(normalized_page_url)

        html = http_client.get_html(page_url)
        if not html:
            continue

        _merge_discoveries(
            collected,
            discover_from_html(page_url, html, config, method="html_links"),
        )
        _merge_discoveries(
            collected,
            discover_from_json_ld(page_url, html),
        )

        for next_page in discover_pagination_links(page_url, html, config):
            if strip_url_fragment(next_page) not in seen_pages:
                pages_to_visit.append(next_page)

    _merge_discoveries(
        collected,
        discover_from_sitemaps(directory_url, http_client, config),
    )

    if not collected and browser_client:
        browser_html = browser_client.fetch_html(directory_url)
        if browser_html:
            _merge_discoveries(
                collected,
                discover_from_html(directory_url, browser_html, config, method="browser_rendered"),
            )
            _merge_discoveries(
                collected,
                discover_from_json_ld(directory_url, browser_html, method="browser_jsonld"),
            )

    return sorted(
        collected.values(),
        key=lambda item: (-item.confidence, item.profile_url),
    )


def discover_from_html(
    base_url: str,
    html: str,
    config: dict,
    method: str = "html_links",
) -> list[DiscoveredProfile]:
    soup = BeautifulSoup(html, "html.parser")
    profile_regexes = [re.compile(pattern) for pattern in config.get("discovery", {}).get("profile_link_regexes", [])]
    profile_hints = tuple(config.get("discovery", {}).get("profile_link_hints", list(DEFAULT_PROFILE_HINTS)))
    discovered: list[DiscoveredProfile] = []

    for link in soup.find_all("a", href=True):
        href = urljoin(base_url, link["href"])
        if not href.startswith(("http://", "https://")):
            continue

        score = _score_profile_candidate(href, link.get_text(" ", strip=True), profile_regexes, profile_hints)
        if score <= 0:
            continue

        discovered.append(
            DiscoveredProfile(
                profile_url=strip_url_fragment(href),
                discovery_method=method,
                confidence=min(score, 0.95),
                notes=f"matched via {method}",
            )
        )

    return _deduplicate_discoveries(discovered)


def discover_pagination_links(base_url: str, html: str, config: dict) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    pagination_param = config.get("discovery", {}).get("pagination_param", "page")
    next_pages: list[str] = []

    for link in soup.find_all("a", href=True):
        href = urljoin(base_url, link["href"])
        text = link.get_text(" ", strip=True).lower()
        if pagination_param in href or text in PAGINATION_TEXT:
            next_pages.append(strip_url_fragment(href))

    return list(dict.fromkeys(next_pages))


def discover_from_json_ld(base_url: str, html: str, method: str = "jsonld_person") -> list[DiscoveredProfile]:
    soup = BeautifulSoup(html, "html.parser")
    discovered: list[DiscoveredProfile] = []
    for person in parse_json_ld_people(soup):
        candidate_url = person.get("url") or person.get("@id")
        if not candidate_url:
            continue
        full_url = urljoin(base_url, candidate_url)
        discovered.append(
            DiscoveredProfile(
                profile_url=strip_url_fragment(full_url),
                discovery_method=method,
                confidence=0.9,
                notes="schema.org Person",
            )
        )
    return _deduplicate_discoveries(discovered)


def discover_from_sitemaps(directory_url: str, http_client: HttpClient, config: dict) -> list[DiscoveredProfile]:
    parsed = urlparse(directory_url)
    site_root = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{site_root}/robots.txt"
    sitemap_urls: list[str] = []

    robots_text = http_client.get_html(robots_url)
    for line in robots_text.splitlines():
        if line.lower().startswith("sitemap:"):
            sitemap_urls.append(line.split(":", 1)[1].strip())

    if not sitemap_urls:
        sitemap_urls.append(f"{site_root}/sitemap.xml")

    discoveries: list[DiscoveredProfile] = []
    for sitemap_url in sitemap_urls[: config.get("discovery", {}).get("max_sitemaps", 3)]:
        sitemap_xml = http_client.get_html(sitemap_url)
        if not sitemap_xml:
            continue
        discoveries.extend(_discover_from_sitemap_xml(sitemap_xml, config))

    return _deduplicate_discoveries(discoveries)


def _discover_from_sitemap_xml(xml_text: str, config: dict) -> list[DiscoveredProfile]:
    locs = re.findall(r"<loc>(.*?)</loc>", xml_text, flags=re.IGNORECASE)
    profile_regexes = [re.compile(pattern) for pattern in config.get("discovery", {}).get("profile_link_regexes", [])]
    profile_hints = tuple(config.get("discovery", {}).get("profile_link_hints", list(DEFAULT_PROFILE_HINTS)))
    discoveries: list[DiscoveredProfile] = []

    for loc in locs:
        score = _score_profile_candidate(loc, "", profile_regexes, profile_hints)
        if score <= 0:
            continue
        discoveries.append(
            DiscoveredProfile(
                profile_url=strip_url_fragment(loc),
                discovery_method="sitemap",
                confidence=0.65,
                notes="sitemap candidate",
            )
        )

    return discoveries


def _score_profile_candidate(
    url: str,
    anchor_text: str,
    profile_regexes: Iterable[re.Pattern[str]],
    profile_hints: tuple[str, ...],
) -> float:
    path = urlparse(url).path.lower()
    anchor = anchor_text.lower()

    for pattern in profile_regexes:
        if pattern.search(path):
            return 0.9

    score = 0.0
    if any(hint in path for hint in profile_hints):
        score += 0.45
    if any(word in anchor for word in ("professor", "faculty", "staff")):
        score += 0.15
    if re.search(r"/[a-z\-]+/?$", path):
        score += 0.15
    if anchor and len(anchor.split()) >= 2:
        score += 0.1
    return score


def _merge_discoveries(collected: dict[str, DiscoveredProfile], discoveries: list[DiscoveredProfile]) -> None:
    for discovery in discoveries:
        existing = collected.get(discovery.profile_url)
        if not existing or discovery.confidence > existing.confidence:
            collected[discovery.profile_url] = discovery


def _deduplicate_discoveries(discoveries: list[DiscoveredProfile]) -> list[DiscoveredProfile]:
    deduped: dict[str, DiscoveredProfile] = {}
    _merge_discoveries(deduped, discoveries)
    return list(deduped.values())
