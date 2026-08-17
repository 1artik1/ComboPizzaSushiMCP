# -*- coding: utf-8 -*-
"""http_client.py — requests-based HTTP client with retry and config-driven cookies/headers."""

import socket
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Suppress InsecureRequestWarning since we use verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Default browser User-Agent
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Default timeout in seconds
DEFAULT_TIMEOUT = 10

# Retry: 2 attempts with exponential backoff
_RETRY_STRATEGY = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    raise_on_status=False,
)


def get_session(chain_config=None):
    """Create a requests session with retry, config-driven headers/cookies/timeout."""
    if chain_config is None:
        chain_config = {}

    timeout = chain_config.get("http_timeout", DEFAULT_TIMEOUT)
    if isinstance(timeout, (int, float)) and timeout > 0:
        timeout = float(timeout)
    else:
        timeout = DEFAULT_TIMEOUT

    headers = dict(DEFAULT_HEADERS)
    custom_headers = chain_config.get("headers", {})
    if isinstance(custom_headers, dict):
        headers.update(custom_headers)

    session = requests.Session()
    session.headers.update(headers)

    # Apply cookies
    cookies = chain_config.get("cookies", {})
    if isinstance(cookies, dict) and cookies:
        session.cookies.update(cookies)

    # Apply retry strategy
    adapter = HTTPAdapter(
        max_retries=_RETRY_STRATEGY,
        pool_connections=1,
        pool_maxsize=1,
        pool_block=True,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session, timeout


def fetch_html(url, chain_config=None):
    """Fetch HTML content from URL. Returns text or None on failure."""
    try:
        socket.setdefaulttimeout(DEFAULT_TIMEOUT)
        session, timeout = get_session(chain_config)
        r = session.get(url, timeout=timeout, verify=False, allow_redirects=True)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    finally:
        socket.setdefaulttimeout(None)
    return None
