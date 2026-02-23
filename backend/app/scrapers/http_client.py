"""
HTTP Client with browser TLS fingerprint impersonation.

Uses curl_cffi to bypass Cloudflare and similar TLS fingerprint checks.
Falls back to httpx for non-CF sites.

This module is the single source of truth for HTTP fetching across all scrapers.
"""
import asyncio
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
    "Chrome/131.0.0.0 Safari/537.36"
)

# Realistic browser headers shared across all scrapers
BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
    "Priority": "u=0, i",
}

# Markers that indicate a Cloudflare challenge/block page
CF_BLOCK_MARKERS = [
    'cf-browser-verification',
    'Just a moment',
    'Checking your browser',
    'Attention Required',
    'Access denied',
]


def _decode_content(content: bytes) -> str:
    """Decode bytes to string with UTF-8, falling back to Latin-1."""
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError:
        return content.decode('latin-1')


def _is_cf_blocked(html: str) -> bool:
    """Check if HTML content is a Cloudflare challenge/block page."""
    return any(marker in html for marker in CF_BLOCK_MARKERS)


async def fetch_with_browser_fingerprint(
    url: str,
    user_agent: Optional[str] = None,
    timeout: float = 30.0,
    max_retries: int = 2,
) -> str:
    """
    Fetch a URL using browser TLS fingerprint impersonation.

    Strategy:
    1. curl_cffi with Chrome impersonation (bypasses Cloudflare TLS checks)
    2. httpx with realistic browser headers (fallback for non-CF sites)

    Retries transient errors (connection, timeout) up to max_retries times
    with exponential backoff.

    Args:
        url: URL to fetch
        user_agent: Optional custom User-Agent string
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for transient errors

    Returns:
        HTML content as string

    Raises:
        Exception: If all fetch methods fail
    """
    ua = user_agent or DEFAULT_USER_AGENT
    headers = {**BROWSER_HEADERS, "User-Agent": ua}
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            return await _fetch_once(url, headers, timeout)
        except Exception as e:
            last_exception = e
            # Only retry on transient errors (connection, timeout)
            err_str = str(e).lower()
            is_transient = any(kw in err_str for kw in [
                'timeout', 'timed out', 'connection', 'connect',
                'reset', 'refused', 'network', 'temporary',
            ])
            if not is_transient or attempt == max_retries:
                raise
            backoff = 2 ** (attempt - 1)  # 1s, 2s
            logger.info(f"Retrying {url} in {backoff}s (attempt {attempt}/{max_retries}): {e}")
            await asyncio.sleep(backoff)

    # Should not reach here, but just in case
    raise last_exception  # type: ignore[misc]


async def _fetch_once(
    url: str,
    headers: dict,
    timeout: float,
) -> str:
    """Single fetch attempt with curl_cffi -> httpx fallback chain."""
    # Method 1: curl_cffi with Chrome TLS fingerprint
    # Try multiple impersonation profiles — different Cloudflare configs block different fingerprints
    if HAS_CURL_CFFI:
        impersonate_profiles = ["chrome", "chrome124", "chrome110", "edge101"]
        for profile in impersonate_profiles:
            try:
                # Use a Session to persist cookies across redirects (helps with CF cookie challenges)
                session = curl_requests.Session(impersonate=profile)
                response = session.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True,
                )
                if response.status_code == 200 and len(response.content) > 1000:
                    html = _decode_content(response.content)
                    if not _is_cf_blocked(html):
                        logger.debug(f"curl_cffi OK for {url} (profile={profile}, len={len(html)})")
                        return html
                    else:
                        logger.warning(f"curl_cffi got Cloudflare challenge for {url} (profile={profile})")
                else:
                    logger.warning(
                        f"curl_cffi response for {url}: "
                        f"status={response.status_code}, len={len(response.content)} (profile={profile})"
                    )
            except Exception as e:
                logger.warning(f"curl_cffi failed for {url} (profile={profile}): {e}")
            finally:
                try:
                    session.close()
                except Exception:
                    pass

    # Method 2: httpx fallback (works for non-CF sites)
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
