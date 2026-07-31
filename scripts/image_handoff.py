#!/usr/bin/env python3
"""
Build a deterministic image-remediation handoff for Webp Me Daddy.

Usage:
    python image_handoff.py page.html --url https://example.com/post --public-root C:/site/public
    python image_handoff.py parsed-page.json --public-root C:/site/public --output seo-image-handoff.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

from parse_html import parse_html


HANDOFF_VERSION = "1.0"
SUPPORTED_PREPARE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ANIMATED_EXTENSIONS = {".gif"}
UNSUPPORTED_EXTENSIONS = {".svg"}
RESPONSIVE_RECIPES = {"hero-banner", "blog-cover", "review-hero", "card-thumbnail", "profile-avatar", "logo-lockup"}
LOGO_HINTS = {"logo", "wordmark", "badge", "brandmark", "lockup"}
GRID_HINTS = {"partner", "sponsor", "badge", "logo-grid"}
AVATAR_HINTS = {"avatar", "headshot", "profile", "portrait"}
HERO_HINTS = {"hero", "banner", "cover", "masthead", "lead"}
REVIEW_HINTS = {"review", "notes"}
POSTER_HINTS = {"poster"}
STORY_HINTS = {"story", "reel"}
REDUNDANT_ALT_PREFIX_PATTERN = re.compile(
    r"^\s*(image|photo|picture|graphic|illustration)\s+of\b",
    re.IGNORECASE,
)


def collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def slugify(text: str) -> str:
    cleaned = collapse_spaces(text).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return re.sub(r"-{2,}", "-", cleaned).strip("-") or "image"


def humanize_slug(text: str) -> str:
    slug = slugify(text)
    return " ".join(part.capitalize() for part in slug.split("-"))


def parse_dimension(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", str(value))
    if not match:
        return None
    return int(match.group(0))


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = collapse_spaces(str(value))
    return text or None


def looks_filename_like(text: str | None, src: str | None) -> bool:
    if not text or not src:
        return False
    stem = Path(urlparse(src).path or src).stem
    return slugify(text) == slugify(stem)


def load_analysis(input_path: Path, url: str | None) -> dict[str, Any]:
    if input_path.suffix.lower() == ".json":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Parsed JSON input must be a JSON object.")
        return payload
    html = input_path.read_text(encoding="utf-8")
    return parse_html(html, url)


def derive_page_slug(url: str | None, page_title: str | None, input_path: Path) -> str:
    if url:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path:
            return slugify(path.split("/")[-1])
        if parsed.netloc:
            return slugify(parsed.netloc)
    if page_title:
        return slugify(page_title)
    return slugify(input_path.stem)


def derive_page_context(page_title: str | None, page_slug: str, override: str | None) -> str:
    if override:
        return collapse_spaces(override)
    if page_title:
        return collapse_spaces(page_title)
    return humanize_slug(page_slug)


def is_truthy_aria_hidden(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes"}


def infer_recipe(image: dict[str, Any], index: int, page_context: str) -> str:
    src = str(image.get("src") or "")
    alt = str(image.get("alt") or "")
    combined = " ".join([src, alt, page_context]).lower()
    width = parse_dimension(image.get("width"))
    height = parse_dimension(image.get("height"))
    ratio = (width / height) if width and height and height else None
    fetchpriority = str(image.get("fetchpriority") or "").lower()
    loading = str(image.get("loading") or "").lower()

    if any(token in combined for token in LOGO_HINTS):
        if any(token in combined for token in GRID_HINTS):
            return "logo-grid"
        return "logo-lockup"

    if any(token in combined for token in AVATAR_HINTS):
        return "profile-avatar"

    if any(token in combined for token in STORY_HINTS):
        return "story-cover"

    if any(token in combined for token in POSTER_HINTS):
        return "poster"

    hero_like = (
        index == 0
        or any(token in combined for token in HERO_HINTS)
        or fetchpriority == "high"
        or loading == "eager"
    )
    if hero_like:
        if any(token in combined for token in REVIEW_HINTS | POSTER_HINTS):
            return "review-hero"
        return "hero-banner"

    if ratio is not None:
        if ratio <= 0.62:
            return "story-cover"
        if ratio <= 0.75:
            return "poster"
        if ratio <= 0.9:
            return "card-thumbnail"
        if 0.9 < ratio < 1.1:
            return "profile-avatar"

    return "blog-cover"


def infer_accessibility_mode(image: dict[str, Any], src: str, recipe: str) -> str:
    raw_alt = image.get("alt")
    role = str(image.get("role") or "").lower()
    if raw_alt is not None and str(raw_alt).strip() == "" and (role == "presentation" or is_truthy_aria_hidden(image.get("aria_hidden"))):
        return "decorative"

    combined = " ".join([src, str(image.get("alt") or "")]).lower()
    if recipe == "logo-grid":
        return "decorative" if raw_alt is None or str(raw_alt).strip() == "" else "logo"
    if recipe == "logo-lockup" or any(token in combined for token in LOGO_HINTS):
        return "logo"
    return "descriptive"


def infer_subject(src: str, alt: str | None, accessibility_mode: str) -> str:
    if alt and not looks_filename_like(alt, src):
        return collapse_spaces(REDUNDANT_ALT_PREFIX_PATTERN.sub("", alt))
    stem = Path(urlparse(src).path or src).stem
    base = humanize_slug(stem)
    if accessibility_mode == "logo" and "logo" not in base.lower():
        return f"{base} Logo"
    return base


def infer_purpose(recipe: str) -> str:
    mapping = {
        "hero-banner": "hero image",
        "review-hero": "article or review hero image",
        "blog-cover": "blog cover image",
        "profile-avatar": "profile image",
        "card-thumbnail": "card thumbnail",
        "poster": "poster image",
        "story-cover": "story cover",
        "logo-lockup": "brand logo",
        "logo-grid": "partner logo tile",
    }
    return mapping.get(recipe, "page image")


def build_usage_alt(subject: str, page_context: str, accessibility_mode: str) -> str:
    if accessibility_mode == "decorative":
        return ""
    if accessibility_mode == "logo":
        return subject if "logo" in subject.lower() else f"{subject} logo"
    if page_context.lower() in subject.lower():
        return subject
    return collapse_spaces(f"{subject} for {page_context}")


def resolve_local_source(src: str, resolved_url: str | None, public_root: Path | None) -> tuple[str | None, str | None]:
    if public_root is None:
        return None, None

    candidate_paths: list[str] = []
    for raw_value in (src, resolved_url):
        if not raw_value:
            continue
        parsed = urlparse(raw_value)
        if parsed.path:
            candidate_paths.append(parsed.path)
        elif raw_value:
            candidate_paths.append(raw_value)

    seen: set[str] = set()
    root = public_root.resolve()
    for raw_path in candidate_paths:
        decoded = unquote(raw_path).strip()
        if not decoded or decoded in seen:
            continue
        seen.add(decoded)
        relative = decoded.lstrip("/").replace("\\", "/")
        if not relative:
            continue
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.exists():
            return str(candidate), relative
    return None, None


def infer_priority(recipe: str, reasons: list[str], index: int) -> str:
    if recipe in {"hero-banner", "review-hero"} or index == 0:
        return "high"
    if len(reasons) >= 3:
        return "medium"
    return "low"


def build_reasons(image: dict[str, Any], recipe: str, accessibility_mode: str, src: str, index: int) -> list[str]:
    reasons: list[str] = []
    alt = normalize_text(image.get("alt"))
    extension = Path(urlparse(src).path or src).suffix.lower()
    hero_like = recipe in {"hero-banner", "review-hero"}
    loading = str(image.get("loading") or "").lower()
    fetchpriority = str(image.get("fetchpriority") or "").lower()

    if accessibility_mode != "decorative" and not alt:
        reasons.append("missing_alt")
    elif looks_filename_like(alt, src):
        reasons.append("filename_like_alt")

    if extension in {".jpg", ".jpeg", ".png"}:
        reasons.append("next_gen_format_recommended")
    if not image.get("width") or not image.get("height"):
        reasons.append("missing_dimensions")
    if hero_like and loading == "lazy":
        reasons.append("hero_image_lazy_loaded")
    if hero_like and fetchpriority != "high":
        reasons.append("missing_fetchpriority")
    if not hero_like and not loading:
        reasons.append("missing_lazy_loading")
    if recipe in RESPONSIVE_RECIPES and not image.get("srcset"):
        reasons.append("missing_srcset")
    if image.get("srcset") and not image.get("sizes"):
        reasons.append("missing_sizes")
    if not image.get("decoding") and not hero_like:
        reasons.append("missing_decoding")
    if index == 0 and recipe in {"hero-banner", "review-hero"}:
        reasons.append("lcp_candidate")

    return sorted(set(reasons))


def build_item(
    image: dict[str, Any],
    index: int,
    page_url: str | None,
    page_context: str,
    page_slug: str,
    public_root: Path | None,
) -> dict[str, Any]:
    src = str(image.get("src") or "")
    resolved_url = urljoin(page_url, src) if page_url and src else (src or None)
    recipe = infer_recipe(image, index, page_context)
    accessibility_mode = infer_accessibility_mode(image, src, recipe)
    alt = normalize_text(image.get("alt"))
    subject = infer_subject(src, alt, accessibility_mode)
    usage_key = f"{page_slug}.{slugify(Path(urlparse(src).path or src).stem or f'image-{index + 1}')}"
    reasons = build_reasons(image, recipe, accessibility_mode, src, index)
    priority = infer_priority(recipe, reasons, index)
    local_source_path, relative_path = resolve_local_source(src, resolved_url, public_root)
    extension = Path(urlparse(src).path or src).suffix.lower()

    status = "ready"
    notes: list[str] = []
    if local_source_path is None:
        status = "manual"
        notes.append("Local public asset could not be resolved from the image src.")
    elif extension in ANIMATED_EXTENSIONS:
        status = "manual"
        notes.append("Animated assets should go through the animate workflow, not the still-image pipeline.")
    elif extension in UNSUPPORTED_EXTENSIONS:
        status = "manual"
        notes.append("SVG assets should stay vector or be handled manually.")
    elif extension not in SUPPORTED_PREPARE_EXTENSIONS:
        status = "manual"
        notes.append(f"Unsupported source format for prepare workflow: {extension or 'unknown'}")

    markup_loading = "eager" if recipe in {"hero-banner", "review-hero"} else "lazy"
    markup_fetch_priority = "high" if recipe in {"hero-banner", "review-hero"} else None

    return {
        "id": usage_key,
        "status": status,
        "priority": priority,
        "recipe": recipe,
        "reasons": reasons,
        "source": {
            "src": src or None,
            "url": resolved_url,
            "path": local_source_path,
            "public_relative_path": relative_path,
            "resolved": local_source_path is not None,
            "format": extension.lstrip(".") or None,
        },
        "metadata": {
            "accessibility_mode": accessibility_mode,
            "subject": subject,
            "context": page_context,
            "purpose": infer_purpose(recipe),
            "visible_text": None,
            "usage_key": usage_key,
            "usage_alt": build_usage_alt(subject, page_context, accessibility_mode),
        },
        "markup": {
            "loading": markup_loading,
            "fetch_priority": markup_fetch_priority,
            "needs_dimensions": not bool(image.get("width") and image.get("height")),
            "needs_responsive_variants": recipe in RESPONSIVE_RECIPES,
            "has_srcset": bool(image.get("srcset")),
            "has_sizes": bool(image.get("sizes")),
            "sizes": "100vw" if recipe in {"hero-banner", "review-hero", "blog-cover"} else None,
        },
        "page_asset_index": index + 1,
        "notes": notes,
    }


def build_handoff(
    analysis: dict[str, Any],
    input_path: Path,
    page_url: str | None,
    public_root: Path | None,
    page_context_override: str | None,
) -> dict[str, Any]:
    page_title = normalize_text(analysis.get("title"))
    images = analysis.get("images", [])
    if not isinstance(images, list):
        raise ValueError("Input analysis must contain an images list.")

    page_slug = derive_page_slug(page_url, page_title, input_path)
    page_context = derive_page_context(page_title, page_slug, page_context_override)
    structured_images = [image for image in images if isinstance(image, dict)]
    items = [
        build_item(image, index, page_url, page_context, page_slug, public_root)
        for index, image in enumerate(structured_images)
    ]

    summary = {
        "image_count": len(items),
        "ready_count": sum(1 for item in items if item["status"] == "ready"),
        "manual_count": sum(1 for item in items if item["status"] == "manual"),
        "high_priority_count": sum(1 for item in items if item["priority"] == "high"),
    }

    return {
        "version": HANDOFF_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "producer": {
            "skill": "seo",
            "script": "image_handoff.py",
        },
        "page": {
            "url": page_url,
            "title": page_title,
            "context": page_context,
            "slug": page_slug,
        },
        "defaults": {
            "public_root": str(public_root.resolve()) if public_root else None,
            "write_sidecar": True,
            "overwrite_recommended": True,
        },
        "summary": summary,
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an SEO image handoff for Webp Me Daddy.")
    parser.add_argument("input", type=Path, help="HTML file or parse_html JSON.")
    parser.add_argument("--url", "-u", help="Page URL used to resolve relative src values.")
    parser.add_argument("--public-root", type=Path, help="Local public folder used to resolve image src values.")
    parser.add_argument("--page-context", help="Override the page context used in metadata suggestions.")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("seo-image-handoff.json"),
        help="Output JSON file path. Defaults to seo-image-handoff.json in the working directory.",
    )
    parser.add_argument("--stdout", action="store_true", help="Also print the JSON handoff to stdout.")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input not found: {args.input}", file=sys.stderr)
        return 1
    if args.public_root and not args.public_root.exists():
        print(f"Error: Public root not found: {args.public_root}", file=sys.stderr)
        return 1

    try:
        analysis = load_analysis(args.input.resolve(), args.url)
        handoff = build_handoff(
            analysis=analysis,
            input_path=args.input.resolve(),
            page_url=args.url,
            public_root=args.public_root.resolve() if args.public_root else None,
            page_context_override=args.page_context,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(handoff, indent=2)
    args.output.write_text(serialized, encoding="utf-8")

    summary = handoff["summary"]
    print(f"Handoff: {args.output.resolve()}")
    print(f"Images: {summary['image_count']}")
    print(f"Ready: {summary['ready_count']}")
    print(f"Manual: {summary['manual_count']}")
    if args.stdout:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
