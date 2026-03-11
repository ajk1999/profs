from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlsplit, urlunsplit

import yaml
from bs4 import BeautifulSoup


STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}


def normalize_whitespace(text: str) -> str:
    return " ".join((text or "").split())


def strip_url_fragment(url: str) -> str:
    parts = list(urlsplit(url))
    parts[3] = parts[3]
    parts[4] = ""
    return urlunsplit(parts)


def load_yaml_file(path: str | Path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data or {}


def merge_nested_dicts(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_nested_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def find_first_email(text: str) -> str:
    match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text or "")
    return match.group(0) if match else ""


def extract_first_name(name: str) -> str:
    cleaned = normalize_whitespace(name)
    if not cleaned:
        return ""
    parts = [part for part in cleaned.split() if part.lower().rstrip(".") not in {"dr", "prof", "professor"}]
    return parts[0] if parts else ""


def parse_json_ld_people(soup: BeautifulSoup) -> list[dict[str, Any]]:
    people: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw_text = script.string or script.get_text()
        if not raw_text:
            continue
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            continue
        people.extend(_extract_people_from_json_ld(payload))
    return people


def _extract_people_from_json_ld(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        people: list[dict[str, Any]] = []
        for item in payload:
            people.extend(_extract_people_from_json_ld(item))
        return people
    if not isinstance(payload, dict):
        return []

    graph = payload.get("@graph")
    if isinstance(graph, list):
        people = []
        for item in graph:
            people.extend(_extract_people_from_json_ld(item))
        return people

    item_type = payload.get("@type", [])
    if isinstance(item_type, str):
        item_type = [item_type]
    if "Person" in item_type:
        return [payload]
    return []


def hostname(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except ValueError:
        return ""


def compact_text_chunks(chunks: list[str]) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for chunk in chunks:
        cleaned = normalize_whitespace(chunk)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return " ".join(ordered)


def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def count_words(text: str) -> int:
    if not text:
        return 0
    return len([word for word in normalize_whitespace(text).split(" ") if word])
