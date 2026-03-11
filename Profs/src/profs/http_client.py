from __future__ import annotations

import time
from typing import Any

import requests

from profs.settings import Settings


class HttpClient:
    """Simple retrying HTTP client for static HTML and JSON requests."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    def get(self, url: str, params: dict[str, Any] | None = None) -> requests.Response | None:
        for attempt in range(self.settings.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.settings.timeout)
                if 500 <= response.status_code < 600:
                    raise requests.HTTPError(f"server error {response.status_code}")
                response.raise_for_status()
                time.sleep(self.settings.request_delay)
                return response
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError):
                if attempt == self.settings.max_retries - 1:
                    return None
                time.sleep(self.settings.request_delay * (2 ** attempt))
            except requests.RequestException:
                return None
        return None

    def get_html(self, url: str, params: dict[str, Any] | None = None) -> str:
        response = self.get(url, params=params)
        return response.text if response else ""

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.get(url, params=params)
        if not response:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}
