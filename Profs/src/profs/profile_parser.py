from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from profs.http_client import HttpClient
from profs.models import FacultyProfile
from profs.utils import compact_text_chunks, extract_first_name, find_first_email, normalize_whitespace, parse_json_ld_people


EXCLUDED_WEBSITE_DOMAINS = {
    "twitter.com",
    "x.com",
    "linkedin.com",
    "facebook.com",
    "github.com",
    "scholar.google.com",
    "researchgate.net",
    "orcid.org",
    "dblp.org",
    "semanticscholar.org",
    "youtube.com",
    "instagram.com",
    "bsky.app",
    "bluesky.social",
    "arxiv.org",
}


def extract_profile(
    profile_url: str,
    university: str,
    department: str,
    http_client: HttpClient,
    config: dict,
) -> FacultyProfile:
    html = http_client.get_html(profile_url)
    if not html:
        return FacultyProfile(
            profile_url=profile_url,
            university=university,
            department=department,
            notes="failed to fetch profile page",
        )

    profile = parse_profile_html(
        profile_url=profile_url,
        html=html,
        university=university,
        department=department,
        config=config,
    )

    if profile.personal_website and profile.personal_website != profile.profile_url:
        profile.raw_personal_site_text = normalize_whitespace(http_client.get_html(profile.personal_website))

    return profile


def parse_profile_html(
    profile_url: str,
    html: str,
    university: str,
    department: str,
    config: dict,
) -> FacultyProfile:
    soup = BeautifulSoup(html, "html.parser")
    people = parse_json_ld_people(soup)
    person = people[0] if people else {}
    raw_text = normalize_whitespace(soup.get_text(" ", strip=True))

    name = _extract_name(soup, person)
    title = normalize_title(_extract_title(soup, person), config)
    email = _extract_email(soup, person)
    personal_website = _extract_personal_website(soup, person, profile_url)
    research_text = _extract_research_text(soup, person)

    extraction_signals = [
        bool(name),
        bool(title),
        bool(email),
        bool(personal_website),
        bool(research_text),
        bool(person),
    ]
    confidence = round(sum(extraction_signals) / len(extraction_signals), 2)

    return FacultyProfile(
        name=name,
        first_name=extract_first_name(name),
        title=title,
        email=email,
        personal_website=personal_website,
        research_text=research_text,
        profile_url=profile_url,
        university=university,
        department=department,
        extraction_confidence=confidence,
        raw_profile_text=raw_text,
    )


def normalize_title(title: str, config: dict) -> str:
    normalized = normalize_whitespace(title)
    aliases = config.get("titles", {}).get("aliases", {})
    lowered = normalized.lower()
    for canonical, variants in aliases.items():
        for variant in variants:
            if variant.lower() in lowered:
                return canonical
    return normalized


def _extract_name(soup: BeautifulSoup, person: dict) -> str:
    if person.get("name"):
        return normalize_whitespace(person["name"])

    header = soup.find(["h1", "h2"])
    if header:
        return normalize_whitespace(header.get_text(" ", strip=True))

    title_tag = soup.find("title")
    if title_tag:
        return normalize_whitespace(re.sub(r"\s*[|\-].*$", "", title_tag.get_text(strip=True)))

    return ""


def _extract_title(soup: BeautifulSoup, person: dict) -> str:
    if person.get("jobTitle"):
        return normalize_whitespace(person["jobTitle"])

    title_pattern = re.compile(
        r"(Assistant Professor|Associate Professor|Professor|Teaching Professor|Research Professor|Lecturer|Research Scientist)",
        re.IGNORECASE,
    )
    for tag in soup.find_all(["div", "span", "p", "h2", "h3", "li"]):
        text = normalize_whitespace(tag.get_text(" ", strip=True))
        match = title_pattern.search(text)
        if match:
            return normalize_whitespace(match.group(1))

    return ""


def _extract_email(soup: BeautifulSoup, person: dict) -> str:
    if person.get("email"):
        return normalize_whitespace(person["email"]).replace("mailto:", "")

    mailto = soup.find("a", href=re.compile(r"^mailto:", re.IGNORECASE))
    if mailto and mailto.get("href"):
        return mailto["href"].replace("mailto:", "").strip()

    return find_first_email(soup.get_text(" ", strip=True))


def _extract_personal_website(soup: BeautifulSoup, person: dict, profile_url: str) -> str:
    person_url = person.get("url")
    if person_url and person_url != profile_url:
        return normalize_whitespace(person_url)

    best_candidate = ""
    for link in soup.find_all("a", href=True):
        href = urljoin(profile_url, link["href"])
        if href == profile_url:
            continue
        if any(excluded in href.lower() for excluded in EXCLUDED_WEBSITE_DOMAINS):
            continue

        anchor = link.get_text(" ", strip=True).lower()
        if any(keyword in anchor for keyword in ("website", "homepage", "lab", "group", "personal")):
            return href

        if not best_candidate and href.startswith(("http://", "https://")):
            best_candidate = href

    return best_candidate


def _extract_research_text(soup: BeautifulSoup, person: dict) -> str:
    chunks: list[str] = []

    knows_about = person.get("knowsAbout")
    if isinstance(knows_about, list):
        chunks.extend(str(item) for item in knows_about)
    elif isinstance(knows_about, str):
        chunks.append(knows_about)

    description = person.get("description")
    if description:
        chunks.append(str(description))

    for heading in soup.find_all(["h2", "h3", "h4"]):
        heading_text = heading.get_text(" ", strip=True).lower()
        if any(keyword in heading_text for keyword in ("research", "interests", "areas", "expertise")):
            sibling = heading.find_next_sibling()
            if sibling:
                chunks.append(sibling.get_text(" ", strip=True))

    meta_keywords = soup.find("meta", attrs={"name": "keywords"})
    if meta_keywords and meta_keywords.get("content"):
        chunks.append(meta_keywords["content"])

    if not chunks:
        for paragraph in soup.find_all(["p", "li"]):
            text = normalize_whitespace(paragraph.get_text(" ", strip=True))
            if len(text.split()) >= 10 and any(word in text.lower() for word in ("research", "work", "interests")):
                chunks.append(text)
                break

    return compact_text_chunks(chunks)
