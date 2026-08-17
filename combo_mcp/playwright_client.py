# -*- coding: utf-8 -*-
"""playwright_client.py — ленивый импорт playwright; headless chromium."""

import os
import subprocess
import json

try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


def get_playwright():
    """Get playwright sync API, or None if not installed."""
    if not _PLAYWRIGHT_AVAILABLE:
        return None
    return sync_playwright()


def get_page(url):
    """Open a headless page and return the page object.

    Returns (page, browser) — caller must close both.
    """
    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright not installed. Run: playwright install")

    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "ms")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(url, timeout=30000)
        return page, browser


def get_cookies(url):
    """Get cookies for a URL via Playwright. Returns list of cookie dicts."""
    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright not installed")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, timeout=30000)
        cookies = page.context.cookies()
        browser.close()
        return cookies


def fetch_text(url, timeout_ms=40000, wait_ms=3000):
    """Открыть страницу в headless chromium и вернуть текст body (None при ошибке).

    Закрывает браузер; повторная попытка при ошибке загрузки.
    """
    if not _PLAYWRIGHT_AVAILABLE:
        return None
    import re
    last = None
    for attempt in range(2):
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale="ru-RU",
                )
                page = context.new_page()
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                page.wait_for_timeout(wait_ms)
                text = page.inner_text("body") or ""
                browser.close()
                return re.sub(r"\s+", " ", text)
        except Exception as exc:
            last = exc
    return None
