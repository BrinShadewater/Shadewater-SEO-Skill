#!/usr/bin/env python3
"""Network safety and shared fetch helpers for SEO scripts."""

from __future__ import annotations

import gzip
import ipaddress
import socket
import urllib.error
import urllib.request
import zlib
from email.message import Message
from urllib.parse import urlparse


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CodexSEO/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


def validate_public_url(url: str, default_scheme: str = "https") -> str:
    """Normalize a URL and reject obvious private or non-public targets."""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"{default_scheme}://{url}"
        parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme or 'missing'}")
    if not parsed.hostname:
        raise ValueError("URL is missing a hostname")

    try:
        addresses = {
            info[4][0].split("%", 1)[0]
            for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror:
        return url

    for raw_ip in addresses:
        ip = ipaddress.ip_address(raw_ip)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValueError(f"Blocked non-public target: {parsed.hostname} ({raw_ip})")

    return url


def build_fetch_result(url: str) -> dict:
    return {
        "url": url,
        "status_code": None,
        "content": None,
        "headers": {},
        "redirect_chain": [],
        "error": None,
    }


def decode_body(body: bytes, headers: Message | dict | None) -> str:
    content_encoding = ""
    if isinstance(headers, Message):
        charset = headers.get_content_charset()
        content_encoding = headers.get("Content-Encoding", "")
    else:
        content_type = ""
        if isinstance(headers, dict):
            content_type = str(headers.get("Content-Type", ""))
            content_encoding = str(headers.get("Content-Encoding", ""))
        charset = None
        if "charset=" in content_type.lower():
            charset = content_type.split("charset=", 1)[1].split(";", 1)[0].strip()

    normalized_encoding = content_encoding.lower().strip()
    try:
        if "gzip" in normalized_encoding:
            body = gzip.decompress(body)
        elif "deflate" in normalized_encoding:
            body = zlib.decompress(body)
    except OSError:
        pass

    for encoding in (charset, "utf-8", "latin-1"):
        if not encoding:
            continue
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


class TrackingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Track redirect targets and stop after a bounded number of hops."""

    def __init__(self, max_redirects: int) -> None:
        super().__init__()
        self.max_redirects = max_redirects
        self.redirect_chain: list[str] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        if len(self.redirect_chain) >= self.max_redirects:
            raise urllib.error.HTTPError(newurl, code, f"Too many redirects (max {self.max_redirects})", headers, fp)
        self.redirect_chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent urllib from automatically following redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def _fetch_with_requests(
    url: str,
    *,
    timeout: int,
    follow_redirects: bool,
    max_redirects: int,
    headers: dict[str, str],
) -> dict:
    import requests

    result = build_fetch_result(url)
    session = requests.Session()
    session.max_redirects = max_redirects
    response = session.get(
        url,
        headers=headers,
        timeout=timeout,
        allow_redirects=follow_redirects,
    )
    result["url"] = response.url
    result["status_code"] = response.status_code
    result["content"] = response.text
    result["headers"] = dict(response.headers)
    if response.history:
        result["redirect_chain"] = [item.url for item in response.history]
    return result


def _fetch_with_urllib(
    url: str,
    *,
    timeout: int,
    follow_redirects: bool,
    max_redirects: int,
    headers: dict[str, str],
) -> dict:
    result = build_fetch_result(url)
    redirect_handler = TrackingRedirectHandler(max_redirects)
    opener = urllib.request.build_opener(
        redirect_handler if follow_redirects else NoRedirectHandler(),
    )
    request = urllib.request.Request(url, headers=headers)

    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read()
            result["url"] = response.geturl()
            result["status_code"] = response.getcode()
            result["headers"] = dict(response.headers.items())
            result["content"] = decode_body(body, response.headers)
            if follow_redirects:
                result["redirect_chain"] = redirect_handler.redirect_chain
            return result
    except urllib.error.HTTPError as exc:
        if not follow_redirects and exc.code in {301, 302, 303, 307, 308}:
            body = exc.read()
            result["url"] = url
            result["status_code"] = exc.code
            result["headers"] = dict(exc.headers.items()) if exc.headers else {}
            result["content"] = decode_body(body, exc.headers)
            location = result["headers"].get("Location")
            if location:
                result["redirect_chain"] = [location]
            return result
        raise


def fetch_public_url(
    url: str,
    *,
    timeout: int = 30,
    follow_redirects: bool = True,
    max_redirects: int = 5,
    headers: dict[str, str] | None = None,
) -> dict:
    """Fetch a public URL with a shared safe fetch path and urllib fallback."""
    normalized_url = validate_public_url(url)
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    errors: list[str] = []

    try:
        return _fetch_with_requests(
            normalized_url,
            timeout=timeout,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            headers=merged_headers,
        )
    except ImportError:
        errors.append("requests not installed")
    except Exception as exc:
        errors.append(str(exc))

    try:
        return _fetch_with_urllib(
            normalized_url,
            timeout=timeout,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            headers=merged_headers,
        )
    except Exception as exc:
        result = build_fetch_result(normalized_url)
        result["error"] = " / ".join(errors + [str(exc)]) if errors else str(exc)
        return result
