from __future__ import annotations

from datetime import date
from typing import Any

from profs.http_client import HttpClient
from profs.models import FacultyProfile, Publication
from profs.utils import hostname, safe_int


OPENALEX_AUTHORS_URL = "https://api.openalex.org/authors"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
CROSSREF_WORKS_URL = "https://api.crossref.org/works"


def lookup_publications(profile: FacultyProfile, http_client: HttpClient) -> FacultyProfile:
    publications, confidence, notes = _lookup_with_openalex(profile, http_client)
    source_notes = [note for note in [notes] if note]

    if not publications:
        publications, fallback_confidence, fallback_note = _lookup_with_crossref(profile, http_client)
        confidence = max(confidence, fallback_confidence)
        if fallback_note:
            source_notes.append(fallback_note)

    selected, no_recent = select_recent_publications(publications)
    if no_recent:
        source_notes.append("no publications found in current/previous year window")

    profile.publications = selected
    profile.publication_confidence = round(confidence, 2)
    profile.no_recent_publications = no_recent
    profile.notes = " | ".join([note for note in [profile.notes, *source_notes] if note])
    return profile


def select_recent_publications(publications: list[Publication]) -> tuple[list[Publication], bool]:
    today = date.today()
    allowed_years = {today.year, today.year - 1}

    sorted_publications = sorted(
        publications,
        key=lambda item: (item.date or "", item.year or 0),
        reverse=True,
    )
    recent_window = [publication for publication in sorted_publications if publication.year in allowed_years]

    if not recent_window:
        return [], True

    top_five = sorted_publications[:5]
    selected = recent_window if len(recent_window) <= len(top_five) else top_five
    return selected, False


def _lookup_with_openalex(profile: FacultyProfile, http_client: HttpClient) -> tuple[list[Publication], float, str]:
    params = {"search": profile.name, "per-page": 10}
    if http_client.settings.openalex_mailto:
        params["mailto"] = http_client.settings.openalex_mailto

    authors_payload = http_client.get_json(OPENALEX_AUTHORS_URL, params=params)
    candidates = authors_payload.get("results", [])
    best_candidate = _select_openalex_author(profile, candidates)
    if not best_candidate:
        return [], 0.0, "OpenAlex author match not found"

    author_id = best_candidate.get("id", "")
    if not author_id:
        return [], 0.0, "OpenAlex author id missing"

    works_params = {
        "filter": f"author.id:{author_id}",
        "sort": "publication_date:desc",
        "per-page": 20,
    }
    if http_client.settings.openalex_mailto:
        works_params["mailto"] = http_client.settings.openalex_mailto

    works_payload = http_client.get_json(OPENALEX_WORKS_URL, params=works_params)
    works = works_payload.get("results", [])
    publications = [_openalex_work_to_publication(work) for work in works]
    confidence = min(1.0, 0.45 + best_candidate.get("_match_score", 0.0) / 10.0)
    return publications, confidence, f"OpenAlex matched author {best_candidate.get('display_name', '')}".strip()


def _select_openalex_author(profile: FacultyProfile, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    best_candidate: dict[str, Any] = {}
    best_score = -1

    email_domain = profile.email.split("@")[-1].lower() if "@" in profile.email else ""
    website_domain = hostname(profile.personal_website)
    university_lower = profile.university.lower()
    target_name = profile.name.lower()

    for candidate in candidates:
        score = 0
        display_name = str(candidate.get("display_name", "")).lower()
        if display_name == target_name:
            score += 4
        elif target_name and target_name in display_name:
            score += 2

        institution = candidate.get("last_known_institution") or {}
        institution_name = str(institution.get("display_name", "")).lower()
        if university_lower and university_lower in institution_name:
            score += 4

        homepage = str(candidate.get("homepage_url", "")).lower()
        if email_domain and email_domain in homepage:
            score += 2
        if website_domain and website_domain in homepage:
            score += 2

        x_concepts = candidate.get("x_concepts") or []
        if x_concepts:
            score += 1

        if score > best_score:
            best_score = score
            best_candidate = dict(candidate)
            best_candidate["_match_score"] = score

    return best_candidate if best_score >= 3 else {}


def _openalex_work_to_publication(work: dict[str, Any]) -> Publication:
    venue = ""
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    if source:
        venue = source.get("display_name", "") or ""

    return Publication(
        title=work.get("display_name", "") or "",
        venue=venue,
        year=safe_int(work.get("publication_year")),
        date=work.get("publication_date", "") or "",
        url=work.get("id", "") or location.get("landing_page_url", "") or "",
        abstract=_openalex_abstract(work.get("abstract_inverted_index") or {}),
        source="OpenAlex",
    )


def _openalex_abstract(inverted_index: dict[str, list[int]]) -> str:
    if not inverted_index:
        return ""
    positioned_words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for position in positions:
            positioned_words.append((position, word))
    positioned_words.sort()
    return " ".join(word for _, word in positioned_words)


def _lookup_with_crossref(profile: FacultyProfile, http_client: HttpClient) -> tuple[list[Publication], float, str]:
    params = {
        "query.author": profile.name,
        "rows": 10,
        "sort": "published",
        "order": "desc",
    }
    if profile.university:
        params["query.affiliation"] = profile.university

    payload = http_client.get_json(CROSSREF_WORKS_URL, params=params)
    items = payload.get("message", {}).get("items", [])
    publications: list[Publication] = []

    for item in items:
        title_list = item.get("title") or []
        title = title_list[0] if title_list else ""
        venue_list = item.get("container-title") or []
        venue = venue_list[0] if venue_list else ""
        date_parts = (
            item.get("published-print", {}).get("date-parts")
            or item.get("published-online", {}).get("date-parts")
            or [[]]
        )
        year = safe_int(date_parts[0][0] if date_parts and date_parts[0] else None)
        publications.append(
            Publication(
                title=title,
                venue=venue,
                year=year,
                date=str(year) if year else "",
                url=item.get("URL", "") or "",
                abstract=item.get("abstract", "") or "",
                source="Crossref",
            )
        )

    confidence = 0.35 if publications else 0.0
    note = "Crossref fallback used" if publications else "Crossref fallback found no publications"
    return publications, confidence, note
