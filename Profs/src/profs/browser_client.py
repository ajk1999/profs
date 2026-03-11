from __future__ import annotations


class BrowserClient:
    """Playwright wrapper used only as a fallback for JavaScript-heavy pages."""

    def __init__(self, enabled: bool = True, headless: bool = True):
        self.enabled = enabled
        self.headless = headless

    def fetch_html(self, url: str) -> str:
        if not self.enabled:
            return ""

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return ""

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.headless)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                return page.content()
            except Exception:
                return ""
            finally:
                browser.close()
