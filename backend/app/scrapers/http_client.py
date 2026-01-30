"""
HTTP Client with browser TLS fingerprint impersonation.

Uses curl_cffi to bypass Cloudflare and similar TLS fingerprint checks.
Falls back to httpx if curl_cffi is not available.

This module is the single source of truth for HTTP fetching across all scrapers.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import curl_cffi (preferred for Cloudflare bypass)
try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    logger.info("curl_cffi not available, will use httpx as fallback")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Realistic browser headers shared across all scrapers
BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}


def _decode_content(content: bytes) -> str:
    """Decode bytes to string with UTF-8, falling back to Latin-1."""
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError:
        return content.decode('latin-1')


async def fetch_with_browser_fingerprint(
    url: str,
    user_agent: Optional[str] = None,
    timeout: float = 30.0,
) -> str:
    """
    Fetch a URL using browser TLS fingerprint impersonation.

    Strategy:
    1. curl_cffi with Chrome impersonation (bypasses Cloudflare TLS checks)
    2. httpx with realistic browser headers (fallback)

    Args:
        url: URL to fetch
        user_agent: Optional custom User-Agent string
        timeout: Request timeout in seconds

    Returns:
        HTML content as string

    Raises:
        Exception: If all fetch methods fail
    """
    ua = user_agent or DEFAULT_USER_AGENT
    headers = {**BROWSER_HEADERS, "User-Agent": ua}

    # Method 1: curl_cffi with Chrome TLS fingerprint
    if HAS_CURL_CFFI:
        try:
            response = curl_requests.get(
                url,
                headers=headers,
                impersonate="chrome",
                timeout=timeout,
                allow_redirects=True,
            )
            if response.status_code == 200 and len(response.content) > 1000:
                html = _decode_content(response.content)
                # Verify it's not a Cloudflare challenge page
                if 'cf-browser-verification' not in html:
                    logger.debug(f"curl_cffi OK for {url} (status={response.status_code}, len={len(html)})")
                    return html
                else:
                    logger.warning(f"curl_cffi got Cloudflare challenge for {url}")
            else:
                logger.warning(
                    f"curl_cffi response unexpected for {url}: "
                    f"status={response.status_code}, len={len(response.content)}"
                )
        except Exception as e:
            logger.warning(f"curl_cffi failed for {url}: {e}")

    # Method 2: httpx fallback
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
            html = _decode_content(response.content)
            logger.debug(f"httpx OK for {url} (status={response.status_code}, len={len(html)})")
            return html
    except Exception as e:
        logger.warning(f"httpx failed for {url}: {e}")
        raise
