"""
URL utilities for normalizing job links before storage/lookup.
"""

from urllib.parse import urlparse, parse_qs, unquote, urlunparse


def normalize_job_url(url: str) -> str:
    """
    Normalize job URLs to avoid duplicate records and lost fragments.

    - Unwrap common Google redirect links (/url?url=<target> or /url?q=<target>)
      so we store the real job board URL.
    - Strip fragments (hash) because we append #autoapply_id in the frontend.
    """
    try:
        parsed = urlparse(url)

        # Handle Google redirect wrapper
        if parsed.hostname and "google." in parsed.hostname and parsed.path == "/url":
            qs = parse_qs(parsed.query)
            target = (qs.get("url") or qs.get("q") or [None])[0]
            if target:
                return normalize_job_url(unquote(target))

        # Drop fragment to keep canonical form
        if parsed.fragment:
            parsed = parsed._replace(fragment="")
            return urlunparse(parsed)

        return url
    except Exception:
        return url


def get_stable_job_id(url: str) -> str:
    """
    Generate a stable, deterministic job ID from a URL.
    This replaces Python's unstable hash() for filesystem paths.
    """
    import zlib
    normalized = normalize_job_url(url)
    # Ensure it's a positive 32-bit integer string for path friendliness
    return str(zlib.adler32(normalized.encode('utf-8')) & 0xffffffff)
