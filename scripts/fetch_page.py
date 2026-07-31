#!/usr/bin/env python3
"""
Fetch a web page with shared network safety and fallback behavior.

Usage:
    python fetch_page.py https://example.com
    python fetch_page.py https://example.com --output page.html
"""

from __future__ import annotations

import argparse
import sys

from net_utils import fetch_public_url


def fetch_page(
    url: str,
    timeout: int = 30,
    follow_redirects: bool = True,
    max_redirects: int = 5,
) -> dict:
    """Fetch a web page and return normalized response details."""
    return fetch_public_url(
        url,
        timeout=timeout,
        follow_redirects=follow_redirects,
        max_redirects=max_redirects,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a web page for SEO analysis")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--no-redirects", action="store_true", help="Don't follow redirects")
    args = parser.parse_args()

    result = fetch_page(
        args.url,
        timeout=args.timeout,
        follow_redirects=not args.no_redirects,
    )

    if result["error"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(result["content"])
        print(f"Saved to {args.output}")
    else:
        print(result["content"])

    print(f"\nURL: {result['url']}", file=sys.stderr)
    print(f"Status: {result['status_code']}", file=sys.stderr)
    if result["redirect_chain"]:
        print(f"Redirects: {' -> '.join(result['redirect_chain'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
