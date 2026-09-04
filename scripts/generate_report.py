#!/usr/bin/env python3
"""
Generate an interactive HTML SEO report.

Runs all analysis scripts and aggregates results into a single,
self-contained interactive HTML file with a premium dashboard UI.

Usage:
    python generate_report.py https://example.com
    python generate_report.py https://example.com --output my-report.html
    python generate_report.py https://example.com --theme classic
"""

import argparse
import base64
import html as html_lib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from image_handoff import build_handoff
from finding_verifier import verify_findings
from net_utils import fetch_public_url

import console_safe  # noqa: F401  (side effect: UTF-8 stdout/stderr)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Candidate locations for the webp-me-daddy handoff script, in preference order.
# Resolved at runtime rather than hard-coded: the previous absolute path baked in the
# wrong user profile and a skill folder name that has since changed, so every generated
# ACTION-PLAN shipped a command that could not run.
WEBP_ME_DADDY_CANDIDATES = (
    Path.home() / ".claude" / "skills" / "webp-me-daddy" / "scripts" / "webp_me_daddy.py",
    Path.home() / ".codex" / "skills" / "webp-me-daddy" / "scripts" / "webp_me_daddy.py",
    Path(SCRIPT_DIR).parent.parent / "webp-me-daddy" / "scripts" / "webp_me_daddy.py",
)


def resolve_webp_me_daddy() -> str:
    """Return a usable path to webp_me_daddy.py, or a clearly-marked placeholder."""
    for candidate in WEBP_ME_DADDY_CANDIDATES:
        if candidate.is_file():
            return str(candidate)
    return "<path-to>/webp-me-daddy/scripts/webp_me_daddy.py"


PAGESPEED_API_KEY_ENV_VARS = (
    "PAGESPEED_API_KEY",
    "GOOGLE_PAGESPEED_API_KEY",
    "GOOGLE_API_KEY",
)

REPORT_THEMES = {
    "classic": {
        "title_prefix": "SEO Report",
        "display_name": "SEO Analysis Report",
        "title_lines": ["SEO Analysis Report"],
        "eyebrow": "Interactive audit",
        "tagline": "Technical SEO, content quality, and AI search readiness in one place.",
        "font_links": (
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">'
        ),
        "font_ui": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "font_display": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "font_body": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "bg": "#0f172a",
        "surface": "rgba(30, 41, 59, 0.96)",
        "surface_elevated": "rgba(51, 65, 85, 0.92)",
        "card": "rgba(30, 41, 59, 0.92)",
        "card_border": "#334155",
        "text": "#f1f5f9",
        "text_muted": "#94a3b8",
        "accent": "#6366f1",
        "accent_2": "#818cf8",
        "accent_glow": "rgba(99, 102, 241, 0.3)",
        "positive": "#22c55e",
        "warning": "#eab308",
        "danger": "#ef4444",
        "orange": "#f97316",
        "info": "#60a5fa",
        "hero_gradient": "linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%)",
        "hero_domain": "#a5b4fc",
        "hero_timestamp": "#818cf8",
        "light_bg": "#f8fafc",
        "light_surface": "#ffffff",
        "light_surface_elevated": "#eef2ff",
        "light_card": "#ffffff",
        "light_card_border": "#e2e8f0",
        "light_text": "#1e293b",
        "light_text_muted": "#64748b",
        "light_accent_glow": "rgba(99, 102, 241, 0.15)",
        "brand_logo_alt": "SEO Skill report logo",
        "footer_theme_name": "Classic Theme",
    },
    "shadewater": {
        "title_prefix": "Shadewater SEO Report",
        "display_name": "Shadewater SEO Report",
        "title_lines": ["Shadewater", "SEO Report"],
        "eyebrow": "Shadewater Theme V1",
        "tagline": "",
        "font_links": (
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Crimson+Pro:ital,wght@0,400;0,500;0,600;1,400&family=Cormorant+Garamond:wght@500;600;700&display=swap" rel="stylesheet">'
        ),
        "font_ui": "'Space Grotesk', sans-serif",
        "font_display": "'Cormorant Garamond', serif",
        "font_body": "'Crimson Pro', serif",
        "bg": "#04121F",
        "surface": "rgba(18, 42, 51, 0.92)",
        "surface_elevated": "rgba(37, 62, 68, 0.9)",
        "card": "rgba(17, 29, 35, 0.88)",
        "card_border": "rgba(255, 255, 255, 0.1)",
        "text": "#f5f2ea",
        "text_muted": "#b8b2a6",
        "accent": "#b08b5b",
        "accent_2": "#4f8d98",
        "accent_glow": "rgba(176, 139, 91, 0.22)",
        "positive": "#6aa37d",
        "warning": "#d2a14a",
        "danger": "#d76d60",
        "orange": "#c78452",
        "info": "#79a8b3",
        "hero_gradient": "linear-gradient(135deg, rgba(18,42,51,0.98), rgba(37,62,68,0.94), rgba(58,48,39,0.9))",
        "hero_domain": "#dfc9a3",
        "hero_timestamp": "#96b2b7",
        "light_bg": "#f5eee2",
        "light_surface": "rgba(255, 251, 245, 0.96)",
        "light_surface_elevated": "rgba(234, 225, 209, 0.9)",
        "light_card": "rgba(255, 255, 255, 0.9)",
        "light_card_border": "rgba(73, 92, 97, 0.18)",
        "light_text": "#19303a",
        "light_text_muted": "#5b6b70",
        "light_accent_glow": "rgba(79, 141, 152, 0.16)",
        "brand_logo_alt": "Shadewater Labs logo",
        "footer_theme_name": "Shadewater Theme V1",
    },
}


def resolve_report_theme(theme_name: str) -> dict:
    """Return the configured report theme or fall back to the classic palette."""
    return REPORT_THEMES.get(theme_name, REPORT_THEMES["classic"])


def encode_image_data_uri(path: Path) -> str | None:
    """Inline a local image so generated reports can render without deployment context."""
    mime_by_suffix = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    mime = mime_by_suffix.get(path.suffix.lower())
    if mime is None or not path.exists() or not path.is_file():
        return None
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def resolve_brand_logo_uri(theme_name: str, explicit_brand_logo: str | None = None) -> str | None:
    """Find and inline a theme brand logo when one is available locally."""
    candidates: list[Path] = []
    if explicit_brand_logo:
        candidates.append(Path(explicit_brand_logo))
    if theme_name == "shadewater":
        cwd = Path.cwd()
        candidates.extend(
            [
                cwd / "public" / "shadewater-labs-logo-mark.webp",
                cwd / "public" / "shadewater-labs-logo-mark-transparent.png",
                cwd / "public" / "Shadewater logo without text.png",
            ]
        )
    for candidate in candidates:
        uri = encode_image_data_uri(candidate)
        if uri:
            return uri
    return None


def resolve_public_root(explicit_public_root: str | None) -> Path | None:
    """Resolve a local public root for image remediation handoffs."""
    candidates: list[Path] = []
    if explicit_public_root:
        candidates.append(Path(explicit_public_root))
    cwd = Path.cwd()
    candidates.append(cwd / "public")

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return None


def pagespeed_domain_env_names(url: str | None) -> list[str]:
    """Build secret-safe PageSpeed env var names for a specific audited domain."""
    if not url:
        return []
    domain = urlparse(str(url)).netloc.lower().split("@")[-1].split(":")[0]
    if not domain:
        return []
    normalized = re.sub(r"[^A-Z0-9]+", "_", domain.upper()).strip("_")
    if not normalized:
        return []
    return [
        f"PAGESPEED_API_KEY_{normalized}",
        f"GOOGLE_PAGESPEED_API_KEY_{normalized}",
    ]


def resolve_pagespeed_api_key(url: str | None = None) -> str | None:
    """Return the first configured PageSpeed API key from domain-specific then global env vars."""
    for env_name in pagespeed_domain_env_names(url):
        value = os.getenv(env_name)
        if value:
            return value
    for env_name in PAGESPEED_API_KEY_ENV_VARS:
        value = os.getenv(env_name)
        if value:
            return value
    return None


def run_script(script_name: str, args: list, timeout: int = 120) -> dict:
    """Run an analysis script and capture JSON output."""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.exists(script_path):
        return {"error": f"Script {script_name} not found"}

    cmd = [sys.executable, script_path] + args + ["--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        err_msg = result.stderr.strip() or f"Exit code {result.returncode}"
        return {"error": f"[{script_name}] {err_msg}"}
    except subprocess.TimeoutExpired:
        return {"error": f"Script timed out after {timeout}s"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON output from script"}
    except Exception as e:
        return {"error": str(e)}


def fetch_page(url: str) -> str:
    """Fetch page HTML to a temp file, return path."""
    result = fetch_public_url(url, timeout=15)
    if result.get("error") or not result.get("content"):
        return ""
    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    tmp.write(result["content"])
    tmp.close()
    return tmp.name


def detect_environment(html_text: str, url: str) -> dict:
    """Infer site environment/CMS/framework from source signals."""
    lower = (html_text or "").lower()
    domain = urlparse(url).netloc.lower()
    scores = {}
    reasons = {}

    def hit(name: str, points: int, reason: str):
        scores[name] = scores.get(name, 0) + points
        reasons.setdefault(name, []).append(reason)

    # Managed CMS signals
    if any(s in lower for s in ("bloggerusercontent.com", "www.blogger.com", "data:blog.", "b:skin")):
        hit("Blogger", 6, "Blogger template/assets detected")
    if domain.endswith("blogspot.com"):
        hit("Blogger", 4, "Blogspot domain detected")

    if any(s in lower for s in ("wp-content/", "wp-includes/", "wp-json")):
        hit("WordPress", 6, "WordPress core paths detected")
    if re.search(r'generator[^>]+wordpress', lower):
        hit("WordPress", 3, "WordPress generator meta detected")

    if any(s in lower for s in ("cdn.shopify.com", "shopify.theme", "shopify-section")):
        hit("Shopify", 6, "Shopify assets/theme markers detected")

    if any(s in lower for s in ("wixstatic.com", "wix.com", "wixsite")):
        hit("Wix", 6, "Wix assets detected")

    if any(s in lower for s in ("webflow", "w-webflow")):
        hit("Webflow", 5, "Webflow markers detected")

    if any(s in lower for s in ("squarespace.com", "static1.squarespace")):
        hit("Squarespace", 6, "Squarespace assets detected")

    if re.search(r'generator[^>]+ghost', lower) or "ghost/" in lower:
        hit("Ghost", 5, "Ghost generator/assets detected")

    # Framework signals
    if any(s in lower for s in ("/_next/", "__next_data__")):
        hit("Next.js", 6, "Next.js runtime/build markers detected")
    if any(s in lower for s in ("/_nuxt/", "__nuxt")):
        hit("Nuxt", 6, "Nuxt runtime/build markers detected")

    if not scores:
        return {
            "primary": "Static / Custom",
            "runtime": "Static HTML or unknown framework",
            "confidence": "low",
            "signals": ["No strong CMS/framework markers were found in HTML source."],
            "alternatives": [],
        }

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary, top_score = ranked[0]
    confidence = "high" if top_score >= 8 else "medium" if top_score >= 5 else "low"
    runtime_map = {
        "Blogger": "Managed CMS",
        "WordPress": "Managed CMS",
        "Shopify": "Managed CMS / Commerce",
        "Wix": "Managed CMS",
        "Webflow": "Managed CMS",
        "Squarespace": "Managed CMS",
        "Ghost": "Managed CMS",
        "Next.js": "JavaScript Framework",
        "Nuxt": "JavaScript Framework",
    }
    return {
        "primary": primary,
        "runtime": runtime_map.get(primary, "Unknown"),
        "confidence": confidence,
        "signals": reasons.get(primary, [])[:5],
        "alternatives": [name for name, _ in ranked[1:3]],
    }


def _platform_hint(primary: str, area: str) -> str:
    """Provide platform-specific implementation guidance."""
    blogger = {
        "metadata": "In Blogger, update Theme -> Edit HTML and add tags in the <head> section (title template, meta description, OG/Twitter tags).",
        "heading": "In Blogger templates, keep exactly one content H1 per page (post title on posts, site headline on homepage).",
        "headers": "Blogger cannot set most response headers directly. Add Cloudflare in front and configure Response Header Transform Rules.",
        "llms": "Blogger cannot natively serve arbitrary root files. Serve /llms.txt via Cloudflare Workers/Pages or reverse-proxy route.",
        "links": "Fix broken internal links in post content and navigation widgets; update outdated post URLs and labels.",
        "performance": "Optimize Blogger theme widgets/scripts, compress hero/media assets, and defer non-critical third-party scripts.",
    }
    wordpress = {
        "metadata": "Use your SEO plugin (Yoast/RankMath/AIOSEO) or theme templates to set title/meta and OG/Twitter tags.",
        "heading": "Ensure one H1 in theme templates and avoid duplicate H1 in builders/widgets.",
        "headers": "Set headers via server config (Nginx/Apache) or CDN edge rules.",
        "llms": "Create /llms.txt at web root or route it through your web server.",
        "links": "Fix links in menus, content blocks, and internal link plugin data.",
        "performance": "Use caching, image optimization, script deferral, and CWV-focused plugin settings.",
    }
    nextjs = {
        "metadata": "Use the Next.js Metadata API (`app/`) or `next/head` (`pages/`) for title/meta/OG/Twitter tags.",
        "heading": "Set a single semantic H1 in each route component.",
        "headers": "Set security headers in `next.config.js` `headers()` or at your edge/CDN.",
        "llms": "Serve `/llms.txt` from `/public/llms.txt`.",
        "links": "Fix links in route components and content source files; validate with link checks in CI.",
        "performance": "Use `next/image`, dynamic imports, script strategy controls, and reduce main-thread JS.",
    }
    fallback = {
        "metadata": "Update page templates to set complete title/meta/OG/Twitter tags.",
        "heading": "Ensure each page has exactly one descriptive H1 aligned to intent.",
        "headers": "Set missing security headers at web server or CDN layer.",
        "llms": "Add `/llms.txt` at site root with concise site description and key URLs.",
        "links": "Repair or remove broken internal links and refresh outdated navigation targets.",
        "performance": "Compress critical assets, reduce render-blocking scripts, and optimize CWV bottlenecks.",
    }

    platform_map = {
        "Blogger": blogger,
        "WordPress": wordpress,
        "Shopify": fallback,
        "Wix": fallback,
        "Webflow": fallback,
        "Squarespace": fallback,
        "Ghost": fallback,
        "Next.js": nextjs,
        "Nuxt": nextjs,
    }
    return platform_map.get(primary, fallback).get(area, fallback.get(area, ""))


def build_environment_fixes(data: dict) -> list:
    """Build actionable issue fixes tailored to detected environment."""
    env = data.get("environment", {})
    platform = env.get("primary", "Unknown")
    fixes = []

    def add(severity: str, title: str, reason: str, fix: str):
        fixes.append({
            "severity": severity,
            "title": title,
            "reason": reason,
            "fix": fix,
        })

    op = data["sections"].get("onpage", {})
    sec = data["sections"].get("security", {})
    soc = data["sections"].get("social", {})
    llm = data["sections"].get("llms_txt", {})
    bl = data["sections"].get("broken_links", {})
    rd = data["sections"].get("readability", {})
    psi = data["sections"].get("pagespeed", {})

    title = (op.get("title") or "").strip()
    meta = (op.get("meta_description") or "").strip()
    h1s = op.get("h1", []) if isinstance(op.get("h1"), list) else []

    if not h1s:
        add(
            "critical",
            "Missing H1 on page",
            "No primary content heading was detected, which weakens topical clarity.",
            _platform_hint(platform, "heading"),
        )

    if not meta or len(meta) < 110 or len(meta) > 170:
        add(
            "warning",
            "Meta description is missing or out of range",
            "This can reduce SERP CTR and snippet quality.",
            _platform_hint(platform, "metadata"),
        )

    if not title or len(title) < 30 or len(title) > 65:
        add(
            "warning",
            "Title tag needs optimization",
            "Title length/content is likely suboptimal for rankings and click-through.",
            _platform_hint(platform, "metadata"),
        )

    missing_headers = sec.get("headers_missing", {})
    if missing_headers:
        add(
            "critical" if len(missing_headers) >= 4 else "warning",
            f"{len(missing_headers)} security headers missing",
            "Missing headers reduce trust and can expose the site to browser/security risks.",
            _platform_hint(platform, "headers"),
        )

    if not llm.get("exists"):
        add(
            "warning",
            "No llms.txt found",
            "AI crawlers and assistants have no curated machine-readable guidance for key pages.",
            _platform_hint(platform, "llms"),
        )

    broken_count = bl.get("summary", {}).get("broken", 0)
    if broken_count > 0:
        add(
            "critical" if broken_count >= 5 else "warning",
            f"{broken_count} broken links detected",
            "Broken internal links hurt crawl flow and user trust.",
            _platform_hint(platform, "links"),
        )

    og_missing = soc.get("og_missing", [])
    tw_missing = soc.get("twitter_missing", [])
    if og_missing or tw_missing:
        add(
            "warning",
            "Social meta tags are incomplete",
            "Missing OG/Twitter tags weakens social previews and share quality.",
            _platform_hint(platform, "metadata"),
        )

    if psi.get("error"):
        add(
            "info",
            "Performance measurement incomplete",
            "PageSpeed API returned an error, so CWV recommendations are less reliable.",
            "Rerun `pagespeed.py` with `--api-key` and then prioritize LCP/INP/CLS fixes from that output.",
        )

    if rd.get("flesch_reading_ease", 100) < 40 or rd.get("avg_sentence_length", 0) > 25:
        add(
            "warning",
            "Content readability is difficult",
            "Long, complex text can reduce engagement and comprehension.",
            "Rewrite key sections with shorter sentences (15-20 words), shorter paragraphs (2-4 sentences), and clearer subheadings.",
        )

    if not fixes:
        add(
            "pass",
            "No major implementation blockers detected",
            "Core checks look healthy for current scope.",
            "Continue monitoring with regular crawls and keep metadata/security/performance baselines in CI.",
        )

    return fixes


def render_environment_fixes(fixes: list) -> str:
    """Render environment-specific fixes for HTML output."""
    if not fixes:
        return '<p style="color:var(--green)">✅ No environment-specific fixes needed.</p>'

    severity_order = {"critical": 0, "warning": 1, "info": 2, "pass": 3}
    html = ""
    for item in sorted(fixes, key=lambda x: severity_order.get(x.get("severity", "info"), 9)):
        sev = item.get("severity", "info")
        badge = sev.upper()
        title = html_lib.escape(item.get("title", ""), quote=True)
        reason = html_lib.escape(item.get("reason", ""), quote=True)
        fix = html_lib.escape(item.get("fix", ""), quote=True)
        html += (
            f'<div class="issue-item {sev if sev in ("critical","warning","info") else "info"}">'
            f'<span class="issue-badge">{badge}</span>'
            f'<div><strong>{title}</strong><br>'
            f'<span style="color:var(--text-muted)">{reason}</span><br>'
            f'<span><strong>Fix:</strong> {fix}</span></div></div>'
        )
    return html


def maybe_emit_image_handoff(
    data: dict,
    *,
    html_path: str | None,
    public_root: Path | None,
    output_path: Path,
) -> dict:
    """Build and persist an image remediation handoff when actionable image issues exist."""
    artifact = {
        "generated": False,
        "path": None,
        "public_root": str(public_root) if public_root else None,
        "reason": None,
        "summary": None,
    }
    onpage = data.get("sections", {}).get("onpage", {})
    if not isinstance(onpage, dict) or onpage.get("error"):
        artifact["reason"] = "On-page analysis unavailable."
        return artifact
    images = onpage.get("images", [])
    if not isinstance(images, list) or not images:
        artifact["reason"] = "No page images detected."
        return artifact
    if not html_path:
        artifact["reason"] = "Fetched HTML was unavailable for handoff generation."
        return artifact

    handoff = build_handoff(
        analysis=onpage,
        input_path=Path(html_path),
        page_url=data.get("url"),
        public_root=public_root,
        page_context_override=None,
    )
    actionable_items = [
        item for item in handoff.get("items", [])
        if isinstance(item, dict) and item.get("reasons")
    ]
    if not actionable_items:
        artifact["reason"] = "No actionable image issues detected."
        artifact["summary"] = handoff.get("summary")
        return artifact

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(handoff, indent=2), encoding="utf-8")
    artifact["generated"] = True
    artifact["path"] = str(output_path.resolve())
    artifact["summary"] = handoff.get("summary")
    if public_root is None:
        artifact["reason"] = "Generated without a resolved local public root; some items may be marked manual."
    return artifact


def collect_data(
    url: str,
    *,
    public_root: Path | None = None,
    image_handoff_output: Path | None = None,
    emit_image_handoff: bool = True,
) -> dict:
    """Run all analysis scripts and collect results."""
    print(f"[analyze] {url}")
    data = {
        "url": url,
        "domain": urlparse(url).netloc,
        "timestamp": datetime.now().isoformat(),
        "sections": {},
        "artifacts": {},
    }

    # Fetch page for parse_html and readability
    print("  [fetch] page HTML")
    html_path = fetch_page(url)
    page_html = ""
    if html_path and os.path.exists(html_path):
        try:
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                page_html = f.read()
        except OSError:
            page_html = ""
    data["environment"] = detect_environment(page_html, url)
    pagespeed_args = [url, "--strategy", "mobile"]
    pagespeed_api_key = resolve_pagespeed_api_key(url)
    if pagespeed_api_key:
        pagespeed_args.extend(["--api-key", pagespeed_api_key])

    analyses = [
        ("robots", "robots_checker.py", [url]),
        ("security", "security_headers.py", [url]),
        ("social", "social_meta.py", [url]),
        ("redirects", "redirect_checker.py", [url]),
        ("llms_txt", "llms_txt_checker.py", [url]),
        ("broken_links", "broken_links.py", [url, "--workers", "5", "--timeout", "8"]),
        ("internal_links", "internal_links.py", [url, "--depth", "1", "--max-pages", "15"]),
        ("pagespeed", "pagespeed.py", pagespeed_args),
        # New analysis scripts (supplementary — failures don't block report)
        ("entity", "entity_checker.py", [url]),
        ("link_profile", "link_profile.py", [url, "--max-pages", "20"]),
        ("hreflang", "hreflang_checker.py", [url]),
        ("duplicate_content", "duplicate_content.py", [url]),
    ]

    # Add parse_html and readability if page was fetched
    if html_path:
        analyses.append(("onpage", "parse_html.py", [html_path, "--url", url]))
        analyses.append(("readability", "readability.py", [html_path]))
        analyses.append(("article", "article_seo.py", [url]))

    for name, script, args in analyses:
        print(f"  [run] {script}")
        start = time.time()
        result = run_script(script, args)
        elapsed = round(time.time() - start, 1)
        data["sections"][name] = result
        status = "[error]" if "error" in result and result.get("error") else "[ok]"
        print(f"  {status} {script} ({elapsed}s)")

    if emit_image_handoff and image_handoff_output is not None:
        print("  [build] image remediation handoff")
        artifact = maybe_emit_image_handoff(
            data,
            html_path=html_path,
            public_root=public_root,
            output_path=image_handoff_output,
        )
        data["artifacts"]["image_handoff"] = artifact
        handoff_status = "[ok]" if artifact.get("generated") else "[info]"
        detail = artifact.get("path") or artifact.get("reason") or "No details"
        print(f"  {handoff_status} image_handoff ({detail})")

    # Cleanup temp file
    if html_path and os.path.exists(html_path):
        os.unlink(html_path)

    data["environment_fixes"] = build_environment_fixes(data)

    return data


def calculate_overall_score(data: dict) -> dict:
    """Calculate overall SEO score from all analyses."""
    scores = {}
    weights = {
        "security": 8,
        "social": 5,
        "robots": 8,
        "broken_links": 10,
        "internal_links": 8,
        "redirects": 3,
        "llms_txt": 5,
        "pagespeed": 13,
        "onpage": 10,
        "readability": 8,
        "entity": 5,
        "link_profile": 7,
        "hreflang": 5,
        "duplicate_content": 5,
    }

    # Security score
    sec = data["sections"].get("security", {})
    scores["security"] = sec.get("score", 0)

    # Social meta score
    soc = data["sections"].get("social", {})
    scores["social"] = soc.get("score", 0)

    # Robots score
    rob = data["sections"].get("robots", {})
    if rob.get("status") == 200:
        base = 60
        if rob.get("sitemaps"):
            base += 20
        ai_managed = sum(1 for s in rob.get("ai_crawler_status", {}).values()
                         if "not managed" not in s)
        base += min(20, ai_managed * 2)
        scores["robots"] = min(100, base)
    elif rob.get("status") == 404:
        scores["robots"] = 20
    else:
        scores["robots"] = 0

    # Article score (informational, not weighted heavily)
    art = data["sections"].get("article", {})
    if art and not art.get("error"):
        art_score = 50
        if art.get("target_keyword"): art_score += 25
        if art.get("lsi_keywords"): art_score += 25
        scores["article"] = min(100, art_score)
    else:
        scores["article"] = 0

    # Broken links score
    bl = data["sections"].get("broken_links", {})
    summary = bl.get("summary", {})
    total = summary.get("total", 1) or 1
    broken = summary.get("broken", 0)
    scores["broken_links"] = max(0, 100 - int((broken / total) * 300))

    # Internal links score
    il = data["sections"].get("internal_links", {})
    il_issues = len(il.get("issues", []))
    scores["internal_links"] = max(0, 100 - il_issues * 20)

    # Redirects score
    red = data["sections"].get("redirects", {})
    red_issues = len(red.get("issues", []))
    scores["redirects"] = max(0, 100 - red_issues * 25)

    # llms.txt score
    llm = data["sections"].get("llms_txt", {})
    if llm.get("exists"):
        scores["llms_txt"] = llm.get("quality", {}).get("score", 0)
    else:
        scores["llms_txt"] = 0

    # PageSpeed score
    psi = data["sections"].get("pagespeed", {})
    scores["pagespeed"] = psi.get("performance_score", 0)

    # On-page score
    op = data["sections"].get("onpage", {})
    if op and not op.get("error"):
        op_score = 50
        if op.get("title"): op_score += 15
        if op.get("meta_description"): op_score += 15
        if op.get("h1"): op_score += 10
        if op.get("canonical"): op_score += 10
        scores["onpage"] = min(100, op_score)
    else:
        scores["onpage"] = 0

    # Readability score
    rd = data["sections"].get("readability", {})
    flesch = rd.get("flesch_reading_ease", 0)
    if flesch >= 60:
        scores["readability"] = 100
    elif flesch >= 30:
        scores["readability"] = 50 + int((flesch - 30) * (50 / 30))
    else:
        scores["readability"] = max(0, int(flesch * (50 / 30)))

    # Entity SEO score
    ent = data["sections"].get("entity", {})
    if ent and not ent.get("error"):
        sameas = ent.get("sameas_analysis", {})
        found = sameas.get("total_found", 0)
        has_wikidata = 1 if ent.get("wikidata", {}).get("found") else 0
        has_wikipedia = 1 if ent.get("wikipedia", {}).get("found") else 0
        ent_score = min(100, found * 15 + has_wikidata * 25 + has_wikipedia * 25)
        severity_penalties = {"Critical": 12, "Warning": 7, "Info": 2}
        issue_penalty = sum(
            severity_penalties.get(issue.get("severity", "Info"), 2)
            for issue in ent.get("issues", [])
        )
        ent_score = max(0, ent_score - issue_penalty)
        scores["entity"] = ent_score
    else:
        scores["entity"] = 0

    # Link profile score
    lp = data["sections"].get("link_profile", {})
    if lp and not lp.get("error"):
        avg_links = lp.get("avg_internal_links_per_page", 0)
        orphans = lp.get("orphan_pages", {}).get("count", 0)
        dead_ends = lp.get("dead_end_pages", {}).get("count", 0)
        lp_score = 70
        if avg_links >= 5: lp_score += 15
        elif avg_links >= 3: lp_score += 5
        else: lp_score -= 15
        lp_score -= min(30, orphans * 5)
        lp_score -= min(20, dead_ends * 3)
        scores["link_profile"] = max(0, min(100, lp_score))
    else:
        scores["link_profile"] = 0

    # Hreflang score (skip weight if not applicable)
    hf = data["sections"].get("hreflang", {})
    if hf and not hf.get("error"):
        if hf.get("hreflang_tags_found", 0) > 0:
            summary = hf.get("summary", {})
            hf_score = 100 - summary.get("critical", 0) * 30 - summary.get("high", 0) * 15 - summary.get("medium", 0) * 5
            scores["hreflang"] = max(0, min(100, hf_score))
        else:
            # No hreflang = single language site, skip from weighting
            scores["hreflang"] = None
    else:
        scores["hreflang"] = None

    # Duplicate content score
    dc = data["sections"].get("duplicate_content", {})
    if dc and not dc.get("error"):
        dupes = len(dc.get("near_duplicates", []))
        thin = len(dc.get("thin_pages", []))
        dc_score = 100 - dupes * 20 - thin * 10
        scores["duplicate_content"] = max(0, min(100, dc_score))
    else:
        scores["duplicate_content"] = 0

    # Weighted average (only scored categories)
    total_weight = 0
    weighted_sum = 0
    for k, w in weights.items():
        if k in scores:
            val = scores.get(k)
            if val is not None:
                total_weight += w
                weighted_sum += val * w
    
    overall = round(weighted_sum / total_weight) if total_weight else 0

    # Coerce any None scores to 0 to prevent UI crashes
    for k in list(scores.keys()):
        if scores[k] is None:
            scores[k] = 0

    return {
        "overall": overall,
        "categories": scores,
        "weights": weights,
    }


def make_finding(
    severity: str,
    finding: str,
    evidence: str,
    fix: str,
    source: str,
    confidence: str = "Confirmed",
) -> dict:
    return {
        "severity": severity,
        "finding": finding,
        "evidence": evidence,
        "fix": fix,
        "source": source,
        "confidence": confidence,
    }


def build_report_findings(data: dict) -> dict:
    """Collect normalized, verified findings for markdown reporting."""
    findings: list[dict] = []
    limitations: list[str] = []
    sections = data.get("sections", {})

    for section_name, section_data in sections.items():
        if isinstance(section_data, dict) and section_data.get("error"):
            limitations.append(f"{section_name}: {section_data.get('error')}")

    onpage = sections.get("onpage", {})
    if isinstance(onpage, dict) and not onpage.get("error"):
        title = (onpage.get("title") or "").strip()
        meta = (onpage.get("meta_description") or "").strip()
        canonical = (onpage.get("canonical") or "").strip()
        h1s = onpage.get("h1", []) if isinstance(onpage.get("h1"), list) else []
        images = onpage.get("images", []) if isinstance(onpage.get("images"), list) else []

        if not title:
            findings.append(make_finding("Warning", "Title tag is missing", "No <title> tag was detected.", "Add a unique, descriptive title tag between 50 and 60 characters.", "onpage"))
        elif len(title) < 30 or len(title) > 65:
            findings.append(make_finding("Warning", "Title tag length is out of range", f"Current title length is {len(title)} characters.", "Rewrite the title tag to land near 50-60 characters while preserving the main intent.", "onpage"))

        if not meta:
            findings.append(make_finding("Warning", "Meta description is missing", "No meta description was detected.", "Add a compelling meta description around 150-160 characters.", "onpage"))
        elif len(meta) < 110 or len(meta) > 170:
            findings.append(make_finding("Warning", "Meta description length is out of range", f"Current meta description length is {len(meta)} characters.", "Rewrite the meta description so it is concise, descriptive, and closer to 150-160 characters.", "onpage"))

        if not h1s:
            findings.append(make_finding("Critical", "Primary H1 is missing", "No H1 heading was detected on the page.", "Add one clear H1 aligned to the page intent.", "onpage"))
        elif len(h1s) > 1:
            findings.append(make_finding("Warning", "Multiple H1 headings were detected", f"The page contains {len(h1s)} H1 headings.", "Keep one primary H1 and move supporting headings down the hierarchy.", "onpage"))

        if not canonical:
            findings.append(make_finding("Warning", "Canonical tag is missing", "No canonical URL was detected in the page head.", "Add a self-referencing canonical tag unless the page intentionally canonicalizes elsewhere.", "onpage"))

        if images:
            missing_alt = sum(1 for image in images if str(image.get("alt") or "").strip() == "")
            missing_dimensions = sum(1 for image in images if not image.get("width") or not image.get("height"))
            missing_loading = sum(1 for index, image in enumerate(images) if index > 0 and not image.get("loading"))
            next_gen_candidates = sum(
                1
                for image in images
                if Path(urlparse(str(image.get("src") or "")).path or str(image.get("src") or "")).suffix.lower() in {".png", ".jpg", ".jpeg"}
            )
            if missing_alt:
                findings.append(make_finding("Warning", "Some page images are missing alt text", f"{missing_alt} image(s) have empty or missing alt attributes.", "Add descriptive alt text or use empty alt only for decorative images.", "onpage"))
            if missing_dimensions:
                findings.append(make_finding("Warning", "Some page images are missing dimensions", f"{missing_dimensions} image(s) are missing width and/or height attributes.", "Add width and height attributes or an equivalent reserved aspect ratio to reduce CLS.", "onpage"))
            if missing_loading:
                findings.append(make_finding("Info", "Below-the-fold images are missing lazy loading", f"{missing_loading} non-primary image(s) are missing loading=\"lazy\".", "Add loading=\"lazy\" to non-LCP images.", "onpage"))
            if next_gen_candidates:
                findings.append(make_finding("Info", "Some page images still use PNG or JPEG", f"{next_gen_candidates} image(s) could move to WebP or AVIF.", "Convert suitable PNG/JPEG assets to next-gen formats and add responsive variants where useful.", "onpage"))

    security = sections.get("security", {})
    if isinstance(security, dict) and not security.get("error"):
        missing_headers = security.get("headers_missing", {})
        if isinstance(missing_headers, dict) and missing_headers:
            count = len(missing_headers)
            severity = "Critical" if count >= 4 else "Warning"
            findings.append(make_finding(severity, "Important security headers are missing", f"{count} security header(s) were reported missing.", "Add the missing headers at the application or CDN layer, starting with HSTS, CSP, and frame protection.", "security"))

    social = sections.get("social", {})
    if isinstance(social, dict) and not social.get("error"):
        og_missing = social.get("og_missing", []) if isinstance(social.get("og_missing"), list) else []
        twitter_missing = social.get("twitter_missing", []) if isinstance(social.get("twitter_missing"), list) else []
        if og_missing or twitter_missing:
            findings.append(make_finding("Warning", "Social preview metadata is incomplete", f"Missing Open Graph tags: {len(og_missing)}; missing Twitter tags: {len(twitter_missing)}.", "Add the missing OG and Twitter tags so shared previews are complete and consistent.", "social"))

    llms_txt = sections.get("llms_txt", {})
    if isinstance(llms_txt, dict) and not llms_txt.get("error") and not llms_txt.get("exists"):
        findings.append(make_finding("Info", "llms.txt is missing", "No llms.txt file was detected.", "Add llms.txt with a concise site summary and key URLs for AI crawlers.", "llms_txt"))

    broken_links = sections.get("broken_links", {})
    if isinstance(broken_links, dict) and not broken_links.get("error"):
        summary = broken_links.get("summary", {})
        broken_count = summary.get("broken", 0) if isinstance(summary, dict) else 0
        if broken_count:
            severity = "Critical" if broken_count >= 5 else "Warning"
            findings.append(make_finding(severity, "Broken links were detected", f"{broken_count} broken link(s) were found during the crawl.", "Repair, redirect, or remove the broken links starting with internal navigation and high-value pages.", "broken_links"))

    internal_links = sections.get("internal_links", {})
    if isinstance(internal_links, dict) and not internal_links.get("error"):
        orphan_candidates = internal_links.get("orphan_candidates", []) if isinstance(internal_links.get("orphan_candidates"), list) else []
        if orphan_candidates:
            findings.append(make_finding("Warning", "Potential orphan pages were detected", f"{len(orphan_candidates)} page(s) appear to have weak internal linking.", "Add contextual internal links from relevant hub or supporting pages.", "internal_links"))

    redirects = sections.get("redirects", {})
    if isinstance(redirects, dict) and not redirects.get("error"):
        redirect_issues = redirects.get("issues", []) if isinstance(redirects.get("issues"), list) else []
        if redirect_issues:
            findings.append(make_finding("Warning", "Redirect issues were detected", f"{len(redirect_issues)} redirect issue(s) were reported.", "Flatten chains, remove loops, and standardize direct canonical destinations.", "redirects"))

    pagespeed = sections.get("pagespeed", {})
    if isinstance(pagespeed, dict) and not pagespeed.get("error"):
        performance_score = pagespeed.get("performance_score", 0)
        if isinstance(performance_score, (int, float)) and performance_score < 50:
            findings.append(make_finding("Critical", "Performance score is poor", f"Mobile performance score is {performance_score}.", "Prioritize LCP, INP, and CLS fixes and reduce render-blocking work.", "pagespeed"))
        elif isinstance(performance_score, (int, float)) and performance_score < 80:
            findings.append(make_finding("Warning", "Performance score needs improvement", f"Mobile performance score is {performance_score}.", "Target the largest performance bottlenecks before the next release.", "pagespeed"))

    readability = sections.get("readability", {})
    if isinstance(readability, dict) and not readability.get("error"):
        flesch = readability.get("flesch_reading_ease", 100)
        avg_sentence_length = readability.get("avg_sentence_length", 0)
        if isinstance(flesch, (int, float)) and flesch < 40:
            findings.append(make_finding("Warning", "Readability is difficult", f"Flesch Reading Ease is {flesch}; average sentence length is {avg_sentence_length}.", "Shorten sentences and paragraphs and introduce clearer subheadings.", "readability"))

    entity = sections.get("entity", {})
    if isinstance(entity, dict) and not entity.get("error"):
        entity_issues = entity.get("issues", []) if isinstance(entity.get("issues"), list) else []
        if entity_issues:
            findings.append(make_finding("Info", "Entity SEO signals are incomplete", f"{len(entity_issues)} entity issue(s) were reported.", "Strengthen sameAs links and external knowledge-graph signals where relevant.", "entity"))

    link_profile = sections.get("link_profile", {})
    if isinstance(link_profile, dict) and not link_profile.get("error"):
        orphan_count = 0
        dead_end_count = 0
        if isinstance(link_profile.get("orphan_pages"), dict):
            orphan_count = int(link_profile["orphan_pages"].get("count", 0))
        if isinstance(link_profile.get("dead_end_pages"), dict):
            dead_end_count = int(link_profile["dead_end_pages"].get("count", 0))
        if orphan_count or dead_end_count:
            findings.append(make_finding("Warning", "Sitewide internal link coverage is weak", f"{orphan_count} orphan page(s) and {dead_end_count} dead-end page(s) were reported.", "Improve hub-to-detail linking and make sure key pages have both inbound and onward links.", "link_profile"))

    hreflang = sections.get("hreflang", {})
    if isinstance(hreflang, dict) and not hreflang.get("error"):
        summary = hreflang.get("summary", {})
        critical_count = int(summary.get("critical", 0)) if isinstance(summary, dict) else 0
        high_count = int(summary.get("high", 0)) if isinstance(summary, dict) else 0
        if critical_count or high_count:
            severity = "Critical" if critical_count else "Warning"
            findings.append(make_finding(severity, "Hreflang implementation has significant issues", f"Critical issues: {critical_count}; high issues: {high_count}.", "Correct hreflang references, return tags, and locale targeting.", "hreflang"))

    duplicate_content = sections.get("duplicate_content", {})
    if isinstance(duplicate_content, dict) and not duplicate_content.get("error"):
        near_duplicates = duplicate_content.get("near_duplicates", []) if isinstance(duplicate_content.get("near_duplicates"), list) else []
        thin_pages = duplicate_content.get("thin_pages", []) if isinstance(duplicate_content.get("thin_pages"), list) else []
        if near_duplicates or thin_pages:
            findings.append(make_finding("Warning", "Content uniqueness needs attention", f"{len(near_duplicates)} near-duplicate page(s) and {len(thin_pages)} thin page(s) were detected.", "Consolidate duplicate pages and expand thin pages with unique, high-intent content.", "duplicate_content"))

    verified = verify_findings(findings=findings, context={})
    return {
        "raw": findings,
        "verified": verified.get("findings", []),
        "dropped": verified.get("dropped", []),
        "limitations": limitations,
    }


def severity_to_priority(severity: str) -> str:
    mapping = {
        "Critical": "Critical",
        "Warning": "High",
        "Info": "Medium",
        "Pass": "Low",
    }
    return mapping.get(severity, "Medium")


def generate_full_audit_report_markdown(
    data: dict,
    scores: dict,
    findings_bundle: dict,
    artifact_paths: dict[str, str | None],
) -> str:
    verified = findings_bundle.get("verified", [])
    limitations = findings_bundle.get("limitations", [])
    critical = [item for item in verified if item.get("severity") == "Critical"][:5]
    quick_wins = [item for item in verified if item.get("severity") != "Critical"][:5]

    artifact_lines = [
        f"- `{label}`: `{path}`"
        for label, path in artifact_paths.items()
        if path
    ]
    if not artifact_lines:
        artifact_lines = ["- No generated artifacts recorded."]

    findings_rows = []
    for item in verified:
        findings_rows.append(
            f"| {item.get('severity', 'Info')} | {item.get('finding', '—')} | {item.get('evidence', '—')} | {item.get('source', '—')} | {item.get('confidence', 'Confirmed')} |"
        )
    if not findings_rows:
        findings_rows.append("| Pass | No major verified issues were generated. | — | report | Confirmed |")

    score_rows = [
        f"| {category.replace('_', ' ').title()} | {value} |"
        for category, value in sorted(scores.get("categories", {}).items())
    ]

    environment_lines = []
    for item in data.get("environment_fixes", []):
        environment_lines.append(
            f"- **{item.get('severity', 'info').title()}**: {item.get('title', 'Guidance')} — {item.get('fix', '')}"
        )
    if not environment_lines:
        environment_lines = ["- No environment-specific implementation notes were generated."]

    limitation_lines = [f"- {item}" for item in limitations] if limitations else ["- No major environment limitations were recorded."]

    critical_lines = [f"- {item.get('finding')}: {item.get('fix')}" for item in critical] or ["- No critical issues were verified."]
    quick_win_lines = [f"- {item.get('finding')}: {item.get('fix')}" for item in quick_wins] or ["- No quick wins were generated."]

    return (
        f"# FULL-AUDIT-REPORT\n\n"
        f"## Audit Summary\n"
        f"- URL: `{data.get('url')}`\n"
        f"- Generated: `{data.get('timestamp')}`\n"
        f"- Overall Score: **{scores.get('overall', 0)}/100**\n"
        f"- Environment: **{data.get('environment', {}).get('primary', 'Unknown')}**\n\n"
        f"## Artifacts\n"
        + "\n".join(artifact_lines)
        + "\n\n## Top Critical Issues\n"
        + "\n".join(critical_lines)
        + "\n\n## Quick Wins\n"
        + "\n".join(quick_win_lines)
        + "\n\n## Scorecard\n| Category | Score |\n|---|---|\n"
        + "\n".join(score_rows)
        + "\n\n## Verified Findings\n| Severity | Finding | Evidence | Source | Confidence |\n|---|---|---|---|---|\n"
        + "\n".join(findings_rows)
        + "\n\n## Environment Guidance\n"
        + "\n".join(environment_lines)
        + "\n\n## Environment Limitations\n"
        + "\n".join(limitation_lines)
        + "\n"
    )


def generate_action_plan_markdown(
    data: dict,
    findings_bundle: dict,
    artifact_paths: dict[str, str | None],
) -> str:
    verified = findings_bundle.get("verified", [])
    grouped: dict[str, list[dict]] = {"Critical": [], "High": [], "Medium": [], "Low": []}
    for item in verified:
        grouped.setdefault(severity_to_priority(item.get("severity", "Info")), []).append(item)

    sections: list[str] = []
    for priority in ("Critical", "High", "Medium", "Low"):
        items = grouped.get(priority, [])
        if not items:
            sections.append(f"## {priority}\n- No actions queued.\n")
            continue
        lines = [f"## {priority}"]
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. {item.get('finding')}")
            lines.append(f"Evidence: {item.get('evidence')}")
            lines.append(f"Fix: {item.get('fix')}")
            lines.append(f"Source: `{item.get('source', 'report')}`")
            lines.append("")
        sections.append("\n".join(lines).rstrip())

    image_handoff_path = artifact_paths.get("Image handoff")
    image_section = ""
    if image_handoff_path:
        webp_script = resolve_webp_me_daddy()
        image_section = (
            "## Image Remediation Workflow\n"
            f"- Preview the generated handoff with `python {webp_script} seo-handoff \"{image_handoff_path}\" --dry-run --json seo-image-apply-report.json`\n"
            f"- Apply it with `python {webp_script} seo-handoff \"{image_handoff_path}\" --yes --overwrite --json seo-image-apply-report.json`\n\n"
        )

    return (
        f"# ACTION-PLAN\n\n"
        f"- URL: `{data.get('url')}`\n"
        f"- Generated: `{data.get('timestamp')}`\n\n"
        f"{image_section}"
        + "\n\n".join(sections)
        + "\n"
    )


def write_markdown_artifacts(
    *,
    data: dict,
    scores: dict,
    findings_bundle: dict,
    audit_report_path: Path,
    action_plan_path: Path,
    claude_handoff_path: Path,
    codex_handoff_path: Path,
    html_report_path: Path,
) -> dict[str, str]:
    artifact_paths = {
        "HTML dashboard": str(html_report_path.resolve()),
        "Full audit report": str(audit_report_path.resolve()),
        "Action plan": str(action_plan_path.resolve()),
        "Claude handoff": str(claude_handoff_path.resolve()),
        "Codex handoff": str(codex_handoff_path.resolve()),
    }
    image_handoff = data.get("artifacts", {}).get("image_handoff", {})
    if isinstance(image_handoff, dict) and image_handoff.get("generated"):
        artifact_paths["Image handoff"] = str(image_handoff.get("path"))

    audit_report_path.parent.mkdir(parents=True, exist_ok=True)
    action_plan_path.parent.mkdir(parents=True, exist_ok=True)
    claude_handoff_path.parent.mkdir(parents=True, exist_ok=True)
    codex_handoff_path.parent.mkdir(parents=True, exist_ok=True)
    audit_report_path.write_text(
        generate_full_audit_report_markdown(data, scores, findings_bundle, artifact_paths),
        encoding="utf-8",
    )
    action_plan_path.write_text(
        generate_action_plan_markdown(data, findings_bundle, artifact_paths),
        encoding="utf-8",
    )
    claude_handoff_path.write_text(
        build_agent_handoff_markdown(agent="Claude", data=data, scores=scores, findings_bundle=findings_bundle, artifact_paths=artifact_paths),
        encoding="utf-8",
    )
    codex_handoff_path.write_text(
        build_agent_handoff_markdown(agent="Codex", data=data, scores=scores, findings_bundle=findings_bundle, artifact_paths=artifact_paths),
        encoding="utf-8",
    )
    return artifact_paths


def render_recommendations(section_data: dict) -> str:
    """Render recommendations from a section's JSON data."""
    recs = section_data.get("recommendations", section_data.get("suggestions", []))
    if isinstance(recs, dict):
        items = [f"{k}: {v}" for k, v in recs.items()]
    elif isinstance(recs, list):
        items = recs
    else:
        items = []
    # Also check opportunities from pagespeed
    opps = section_data.get("opportunities", [])
    if isinstance(opps, list):
        items.extend(opps)

    # Render structured issues (used by entity_checker, hreflang_checker, etc.)
    issues = section_data.get("issues", [])
    issues_html = ""
    if isinstance(issues, list) and issues:
        severity_map = {"critical": "critical", "high": "critical", "warning": "warning", "medium": "warning", "info": "info", "low": "info"}
        for issue in issues[:15]:
            if isinstance(issue, dict):
                sev = severity_map.get(issue.get("severity", "info").lower(), "info")
                badge = html_lib.escape(issue.get("severity", "INFO").upper(), quote=True)
                finding = html_lib.escape(str(issue.get("finding", "")), quote=True)
                fix = html_lib.escape(str(issue.get("fix", "")), quote=True)
                issues_html += (
                    f'<div class="issue-item {sev}">'
                    f'<span class="issue-badge">{badge}</span>'
                    f'<div><strong>{finding}</strong>'
                    f'{f"<br><span style=&quot;color:var(--text-muted)&quot;>Fix: {fix}</span>" if fix else ""}'
                    f'</div></div>'
                )
            elif isinstance(issue, str):
                items.append(issue)

    html = ""
    if issues_html:
        html += f'<div style="margin-top:16px"><h3 style="font-size:0.95rem;margin-bottom:8px;">🔍 Issues Found</h3>{issues_html}</div>'
    if items:
        html += '<div style="margin-top:16px"><h3 style="font-size:0.95rem;margin-bottom:8px;">💡 Recommendations</h3>'
        for item in items[:15]:
            item_str = str(item) if not isinstance(item, str) else item
            html += f'<div class="issue-item info"><span class="issue-badge">FIX</span> {item_str}</div>'
        html += '</div>'
    return html


def render_readability_rewrites(readability_data: dict) -> str:
    """Render concrete sentence replacements for readability fixes."""
    rewrites = readability_data.get("sentence_rewrites", [])
    if not rewrites:
        return ""

    html = (
        '<div style="margin-top:16px">'
        '<h3 style="font-size:0.95rem;margin-bottom:8px;">✍️ What To Replace (Before/After)</h3>'
    )
    for item in rewrites[:5]:
        current = html_lib.escape(str(item.get("current", "")), quote=True)
        suggested = html_lib.escape(str(item.get("suggested", "")), quote=True)
        wc_raw = item.get("current_word_count", "")
        wc_label = f"{wc_raw}w" if isinstance(wc_raw, (int, float)) else str(wc_raw)
        wc = html_lib.escape(wc_label, quote=True)
        html += (
            '<div class="issue-item warning">'
            f'<span class="issue-badge">SENTENCE ({wc})</span>'
            '<div>'
            f'<div><strong>Current:</strong> {current}</div>'
            f'<div style="margin-top:6px;"><strong>Replace with:</strong> {suggested}</div>'
            '</div>'
            '</div>'
        )
    html += "</div>"
    return html


def render_all_recommendations(data: dict) -> str:
    """Render all recommendations from all sections."""
    section_names = {
        "security": "🔒 Security", "social": "📱 Social Meta", "robots": "🤖 Robots",
        "broken_links": "🔗 Links", "internal_links": "🕸️ Internal Links",
        "redirects": "↪️ Redirects", "llms_txt": "🧠 AI Search",
        "pagespeed": "⚡ Performance", "onpage": "📝 On-Page", "readability": "📖 Readability",
        "article": "📄 Article SEO", "entity": "🏛️ Entity SEO",
        "link_profile": "🔗 Link Profile", "hreflang": "🌍 Hreflang",
        "duplicate_content": "📋 Content Uniqueness",
    }
    html = ""
    env_fixes = data.get("environment_fixes", [])
    if env_fixes:
        html += '<h3 style="font-size:0.95rem;margin:16px 0 8px;">🛠️ Environment-Specific Fixes</h3>'
        for item in env_fixes[:8]:
            title = html_lib.escape(item.get("title", ""), quote=True)
            fix = html_lib.escape(item.get("fix", ""), quote=True)
            html += f'<div class="issue-item info"><span class="issue-badge">FIX</span> <strong>{title}</strong>: {fix}</div>'

    for key, label in section_names.items():
        section = data["sections"].get(key, {})
        recs = section.get("recommendations", section.get("suggestions", []))
        if isinstance(recs, dict):
            items = [f"{k}: {v}" for k, v in recs.items()]
        elif isinstance(recs, list):
            items = recs
        else:
            items = []
        opps = section.get("opportunities", [])
        if isinstance(opps, list):
            items.extend(opps)
        if key == "readability":
            for rw in section.get("sentence_rewrites", [])[:3]:
                cur = html_lib.escape(str(rw.get("current", ""))[:180], quote=True)
                sug = html_lib.escape(str(rw.get("suggested", ""))[:180], quote=True)
                items.append(f"Rewrite: {cur} → {sug}")
        if items:
            html += f'<h3 style="font-size:0.95rem;margin:16px 0 8px;">{label}</h3>'
            for item in items[:10]:
                html += f'<div class="issue-item info"><span class="issue-badge">FIX</span> {item}</div>'
    return html if html else '<p style="color:var(--green)">✅ No recommendations — everything looks good!</p>'


def provider_scope_for_source(source: str) -> str:
    source = (source or "").lower()
    if source in {"pagespeed", "schema"}:
        return "Google-specific"
    if source == "llms_txt":
        return "Experimental"
    return "Universal"


def action_type_for_finding(item: dict) -> str:
    severity = str(item.get("severity", "Info")).lower()
    source = str(item.get("source", "")).lower()
    if severity == "critical":
        return "Required"
    if source == "llms_txt":
        return "Optional"
    if severity == "warning":
        return "Recommended"
    return "Optional"


def evidence_source_for_source(source: str) -> str:
    mapping = {
        "onpage": "raw HTML / parse_html",
        "security": "security_headers.py",
        "social": "social_meta.py",
        "llms_txt": "llms_txt_checker.py",
        "internal_links": "internal_links.py",
        "readability": "readability.py",
        "entity": "entity_checker.py",
        "link_profile": "link_profile.py",
        "hreflang": "hreflang_checker.py",
        "duplicate_content": "duplicate_content.py",
        "pagespeed": "PageSpeed Insights API",
        "broken_links": "broken_links.py",
        "redirects": "redirect_checker.py",
        "robots": "robots_checker.py",
    }
    return mapping.get((source or "").lower(), source or "script output")


def score_rating(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Mixed"
    return "At-risk"


def format_report_timestamp(timestamp: str) -> str:
    try:
        return datetime.fromisoformat(str(timestamp)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(timestamp or "Unknown")


def severity_class(severity: str) -> str:
    return str(severity or "Info").strip().lower().replace(" ", "-")


def impact_for_finding(item: dict[str, object]) -> str:
    severity = str(item.get("severity", "Info")).lower()
    source = str(item.get("source", "")).lower()
    if severity == "critical":
        return "High"
    if source in {"pagespeed", "internal_links", "entity", "duplicate_content"}:
        return "High"
    if severity == "warning":
        return "Medium"
    return "Low"


def effort_for_finding(item: dict[str, object]) -> str:
    source = str(item.get("source", "")).lower()
    finding = str(item.get("finding", "")).lower()
    if source in {"pagespeed", "duplicate_content"}:
        return "High"
    if source in {"internal_links", "link_profile", "entity", "hreflang"}:
        return "Medium"
    if any(token in finding for token in ("title", "meta", "canonical", "h1", "llms.txt")):
        return "Low"
    return "Medium"


def category_label(category: str) -> str:
    return str(category or "score").replace("_", " ").title()


def build_executive_summary(
    *,
    findings: list[dict],
    critical_count: int,
    warning_count: int,
    info_count: int,
    overall: int,
    rating: str,
    next_move_fix: str,
    limitations: list[str],
) -> str:
    if findings:
        top_summary = "; ".join(
            str(item.get("finding", item.get("title", "finding")))
            for item in findings[:3]
        )
        summary = (
            f"Overall, this site scores {overall}/100 ({rating}). "
            f"The audit found {len(findings)} verified finding{'s' if len(findings) != 1 else ''}: "
            f"{critical_count} critical, {warning_count} warning, and {info_count} info/opportunity. "
            f"The main items to address are {top_summary}. "
            f"Recommended next move: {next_move_fix}"
        )
    else:
        summary = (
            f"Overall, this site scores {overall}/100 ({rating}) and no urgent SEO issues were verified in this run. "
            "Keep monitoring the site and rerun the report after major content, template, or platform changes."
        )
    if limitations:
        summary += f" Environment note: {limitations[0]}"
    return summary


def build_summary_item_html(
    item: dict[str, object],
    *,
    fallback_fix: str = "Keep monitoring this signal and rerun the audit after changes.",
) -> str:
    title = html_lib.escape(str(item.get("finding", item.get("title", "Finding"))))
    evidence = html_lib.escape(str(item.get("evidence", item.get("explanation", "No extra evidence was recorded."))))
    fix = html_lib.escape(str(item.get("fix", fallback_fix)))
    impact = html_lib.escape(str(item.get("impact", impact_for_finding(item))))
    effort = html_lib.escape(str(item.get("effort", effort_for_finding(item))))
    return (
        '<li class="sw-summary-item">'
        f"<div><strong>{title}</strong><p>{evidence}</p><p><b>How to resolve:</b> {fix}</p></div>"
        f'<div class="sw-summary-chips"><span>Impact: {impact}</span><span>Effort: {effort}</span></div>'
        "</li>"
    )


def render_summary_group(
    *,
    css_class: str,
    icon: str,
    title: str,
    count: int,
    intro: str,
    items_html: str,
    empty_text: str,
) -> str:
    body = items_html or f'<li class="sw-summary-item sw-empty"><p>{html_lib.escape(empty_text)}</p></li>'
    return (
        f'<section class="sw-summary-group {html_lib.escape(css_class, quote=True)}">'
        f'<div class="sw-summary-group-head"><div><h2>{html_lib.escape(icon)} {html_lib.escape(title)}</h2>'
        f'<p>{html_lib.escape(intro)}</p></div><span class="sw-summary-count">{count}</span></div>'
        f'<ul class="sw-summary-list">{body}</ul>'
        "</section>"
    )


def build_agent_handoff_markdown(
    *,
    agent: str,
    data: dict,
    scores: dict,
    findings_bundle: dict,
    artifact_paths: dict[str, str | None],
) -> str:
    verified = findings_bundle.get("verified", [])
    limitations = findings_bundle.get("limitations", [])
    categories = scores.get("categories", {})
    overall = int(scores.get("overall", 0) or 0)
    rating = score_rating(overall)
    critical_count = sum(1 for item in verified if str(item.get("severity", "")).lower() == "critical")
    warning_count = sum(1 for item in verified if str(item.get("severity", "")).lower() == "warning")
    info_count = sum(1 for item in verified if str(item.get("severity", "")).lower() == "info")
    top_finding = next((item for item in verified if str(item.get("severity", "")).lower() == "critical"), None)
    top_finding = top_finding or next((item for item in verified if str(item.get("severity", "")).lower() == "warning"), None)
    next_move_title = top_finding.get("finding", "Review the highest-priority findings") if top_finding else "No urgent findings verified"
    next_move_fix = top_finding.get("fix", "Keep monitoring and rerun the audit after major site changes.") if top_finding else "Keep monitoring and rerun the audit after major site changes."
    executive_summary = build_executive_summary(
        findings=verified,
        critical_count=critical_count,
        warning_count=warning_count,
        info_count=info_count,
        overall=overall,
        rating=rating,
        next_move_fix=str(next_move_fix),
        limitations=limitations,
    )

    grouped = {"Critical": [], "Warning": [], "Info": []}
    for item in verified:
        grouped.setdefault(str(item.get("severity", "Info")), []).append(item)

    group_sections: list[str] = []
    for severity in ("Critical", "Warning", "Info"):
        items = grouped.get(severity, [])
        if not items:
            group_sections.append(f"## {severity}\n- No {severity.lower()} items recorded.")
            continue
        lines = [f"## {severity}"]
        for index, item in enumerate(items, start=1):
            lines.extend(
                [
                    f"{index}. {item.get('finding', 'Finding')}",
                    f"   - Evidence: {item.get('evidence', 'No evidence recorded.')}",
                    f"   - Fix: {item.get('fix', 'No fix recorded.')}",
                    f"   - Impact: {impact_for_finding(item)}",
                    f"   - Effort: {effort_for_finding(item)}",
                ]
            )
        group_sections.append("\n".join(lines))

    strong_scores = [
        f"- {category_label(category)}: {value}/100. Preserve this implementation and monitor after major changes."
        for category, value in sorted(categories.items())
        if isinstance(value, (int, float)) and value >= 90
    ] or ["- No strong score categories were recorded in this run."]
    fix_sequence = [
        f"{index}. {item.get('finding', 'Finding')} — {item.get('fix', 'Review and resolve this item.')}"
        for index, item in enumerate(verified[:8], start=1)
    ] or ["1. No immediate implementation tasks were generated."]
    artifact_lines = [
        f"- {label}: `{path}`"
        for label, path in artifact_paths.items()
        if path
    ] or ["- No generated artifacts recorded."]
    limitation_lines = [f"- {item}" for item in limitations] or ["- No environment limitations recorded."]

    if agent == "Claude":
        title = "# CLAUDE-HANDOFF"
        safe_instructions = (
            "## Claude Code Instructions\n"
            "- Open the SEO project folder before editing.\n"
            "- Read `CLAUDE.md` if present.\n"
            "- Run tests before and after changes.\n"
            "- Do not read secrets, `.env` files, API keys, cookies, or credentials.\n"
            "- Do not push, delete, reset, or rewrite history without explicit approval."
        )
    else:
        title = "# CODEX-HANDOFF"
        safe_instructions = (
            "## Codex Instructions\n"
            "- Read `AGENTS.md` and relevant Shadewater project memory where present.\n"
            "- Inspect git state before edits when git is available.\n"
            "- Use existing tests and generated report artifacts as the source of truth.\n"
            "- Do not reset, delete, revert user work, or push without explicit approval.\n"
            "- Do not expose secrets, `.env` values, API keys, cookies, or credentials."
        )

    return (
        f"{title}\n\n"
        f"- URL: `{data.get('url')}`\n"
        f"- Domain: `{data.get('domain') or urlparse(str(data.get('url', ''))).netloc}`\n"
        f"- Generated: `{data.get('timestamp')}`\n"
        f"- Overall Score: **{overall}/100 ({rating})**\n"
        f"- Environment: **{data.get('environment', {}).get('detected') or data.get('environment', {}).get('primary') or 'Unknown'}**\n\n"
        "## Executive Summary\n"
        f"{executive_summary}\n\n"
        "## Recommended Next Move\n"
        f"**{next_move_title}** — {next_move_fix}\n\n"
        "## Fix Sequence\n"
        + "\n".join(fix_sequence)
        + "\n\n"
        + "\n\n".join(group_sections)
        + "\n\n## Strong Scores\n"
        + "\n".join(strong_scores)
        + "\n\n## Environment Limitations\n"
        + "\n".join(limitation_lines)
        + "\n\n## Artifacts\n"
        + "\n".join(artifact_lines)
        + "\n\n"
        + safe_instructions
        + "\n"
    )


def generate_shadewater_dashboard_html(
    data: dict,
    scores: dict,
    brand_logo_uri: str | None = None,
) -> str:
    """Generate the Claude Design-inspired Shadewater report dashboard."""
    domain = data.get("domain") or urlparse(data.get("url", "")).netloc or "site"
    url = data.get("url", "")
    timestamp = data.get("timestamp", "")
    environment = data.get("environment", {}).get("detected") or data.get("environment", {}).get("primary") or data.get("environment", {}).get("name") or "Unknown"
    overall = int(scores.get("overall", 0) or 0)
    findings_bundle = build_report_findings(data)
    findings = findings_bundle.get("verified", [])
    limitations = findings_bundle.get("limitations", [])
    categories = scores.get("categories", {})
    report_title = "Shadewater SEO Report"
    run_id = "SWL-" + re.sub(r"[^A-Za-z0-9]+", "-", domain).strip("-").upper()[:18]
    generated_label = format_report_timestamp(timestamp)
    rating = score_rating(overall)
    pdf_filename = html_lib.escape(
        f"{re.sub(r'[^a-z0-9]+', '-', domain.lower()).strip('-') or 'seo-report'}-seo-report.pdf",
        quote=True,
    )

    warning_count = sum(1 for item in findings if str(item.get("severity", "")).lower() == "warning")
    info_count = sum(1 for item in findings if str(item.get("severity", "")).lower() == "info")
    critical_count = sum(1 for item in findings if str(item.get("severity", "")).lower() == "critical")
    pass_count = sum(1 for value in categories.values() if isinstance(value, (int, float)) and value >= 90)
    top_finding = next((item for item in findings if str(item.get("severity", "")).lower() == "critical"), None)
    top_finding = top_finding or next((item for item in findings if str(item.get("severity", "")).lower() == "warning"), None)
    next_move_title = top_finding.get("finding", "Review the highest-priority findings") if top_finding else "No urgent findings verified"
    next_move_fix = top_finding.get("fix", "Keep monitoring and rerun the audit after major site changes.") if top_finding else "Keep monitoring and rerun the audit after major site changes."
    pagespeed_section = data.get("sections", {}).get("pagespeed", {})
    pagespeed_error = isinstance(pagespeed_section, dict) and pagespeed_section.get("error")
    pagespeed_score = categories.get("pagespeed")
    if pagespeed_error:
        speed_value = "N/A"
        speed_rating = "Environment-limited"
        speed_card_class = " env"
    elif isinstance(pagespeed_score, (int, float)):
        speed_value = str(int(pagespeed_score))
        speed_rating = score_rating(int(pagespeed_score))
        speed_card_class = ""
    else:
        speed_value = "N/A"
        speed_rating = "Pending"
        speed_card_class = " env"
    critical_items = [item for item in findings if str(item.get("severity", "")).lower() == "critical"]
    warning_items = [item for item in findings if str(item.get("severity", "")).lower() == "warning"]
    info_items = [item for item in findings if str(item.get("severity", "")).lower() == "info"]
    strong_items = [
        {
            "finding": f"{category_label(key)} is strong",
            "evidence": f"This category scored {int(value)}/100.",
            "fix": "Maintain this implementation and monitor it after major content, template, or platform changes.",
            "impact": "Protective",
            "effort": "Low",
        }
        for key, value in sorted(categories.items())
        if isinstance(value, (int, float)) and value >= 90
    ]

    logo_markup = '<div class="sw-brand-mark" aria-hidden="true"><svg viewBox="0 0 28 28"><rect x="1" y="1" width="26" height="26" fill="none" stroke="currentColor"/><path d="M7 21 L14 7 L21 21 Z" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M14 14 L14 21" stroke="currentColor" stroke-width="1.2"/></svg></div>'
    header_logo_markup = (
        f'<div class="sw-report-logo-wrap sw-report-head-logo"><img class="sw-report-logo" src="{brand_logo_uri}" alt="Shadewater Labs logo"></div>'
        if brand_logo_uri
        else ""
    )

    score_cards = []
    for key, value in sorted(categories.items()):
        score = int(value or 0)
        env_limited = key == "pagespeed" and isinstance(data.get("sections", {}).get(key), dict) and data["sections"][key].get("error")
        note = "Environment-limited" if env_limited else score_rating(score)
        tone = "env" if env_limited else "ok" if score >= 90 else "warn" if score >= 50 else "bad"
        score_value = "N/A" if env_limited else str(score)
        meter_width = 0 if env_limited else max(0, min(100, score))
        score_cards.append(
            f'<article class="sw-score-card{" env" if env_limited else ""}">'
            f'<div class="sw-score-card-head"><span>{html_lib.escape(key.replace("_", " ").title())}</span><span class="sw-badge {tone}">{html_lib.escape(note)}</span></div>'
            f'<div class="sw-score-num">{score_value}<span>/100</span></div>'
            f'<div class="sw-meter"><i style="width:{meter_width}%"></i></div>'
            f'</article>'
        )
    score_cards_html = "\n".join(score_cards) or '<p class="sw-muted">No category scores were generated.</p>'

    finding_rows = []
    quick_wins = []
    for idx, item in enumerate(findings, 1):
        severity = item.get("severity", "Info")
        source = item.get("source", "report")
        scope = item.get("provider_scope") or provider_scope_for_source(source)
        action = item.get("action_type") or action_type_for_finding(item)
        evidence_source = item.get("evidence_source") or evidence_source_for_source(source)
        confidence = item.get("confidence", "Confirmed")
        finding = item.get("finding", "Finding")
        evidence = item.get("evidence", "")
        fix = item.get("fix", "")
        severity_key = severity_class(severity)
        if severity != "Critical" and len(quick_wins) < 5:
            quick_wins.append({"id": f"F-{idx:02d}", "title": finding, "fix": fix, "severity": severity, "action": action})
        finding_rows.append(
            f'<tr data-severity="{html_lib.escape(severity_key, quote=True)}">'
            f"<td>F-{idx:02d}</td>"
            f"<td><span class=\"sw-badge {severity_key}\">{html_lib.escape(str(severity))}</span></td>"
            f"<td>{html_lib.escape(str(scope))}</td>"
            f"<td>{html_lib.escape(str(confidence))}</td>"
            f"<td>{html_lib.escape(str(action))}</td>"
            f"<td><strong>{html_lib.escape(str(finding))}</strong><details><summary>Evidence and fix</summary><p>{html_lib.escape(str(evidence))}</p><p><b>Evidence Source:</b> {html_lib.escape(str(evidence_source))}</p><p><b>Fix:</b> {html_lib.escape(str(fix))}</p></details></td>"
            "</tr>"
        )
    findings_html = "\n".join(finding_rows) or '<tr><td colspan="6">No verified findings were generated.</td></tr>'

    summary_groups_html = "\n".join(
        [
            render_summary_group(
                css_class="critical",
                icon="🚦",
                title="Critical Issues",
                count=len(critical_items),
                intro="Fix these first because they can block search visibility, indexing, or user experience.",
                items_html="\n".join(build_summary_item_html(item) for item in critical_items),
                empty_text="No critical issues were verified in this run.",
            ),
            render_summary_group(
                css_class="warning",
                icon="⚠️",
                title="Warnings",
                count=len(warning_items),
                intro="Important improvements that should be planned after any critical issues are handled.",
                items_html="\n".join(build_summary_item_html(item) for item in warning_items),
                empty_text="No warning-level items were verified in this run.",
            ),
            render_summary_group(
                css_class="info",
                icon="💡",
                title="Info / Opportunities",
                count=len(info_items),
                intro="Useful optimizations, AI-search enhancements, or cleanup work with lower urgency.",
                items_html="\n".join(build_summary_item_html(item) for item in info_items),
                empty_text="No informational opportunities were generated in this run.",
            ),
            render_summary_group(
                css_class="strong",
                icon="🌊",
                title="Strong Scores",
                count=len(strong_items),
                intro="These areas are performing well; preserve them when making site changes.",
                items_html="\n".join(build_summary_item_html(item) for item in strong_items),
                empty_text="No score category reached the strong-score threshold in this run.",
            ),
        ]
    )

    fix_sequence_items = findings[:8]
    fix_sequence_html = "\n".join(
        f"<li><strong>{html_lib.escape(str(item.get('finding', 'Finding')))}</strong><span>{html_lib.escape(str(item.get('fix', 'Review and resolve this item.')))}</span></li>"
        for item in fix_sequence_items
    ) or "<li><strong>No immediate implementation tasks.</strong><span>Keep monitoring and rerun after major site updates.</span></li>"

    quick_wins_html = "\n".join(
        f"<li><strong>{html_lib.escape(str(item['title']))}</strong><span>{html_lib.escape(str(item['fix']))}</span></li>"
        for item in quick_wins
    ) or "<li><strong>No critical issues verified.</strong><span>Keep monitoring and rerun with complete environment data.</span></li>"

    def render_action_card(item: dict[str, object]) -> str:
        task_text = (
            f"{item['id']}: {item['title']}\n"
            f"Fix: {item['fix']}\n"
            f"Severity: {item['severity']}\n"
            f"Action Type: {item['action']}\n"
            "Owner: SEO / Web"
        )
        return (
            f'<article class="sw-action-card" data-finding-id="{html_lib.escape(str(item["id"]), quote=True)}" '
            f'data-task-text="{html_lib.escape(task_text, quote=True)}">'
            f'<div><span class="sw-action-id">{html_lib.escape(str(item["id"]))}</span><h3>{html_lib.escape(str(item["title"]))}</h3></div>'
            f'<p>{html_lib.escape(str(item["fix"]))}</p>'
            f'<div class="sw-action-meta"><span>{html_lib.escape(str(item["severity"]))}</span><span>{html_lib.escape(str(item["action"]))}</span><span>Owner: SEO / Web</span></div>'
            f'<button class="sw-mini-btn" onclick="copyAction(this)">📋 Copy task</button>'
            f'</article>'
        )

    action_cards_html = "\n".join(render_action_card(item) for item in quick_wins) or '<p class="sw-muted">No immediate actions generated.</p>'

    limitations_html = "\n".join(
        f"<li>{html_lib.escape(str(item))}</li>" for item in limitations
    ) or "<li>No environment limitations were recorded.</li>"

    artifact_names = ["SEO-REPORT.html", "FULL-AUDIT-REPORT.md", "ACTION-PLAN.md", "CLAUDE-HANDOFF.md", "CODEX-HANDOFF.md", "seo-image-handoff.json"]
    artifact_descriptions = {
        "SEO-REPORT.html": "Interactive HTML dashboard",
        "FULL-AUDIT-REPORT.md": "Markdown audit details",
        "ACTION-PLAN.md": "Prioritized implementation tasks",
        "CLAUDE-HANDOFF.md": "Claude Code implementation handoff",
        "CODEX-HANDOFF.md": "Codex implementation handoff",
        "seo-image-handoff.json": "Structured image remediation handoff",
    }
    artifacts_html = "\n".join(
        f'<article class="sw-artifact"><span class="sw-file-icon">{html_lib.escape(name.rsplit(".", 1)[-1].upper())}</span><div><strong>{html_lib.escape(name)}</strong><p>{html_lib.escape(artifact_descriptions.get(name, "Generated audit artifact"))}</p></div></article>'
        for name in artifact_names
    )

    methodology_rows = []
    for key in sorted(data.get("sections", {}).keys()):
        section = data.get("sections", {}).get(key, {})
        status = "Environment-limited" if isinstance(section, dict) and section.get("error") else "Completed"
        methodology_rows.append(
            f"<tr><td>{html_lib.escape(key.replace('_', ' ').title())}</td><td>{html_lib.escape(status)}</td><td>{html_lib.escape(evidence_source_for_source(key))}</td></tr>"
        )
    methodology_html = "\n".join(methodology_rows)

    auditor_summary = build_executive_summary(
        findings=findings,
        critical_count=critical_count,
        warning_count=warning_count,
        info_count=info_count,
        overall=overall,
        rating=rating,
        next_move_fix=str(next_move_fix),
        limitations=limitations,
    )

    summary_text = (
        f"{report_title}\nURL: {url}\nScore: {overall}/100 ({rating})\n"
        f"Generated: {generated_label}\nEnvironment: {environment}\n\n"
        f"Findings: {len(findings)} total, {warning_count} warning, {info_count} info, {critical_count} critical."
    )
    score_text_lines = [
        f"- {category_label(key)}: {'N/A' if key == 'pagespeed' and isinstance(data.get('sections', {}).get(key), dict) and data['sections'][key].get('error') else value}/100"
        for key, value in sorted(categories.items())
    ] or ["- No category scores were generated."]
    finding_text_lines = [
        f"- F-{idx:02d} [{item.get('severity', 'Info')}] {item.get('finding', item.get('title', 'Finding'))}: {item.get('evidence', '')} Fix: {item.get('fix', '')}"
        for idx, item in enumerate(findings, start=1)
    ] or ["- No verified findings were generated."]
    action_text_lines = [
        f"- {item['id']} {item['title']}: {item['fix']}"
        for item in quick_wins
    ] or ["- No immediate action tasks were generated."]
    artifact_text_lines = [
        f"- {name}"
        for name in artifact_names
    ] or ["- No artifacts were listed."]
    report_text = (
        f"{summary_text}\n\n"
        "Auditor Summary\n"
        f"{auditor_summary}\n\n"
        "Recommended Next Move\n"
        f"{next_move_title}: {next_move_fix}\n\n"
        "Scores\n"
        + "\n".join(score_text_lines)
        + "\n\nFindings\n"
        + "\n".join(finding_text_lines)
        + "\n\nAction Plan\n"
        + "\n".join(action_text_lines)
        + "\n\nArtifacts\n"
        + "\n".join(artifact_text_lines)
    )
    handoff_artifact_paths = {
        "HTML dashboard": "SEO-REPORT.html",
        "Full audit report": "FULL-AUDIT-REPORT.md",
        "Action plan": "ACTION-PLAN.md",
        "Claude handoff": "CLAUDE-HANDOFF.md",
        "Codex handoff": "CODEX-HANDOFF.md",
        "Image handoff": "seo-image-handoff.json",
    }
    claude_handoff_text = build_agent_handoff_markdown(
        agent="Claude",
        data=data,
        scores=scores,
        findings_bundle=findings_bundle,
        artifact_paths=handoff_artifact_paths,
    )
    codex_handoff_text = build_agent_handoff_markdown(
        agent="Codex",
        data=data,
        scores=scores,
        findings_bundle=findings_bundle,
        artifact_paths=handoff_artifact_paths,
    )

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_lib.escape(report_title)} — {html_lib.escape(domain)}</title>
<style>
:root {{ color-scheme: dark; --bg:#061d27; --panel:#0b2730; --panel2:#102f37; --line:rgba(232,230,218,.14); --fg:#f4f0e7; --muted:#a9b7b4; --faint:#70827f; --accent:#234a7c; --accent2:#3d6fa6; --accent3:#86a7c8; --good:#84c398; --warn:#86a7c8; --bad:#d87561; --info:#79a8b3; --env:#9aa4a6; font-family: Geist, Inter, ui-sans-serif, system-ui, sans-serif; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:radial-gradient(circle at 80% 0%, rgba(35,74,124,.24), transparent 28%), radial-gradient(circle at 15% 100%, rgba(61,111,166,.12), transparent 30%), var(--bg); color:var(--fg); }} a {{ color:inherit; }} button {{ font:inherit; }}
.sw-topbar {{ display:flex; justify-content:space-between; gap:16px; padding:10px 24px; border-bottom:1px solid var(--line); color:var(--muted); font-size:12px; }} .mono {{ font-family:"Geist Mono", ui-monospace, monospace; }}
.sw-shell {{ max-width:1180px; margin:0 auto; padding:28px 22px 64px; }} .sw-masthead {{ border-bottom:1px solid var(--line); padding-bottom:24px; }}
.sw-report-logo-wrap {{ display:flex; justify-content:center; align-items:flex-end; padding:0; margin-bottom:-34px; }} .sw-report-head-logo {{ min-height:345px; }} .sw-report-logo {{ width:min(690px,100%); height:345px; object-fit:contain; object-position:center bottom; filter:drop-shadow(0 14px 28px rgba(35,74,124,.34)); }}
.sw-masthead-row {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-start; }} .sw-brand {{ display:flex; gap:12px; align-items:center; }} .sw-brand-mark,.sw-brand-img {{ width:36px; height:36px; display:grid; place-items:center; color:var(--accent); }} .sw-brand-img {{ object-fit:contain; }} .sw-brand-mark svg {{ width:28px; height:28px; }}
.sw-brand-name {{ font-size:12px; letter-spacing:.18em; font-weight:700; }} .sw-brand-sub {{ font-size:12px; color:var(--muted); margin-top:2px; }}
.sw-actions {{ display:flex; gap:8px; flex-wrap:wrap; }} .sw-btn {{ border:1px solid var(--line); background:var(--panel2); color:var(--fg); padding:9px 12px; border-radius:6px; cursor:pointer; }} .sw-btn.primary {{ background:linear-gradient(135deg,var(--accent2),var(--accent)); color:#f3f8ff; border-color:var(--accent2); font-weight:700; box-shadow:0 10px 24px rgba(35,74,124,.25); }}
.sw-report-head {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(520px,620px) 220px; gap:24px; margin-top:30px; align-items:end; }} .sw-report-title {{ min-width:0; display:grid; align-content:end; }} .sw-h1 {{ font-size:42px; line-height:1; margin:0 0 12px; letter-spacing:0; }} .sw-url-pill {{ display:inline-flex; width:fit-content; max-width:100%; align-items:center; gap:8px; color:#dbeafe; background:rgba(134,167,200,.14); border:1px solid rgba(134,167,200,.38); border-radius:8px; padding:8px 10px; font-size:14px; text-decoration:none; overflow-wrap:anywhere; word-break:break-word; }} .sw-url-pill::before {{ content:"URL"; color:var(--accent3); font-size:10px; font-weight:700; letter-spacing:.12em; }} .sw-url {{ color:inherit; }} .sw-meta-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-top:22px; }} .sw-meta-grid div {{ min-width:0; min-height:68px; border:1px solid var(--line); background:rgba(255,255,255,.035); padding:12px; border-radius:8px; }} dt {{ color:var(--faint); font-size:11px; text-transform:uppercase; letter-spacing:.08em; overflow-wrap:anywhere; }} dd {{ margin:3px 0 0; overflow-wrap:anywhere; }}
.sw-score-stack {{ display:grid; gap:12px; align-self:end; }} .sw-score {{ min-height:147px; display:grid; align-content:center; text-align:center; border:1px solid var(--line); background:rgba(255,255,255,.035); border-radius:8px; padding:14px; }} .sw-score.compact {{ min-height:112px; }} .sw-score.env {{ background:#16262b; }} .sw-score-kicker {{ color:var(--faint); font-size:11px; text-transform:uppercase; letter-spacing:.12em; margin-bottom:8px; }} .sw-score-big {{ font-size:64px; line-height:.9; color:var(--accent3); font-weight:700; text-shadow:0 12px 32px rgba(35,74,124,.35); }} .sw-score-big.small {{ font-size:44px; }} .sw-score-label {{ color:var(--muted); margin-top:8px; overflow-wrap:anywhere; font-size:13px; }} .sw-score-description {{ margin:8px 0 0; color:var(--faint); font-size:11px; line-height:1.35; }}
.sw-tabs {{ display:flex; overflow:auto; border:1px solid var(--line); border-radius:8px; margin:24px 0; position:sticky; top:0; z-index:5; backdrop-filter:blur(12px); }} .sw-tab {{ flex:1; min-width:130px; border:0; border-right:1px solid var(--line); background:#071f28; color:var(--muted); padding:12px; cursor:pointer; }} .sw-tab:last-child {{ border-right:0; }} .sw-tab.active {{ color:var(--fg); background:var(--panel2); box-shadow:inset 0 -2px var(--accent); }}
.sw-pane {{ display:none; }} .sw-pane.active {{ display:block; }} .sw-grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }} .sw-panel {{ border:1px solid var(--line); background:linear-gradient(180deg,var(--panel),#071e27); border-radius:8px; padding:18px; margin-bottom:18px; box-shadow:0 14px 36px rgba(0,0,0,.14); }} .sw-section-title {{ margin:0 0 14px; font-size:18px; }} .sw-muted {{ color:var(--muted); }}
.sw-next-move {{ display:grid; grid-template-columns:190px 1fr; gap:18px; align-items:center; border:1px solid rgba(134,167,200,.35); background:linear-gradient(135deg,rgba(35,74,124,.34),rgba(255,255,255,.03)); border-radius:8px; padding:16px; margin-bottom:18px; }} .sw-next-move h2 {{ margin:0 0 6px; font-size:18px; }} .sw-next-label {{ display:flex; align-items:center; gap:10px; color:var(--accent3); font-size:11px; text-transform:uppercase; letter-spacing:.1em; font-weight:700; line-height:1.25; align-self:center; }} .sw-next-emoji {{ display:grid; place-items:center; width:30px; height:30px; border:1px solid rgba(134,167,200,.35); border-radius:999px; background:rgba(134,167,200,.12); font-size:14px; letter-spacing:0; }} .sw-next-copy {{ display:block; max-width:118px; }} .sw-next-move p {{ margin:0; color:var(--muted); }}
.sw-legend {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:10px; margin-bottom:18px; }} .sw-legend div {{ border:1px solid var(--line); background:rgba(255,255,255,.035); border-radius:8px; padding:12px; color:var(--muted); }} .sw-legend strong {{ display:block; color:var(--fg); margin-bottom:3px; }}
.sw-summary-groups {{ display:grid; gap:14px; margin-bottom:18px; }} .sw-summary-group {{ border:1px solid var(--line); border-left:4px solid var(--accent2); background:linear-gradient(180deg,var(--panel),#071e27); border-radius:8px; padding:16px; box-shadow:0 14px 36px rgba(0,0,0,.14); }} .sw-summary-group.critical {{ border-left-color:var(--bad); }} .sw-summary-group.warning {{ border-left-color:var(--warn); }} .sw-summary-group.info {{ border-left-color:var(--info); }} .sw-summary-group.strong {{ border-left-color:var(--good); }} .sw-summary-group-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:12px; }} .sw-summary-group h2 {{ margin:0 0 4px; font-size:18px; }} .sw-summary-group-head p {{ margin:0; color:var(--muted); }} .sw-summary-count {{ display:grid; place-items:center; min-width:44px; height:44px; border:1px solid var(--line); border-radius:999px; color:var(--accent3); font-size:22px; font-weight:700; }} .sw-summary-list {{ list-style:none; padding:0; margin:0; display:grid; gap:10px; }} .sw-summary-item {{ display:grid; grid-template-columns:minmax(0,1fr) auto; gap:14px; border:1px solid var(--line); border-radius:8px; padding:12px; background:rgba(255,255,255,.025); }} .sw-summary-item p {{ margin:4px 0 0; color:var(--muted); }} .sw-summary-item.sw-empty {{ display:block; }} .sw-summary-chips {{ display:flex; flex-wrap:wrap; gap:6px; align-content:start; justify-content:flex-end; }} .sw-summary-chips span {{ border:1px solid rgba(134,167,200,.32); background:rgba(134,167,200,.09); color:var(--accent3); border-radius:999px; padding:4px 8px; font-size:11px; font-weight:700; white-space:nowrap; }}
.sw-qwins {{ list-style:none; padding:0; margin:0; display:grid; gap:10px; }} .sw-qwins li {{ border:1px solid var(--line); border-left:3px solid var(--accent); padding:12px; border-radius:6px; }} .sw-qwins span {{ display:block; color:var(--muted); font-size:13px; margin-top:2px; }}
.sw-badge {{ display:inline-flex; align-items:center; border:1px solid currentColor; border-radius:999px; padding:2px 8px; font-size:11px; font-weight:700; white-space:nowrap; }} .sw-badge.warning,.sw-badge.warn {{ color:var(--warn); }} .sw-badge.info {{ color:var(--info); }} .sw-badge.critical,.sw-badge.bad {{ color:var(--bad); }} .sw-badge.ok,.sw-badge.pass {{ color:var(--good); }} .sw-badge.env {{ color:var(--env); }}
.sw-filter-bar {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; justify-content:space-between; border:1px solid var(--line); background:rgba(255,255,255,.035); border-radius:8px; padding:10px; margin-bottom:12px; }} .sw-filter-group {{ display:flex; gap:8px; flex-wrap:wrap; }} .sw-filter-label {{ color:var(--faint); font-size:11px; text-transform:uppercase; letter-spacing:.12em; }} .sw-filter {{ border:1px solid var(--line); background:#071f28; color:var(--muted); border-radius:6px; padding:7px 10px; cursor:pointer; }} .sw-filter.active {{ background:var(--accent); border-color:var(--accent2); color:#f3f8ff; }} .sw-finding-search {{ min-width:220px; flex:1; border:1px solid var(--line); background:#071f28; color:var(--fg); border-radius:6px; padding:8px 10px; }} .sw-empty-row {{ display:none; color:var(--muted); padding:14px 2px; }}
.sw-table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:8px; }} table {{ width:100%; border-collapse:collapse; min-width:820px; }} th,td {{ text-align:left; padding:11px 12px; border-bottom:1px solid var(--line); vertical-align:top; }} th {{ color:var(--faint); font-size:11px; text-transform:uppercase; letter-spacing:.1em; background:#09242d; position:sticky; top:0; z-index:2; }} tr:hover td {{ background:rgba(35,74,124,.13); }} details {{ margin-top:6px; color:var(--muted); }} summary {{ cursor:pointer; color:var(--accent3); }} details[open] > summary {{ margin-bottom:6px; }}
.sw-score-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; }} .sw-score-card {{ border:1px solid var(--line); background:linear-gradient(180deg,var(--panel),rgba(11,39,48,.7)); border-radius:8px; padding:14px; }} .sw-score-card.env {{ background:#16262b; }} .sw-score-card-head {{ display:flex; justify-content:space-between; gap:8px; align-items:center; color:var(--muted); font-size:12px; }} .sw-score-num {{ font-size:34px; margin:14px 0 8px; }} .sw-score-num span {{ color:var(--faint); font-size:14px; }} .sw-meter {{ height:6px; background:#1d3a42; border-radius:99px; overflow:hidden; }} .sw-meter i {{ display:block; height:100%; background:linear-gradient(90deg,var(--accent2),var(--accent3)); }}
.sw-actions-list {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }} .sw-action-card {{ border:1px solid var(--line); background:linear-gradient(180deg,var(--panel),#071e27); border-radius:8px; padding:14px; display:grid; gap:10px; }} .sw-action-card h3 {{ margin:6px 0 0; font-size:16px; }} .sw-action-card p {{ margin:0; color:var(--muted); }} .sw-action-id {{ color:var(--accent3); font-size:11px; font-weight:700; }} .sw-action-meta {{ display:flex; gap:8px; flex-wrap:wrap; color:var(--faint); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }} .sw-mini-btn {{ justify-self:start; border:1px solid var(--line); background:var(--panel2); color:var(--fg); border-radius:6px; padding:7px 10px; cursor:pointer; }} .sw-artifacts {{ display:grid; gap:10px; }} .sw-artifact {{ display:grid; grid-template-columns:42px 1fr; gap:12px; align-items:center; border:1px solid var(--line); border-radius:8px; padding:12px; }} .sw-file-icon {{ width:42px; height:42px; display:grid; place-items:center; border:1px solid var(--line); border-radius:6px; color:var(--accent); font-size:11px; }}
.sw-footer {{ display:flex; justify-content:space-between; gap:12px; color:var(--faint); font-size:12px; border-top:1px solid var(--line); padding-top:18px; margin-top:28px; }}
@media (max-width:1200px) {{ .sw-report-head {{ grid-template-columns:minmax(0,1fr) minmax(360px,460px) 220px; }} .sw-report-logo {{ width:min(560px,100%); }} }}
@media (max-width:980px) {{ .sw-report-head {{ grid-template-columns:minmax(0,1fr) minmax(300px,420px); }} .sw-score-stack {{ grid-column:1 / -1; }} .sw-score {{ min-height:150px; }} }}
@media (max-width:820px) {{ .sw-masthead-row,.sw-grid-2,.sw-footer {{ flex-direction:column; display:flex; }} .sw-report-head {{ grid-template-columns:1fr; }} .sw-report-head-logo {{ order:-1; width:100%; min-height:300px; }} .sw-report-logo {{ width:min(560px,94vw); height:300px; }} .sw-meta-grid {{ grid-template-columns:1fr 1fr; }} .sw-summary-item {{ grid-template-columns:1fr; }} .sw-summary-chips {{ justify-content:flex-start; }} .sw-next-move {{ grid-template-columns:1fr; }} .sw-next-label {{ align-items:flex-start; }} .sw-next-copy {{ max-width:none; }} .sw-h1 {{ font-size:34px; }} }}
@media print {{ .sw-topbar,.sw-actions,.sw-tabs,.sw-filter-bar {{ display:none!important; }} .sw-report-logo {{ height:150px; }} .sw-pane {{ display:block!important; break-inside:avoid; }} details {{ display:block!important; }} details > * {{ display:block!important; }} body {{ background:white; color:black; }} .sw-panel,.sw-summary-group,.sw-summary-item,.sw-score-card,.sw-artifact,.sw-score,.sw-meta-grid div,.sw-legend div {{ background:white; color:black; border-color:#ccc; }} }}
</style></head><body>
<div class="sw-topbar"><span>Audit complete <span class="mono">· {html_lib.escape(run_id)}</span></span><span>Generated by SEO Skill</span></div>
<main class="sw-shell">
<header class="sw-masthead"><div class="sw-masthead-row"><div class="sw-brand">{logo_markup}<div><div class="sw-brand-name">SHADEWATER LABS</div><div class="sw-brand-sub">SEO Audit Suite · v3.4</div></div></div><div class="sw-actions"><button class="sw-btn" onclick="copyReport(this)">📋 Copy Report</button><button class="sw-btn" onclick="copyClaudeHandoff(this)">🤖 Claude Handoff</button><button class="sw-btn" onclick="copyCodexHandoff(this)">⚙️ Codex Handoff</button><button class="sw-btn" onclick="window.print()">🖨️ Print</button><button class="sw-btn primary" onclick="downloadPdf()">⬇️ Download PDF</button></div></div>
<div class="sw-report-head"><div class="sw-report-title"><h1 class="sw-h1">{html_lib.escape(report_title)}</h1><a class="sw-url sw-url-pill mono" href="{html_lib.escape(url, quote=True)}">{html_lib.escape(url)}</a><dl class="sw-meta-grid"><div><dt>Generated</dt><dd>{html_lib.escape(generated_label)}</dd></div><div><dt>Environment</dt><dd>{html_lib.escape(str(environment))}</dd></div><div><dt>Run ID</dt><dd>{html_lib.escape(run_id)}</dd></div><div><dt>Domain</dt><dd>{html_lib.escape(domain)}</dd></div></dl></div>{header_logo_markup}<div class="sw-score-stack"><aside class="sw-score"><div class="sw-score-kicker">Overall Score</div><div class="sw-score-big">{overall}</div><div class="sw-score-label">OVERALL · {html_lib.escape(rating)}</div><p class="sw-score-description">Full audit score across technical SEO, content, AI readiness, and site health.</p></aside><aside class="sw-score compact{speed_card_class}"><div class="sw-score-kicker">Speed Insights</div><div class="sw-score-big small">{html_lib.escape(speed_value)}</div><div class="sw-score-label">PAGESPEED · {html_lib.escape(speed_rating)}</div><p class="sw-score-description">Google PageSpeed mobile performance score for Core Web Vitals context.</p></aside></div></div></header>
<nav class="sw-tabs"><button class="sw-tab active" data-tab="summary" onclick="showTab('summary')">📊 Summary</button><button class="sw-tab" data-tab="findings" onclick="showTab('findings')">🔎 Findings</button><button class="sw-tab" data-tab="scores" onclick="showTab('scores')">📈 Scores</button><button class="sw-tab" data-tab="actions" onclick="showTab('actions')">✅ Actions</button><button class="sw-tab" data-tab="artifacts" onclick="showTab('artifacts')">📁 Artifacts</button><button class="sw-tab" data-tab="methodology" onclick="showTab('methodology')">🧪 Methodology</button></nav>
<section id="summary" class="sw-pane active"><section class="sw-next-move"><div class="sw-next-label"><span class="sw-next-emoji">🎯</span><span class="sw-next-copy">Recommended Next Move</span></div><div><h2>{html_lib.escape(str(next_move_title))}</h2><p>{html_lib.escape(str(next_move_fix))}</p></div></section><section class="sw-panel"><h2 class="sw-section-title">🧭 How to read this report</h2><div class="sw-legend"><div><strong>🚦 Critical</strong>Fix first; may block visibility, indexing, or user trust.</div><div><strong>⚠️ Warning</strong>Important, but usually schedulable after critical work.</div><div><strong>💡 Info</strong>Opportunity or AI-search enhancement with lower urgency.</div><div><strong>🌊 Strong</strong>Already healthy; preserve during future changes.</div></div></section><section class="sw-panel"><h2 class="sw-section-title">📝 Auditor summary</h2><p class="sw-muted" id="sw-auditor-summary">{html_lib.escape(auditor_summary)}</p></section><section class="sw-panel"><h2 class="sw-section-title">✅ Fix sequence</h2><ol class="sw-qwins">{fix_sequence_html}</ol></section><div class="sw-summary-groups">{summary_groups_html}</div><section class="sw-panel"><h2 class="sw-section-title">🧭 Environment / tool limitations</h2><ul class="sw-qwins">{limitations_html}</ul></section></section>
<section id="findings" class="sw-pane"><div class="sw-filter-bar"><input id="sw-finding-search" class="sw-finding-search" type="search" placeholder="🔍 Search findings, evidence, fixes" oninput="searchFindings(this.value)"><div class="sw-filter-group"><button class="sw-filter active" data-severity-filter="all" data-count="{len(findings)}" onclick="filterFindings('all')">All · {len(findings)}</button><button class="sw-filter" data-severity-filter="critical" data-count="{critical_count}" onclick="filterFindings('critical')">Critical · {critical_count}</button><button class="sw-filter" data-severity-filter="warning" data-count="{warning_count}" onclick="filterFindings('warning')">Warning · {warning_count}</button><button class="sw-filter" data-severity-filter="info" data-count="{info_count}" onclick="filterFindings('info')">Info · {info_count}</button><button class="sw-filter" type="button" onclick="toggleEvidence(true)">🔎 Expand Evidence</button><button class="sw-filter" type="button" onclick="toggleEvidence(false)">Collapse</button></div></div><div class="sw-empty-row" id="sw-empty-findings">No findings match this filter.</div><div class="sw-table-wrap"><table><thead><tr><th>ID</th><th>Severity</th><th>Provider Scope</th><th>Confidence</th><th>Action Type</th><th>Finding / Evidence Source</th></tr></thead><tbody>{findings_html}</tbody></table></div></section>
<section id="scores" class="sw-pane"><div class="sw-score-grid">{score_cards_html}</div></section>
<section id="actions" class="sw-pane"><section class="sw-panel"><h2 class="sw-section-title">Prioritized action plan</h2><div class="sw-actions-list">{action_cards_html}</div></section></section>
<section id="artifacts" class="sw-pane"><div class="sw-artifacts">{artifacts_html}</div></section>
<section id="methodology" class="sw-pane"><div class="sw-table-wrap"><table><thead><tr><th>Check</th><th>Status</th><th>Evidence Source</th></tr></thead><tbody>{methodology_html}</tbody></table></div></section>
<footer class="sw-footer"><span>Shadewater Labs · Confidential</span><span class="mono">{html_lib.escape(run_id)} · {html_lib.escape(generated_label)}</span></footer>
</main>
<script>
const SUMMARY_TEXT = {json.dumps(summary_text)};
const REPORT_TEXT = {json.dumps(report_text)};
const AUDITOR_SUMMARY = {json.dumps(auditor_summary)};
const CLAUDE_HANDOFF_TEXT = {json.dumps(claude_handoff_text)};
const CODEX_HANDOFF_TEXT = {json.dumps(codex_handoff_text)};
function showTab(id) {{ document.querySelectorAll('.sw-pane').forEach(el => el.classList.toggle('active', el.id === id)); document.querySelectorAll('.sw-tab').forEach(el => el.classList.toggle('active', el.dataset.tab === id)); }}
let ACTIVE_SEVERITY = 'all';
let FINDING_QUERY = '';
let detailsOpenedForPrint = [];
function updateFindingVisibility() {{ let shown = 0; document.querySelectorAll('#findings tbody tr[data-severity]').forEach(row => {{ const text = row.innerText.toLowerCase(); const severityMatch = ACTIVE_SEVERITY === 'all' || row.dataset.severity === ACTIVE_SEVERITY; const queryMatch = !FINDING_QUERY || text.includes(FINDING_QUERY); const visible = severityMatch && queryMatch; row.hidden = !visible; if (visible) shown += 1; }}); const empty = document.getElementById('sw-empty-findings'); if (empty) empty.style.display = shown ? 'none' : 'block'; }}
function filterFindings(severity) {{ ACTIVE_SEVERITY = severity; document.querySelectorAll('.sw-filter[data-severity-filter]').forEach(el => el.classList.toggle('active', el.dataset.severityFilter === severity)); updateFindingVisibility(); }}
function searchFindings(value) {{ FINDING_QUERY = String(value || '').trim().toLowerCase(); updateFindingVisibility(); }}
function toggleEvidence(open) {{ document.querySelectorAll('#findings details').forEach(el => el.open = open); }}
function copyText(button, text, label) {{ const done = () => {{ if (button) {{ button.textContent = 'Copied'; setTimeout(() => button.textContent = label, 1200); }} }}; if (navigator.clipboard && window.isSecureContext) {{ navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done)); }} else {{ fallbackCopy(text, done); }} }}
function fallbackCopy(text, done) {{ const box = document.createElement('textarea'); box.value = text; box.setAttribute('readonly', ''); box.style.position = 'fixed'; box.style.opacity = '0'; document.body.appendChild(box); box.select(); try {{ document.execCommand('copy'); }} finally {{ document.body.removeChild(box); done(); }} }}
function copyAction(button) {{ const card = button.closest('.sw-action-card'); if (!card) return; copyText(button, card.dataset.taskText || card.innerText.trim(), '📋 Copy task'); }}
function copyReport(button) {{ copyText(button, REPORT_TEXT, '📋 Copy Report'); }}
function copyClaudeHandoff(button) {{ copyText(button, CLAUDE_HANDOFF_TEXT, '🤖 Claude Handoff'); }}
function copyCodexHandoff(button) {{ copyText(button, CODEX_HANDOFF_TEXT, '⚙️ Codex Handoff'); }}
function copySummary(button) {{ copyText(button, SUMMARY_TEXT, '📋 Copy Summary'); }}
function prepareForPrint() {{ detailsOpenedForPrint = []; document.querySelectorAll('details').forEach((el, index) => {{ if (!el.open) {{ detailsOpenedForPrint.push(index); el.open = true; }} }}); }}
function restoreAfterPrint() {{ document.querySelectorAll('details').forEach((el, index) => {{ if (detailsOpenedForPrint.includes(index)) el.open = false; }}); detailsOpenedForPrint = []; }}
function downloadPdf() {{ const oldTitle = document.title; prepareForPrint(); document.title = "{pdf_filename}"; window.print(); setTimeout(() => document.title = oldTitle, 250); }}
window.addEventListener('beforeprint', prepareForPrint);
window.addEventListener('afterprint', restoreAfterPrint);
</script></body></html>'''


def generate_html(
    data: dict,
    scores: dict,
    theme_name: str = "shadewater",
    brand_logo_uri: str | None = None,
) -> str:
    """Generate the interactive HTML report."""
    if theme_name == "shadewater":
        return generate_shadewater_dashboard_html(data, scores, brand_logo_uri=brand_logo_uri)

    domain = data["domain"]
    url = data["url"]
    timestamp = data["timestamp"]
    theme = resolve_report_theme(theme_name)
    font_links = theme["font_links"]

    def _esc(value: object) -> str:
        # Everything below that came from the audited site is untrusted. The
        # shadewater dashboard already escapes; this branch did not.
        return html_lib.escape(str(value), quote=True)

    title_prefix = html_lib.escape(theme["title_prefix"], quote=True)
    report_title = html_lib.escape(theme["display_name"], quote=True)
    title_lines = theme.get("title_lines") or [theme["display_name"]]
    report_eyebrow = html_lib.escape(theme["eyebrow"], quote=True)
    report_tagline = html_lib.escape(theme["tagline"], quote=True)
    footer_theme_name = html_lib.escape(theme.get("footer_theme_name", f"{theme_name.title()} Theme"), quote=True)
    hero_eyebrow_markup = f'<div class="hero-eyebrow">{report_eyebrow}</div>' if report_eyebrow else ""
    hero_brand_markup = (
        f'<img class="hero-brand-mark hero-bridge-mark" src="{brand_logo_uri}" alt="{html_lib.escape(theme["brand_logo_alt"], quote=True)}" />'
        if brand_logo_uri
        else ""
    )
    hero_tagline_markup = f'<p class="hero-tagline">{report_tagline}</p>' if report_tagline else ""
    hero_title_lines_markup = "".join(
        f'<span class="hero-title-line">{html_lib.escape(str(line), quote=True)}</span>'
        for line in title_lines
        if str(line).strip()
    )
    pdf_filename = html_lib.escape(
        f"{re.sub(r'[^a-z0-9]+', '-', domain.lower()).strip('-') or 'seo-report'}-seo-report.pdf",
        quote=True,
    )
    overall = scores["overall"]

    # Determine overall grade
    if overall >= 90:
        grade, grade_color = "A+", "#22c55e"
    elif overall >= 80:
        grade, grade_color = "A", "#22c55e"
    elif overall >= 70:
        grade, grade_color = "B", "#eab308"
    elif overall >= 60:
        grade, grade_color = "C", "#f97316"
    elif overall >= 50:
        grade, grade_color = "D", "#ef4444"
    else:
        grade, grade_color = "F", "#dc2626"

    # Collect all issues
    all_issues = []
    for section_name, section_data in data["sections"].items():
        issues = section_data.get("issues", [])
        for issue in issues:
            if isinstance(issue, dict):
                # Structured issue from entity_checker, hreflang_checker, etc.
                sev_raw = issue.get("severity", "info").lower()
                severity_map = {"critical": "critical", "high": "critical", "warning": "warning", "medium": "warning", "info": "info", "low": "info"}
                severity = severity_map.get(sev_raw, "info")
                text = f"{issue.get('finding', '')} — Fix: {issue.get('fix', '')}" if issue.get('fix') else issue.get('finding', str(issue))
                all_issues.append({"text": text, "severity": severity, "section": section_name})
            elif isinstance(issue, str):
                severity = "critical" if "🔴" in issue else "warning" if "⚠️" in issue else "info"
                all_issues.append({"text": issue, "severity": severity, "section": section_name})

    critical_count = sum(1 for i in all_issues if i["severity"] == "critical")
    warning_count = sum(1 for i in all_issues if i["severity"] == "warning")
    pass_count = sum(1 for i in all_issues if i["severity"] == "info")

    # Section data extraction
    sec = data["sections"].get("security", {})
    soc = data["sections"].get("social", {})
    rob = data["sections"].get("robots", {})
    bl = data["sections"].get("broken_links", {})
    il = data["sections"].get("internal_links", {})
    red = data["sections"].get("redirects", {})
    llm = data["sections"].get("llms_txt", {})
    psi = data["sections"].get("pagespeed", {})
    op = data["sections"].get("onpage", {})
    rd = data["sections"].get("readability", {})
    art = data["sections"].get("article", {})
    ent = data["sections"].get("entity", {})
    lp = data["sections"].get("link_profile", {})
    hf = data["sections"].get("hreflang", {})
    dc = data["sections"].get("duplicate_content", {})
    env = data.get("environment", {})
    env_fixes = data.get("environment_fixes", [])

    env_primary = html_lib.escape(env.get("primary", "Unknown"), quote=True)
    env_runtime = html_lib.escape(env.get("runtime", "Unknown"), quote=True)
    env_confidence = html_lib.escape(env.get("confidence", "low").upper(), quote=True)
    env_alts = [html_lib.escape(x, quote=True) for x in env.get("alternatives", [])]
    env_signals_html = "".join(
        f'<li class="mono" style="margin:4px 0;">{html_lib.escape(sig, quote=True)}</li>'
        for sig in env.get("signals", [])
    ) or '<li style="color:var(--text-muted)">No strong platform markers found.</li>'
    env_fixes_html = render_environment_fixes(env_fixes)

    # Build issues HTML
    issues_html = ""
    for issue in sorted(all_issues, key=lambda x: {"critical": 0, "warning": 1, "info": 2}[x["severity"]]):
        badge_class = issue["severity"]
        issues_html += f'<div class="issue-item {badge_class}"><span class="issue-badge">{badge_class.upper()}</span> {_esc(issue["text"])}</div>\n'

    # Build category cards
    category_labels = {
        "security": ("🔒", "Security Headers"),
        "social": ("📱", "Social Meta"),
        "robots": ("🤖", "Robots & Crawlers"),
        "broken_links": ("🔗", "Broken Links"),
        "internal_links": ("🕸️", "Internal Links"),
        "redirects": ("↪️", "Redirects"),
        "llms_txt": ("🧠", "AI Search (llms.txt)"),
        "pagespeed": ("⚡", "Performance (CWV)"),
        "onpage": ("📝", "On-Page SEO"),
        "readability": ("📖", "Readability"),
        "article": ("📄", "Article Extractor"),
        "entity": ("🏛️", "Entity SEO"),
        "link_profile": ("🔗", "Link Profile"),
        "hreflang": ("🌍", "Hreflang"),
        "duplicate_content": ("📋", "Content Uniqueness"),
    }

    category_cards = ""
    for key, (icon, label) in category_labels.items():
        score = scores["categories"].get(key, 0)
        if score is None:
            score = 0
        if score >= 80:
            ring_color = theme["positive"]
        elif score >= 50:
            ring_color = theme["warning"]
        else:
            ring_color = theme["danger"]
        dash = round(score * 2.51327, 1)  # circumference = 251.327
        category_cards += f'''
        <div class="category-card" onclick="scrollToSection('{key}')">
            <svg class="ring" viewBox="0 0 90 90">
                <circle cx="45" cy="45" r="40" fill="none" stroke="var(--card-border)" stroke-width="6"/>
                <circle cx="45" cy="45" r="40" fill="none" stroke="{ring_color}" stroke-width="6"
                    stroke-dasharray="{dash} 251.327" stroke-linecap="round"
                    transform="rotate(-90 45 45)" class="ring-progress"/>
            </svg>
            <div class="ring-label">{score}</div>
            <div class="category-icon">{icon}</div>
            <div class="category-name">{label}</div>
        </div>'''

    # Security details
    security_rows = ""
    for header, value in sec.get("headers_present", {}).items():
        security_rows += f'<tr><td>{_esc(header)}</td><td><span class="badge pass">Present</span></td><td class="mono">{_esc(value[:60])}</td></tr>'
    for header, desc in sec.get("headers_missing", {}).items():
        security_rows += f'<tr><td>{_esc(header)}</td><td><span class="badge critical">Missing</span></td><td>{_esc(desc)}</td></tr>'

    # Social meta details
    social_rows = ""
    og = soc.get("og_tags", {})
    tw = soc.get("twitter_tags", {})
    for tag in ["og:title", "og:description", "og:image", "og:url", "og:type", "og:site_name"]:
        val = og.get(tag, "")
        status = '<span class="badge pass">✅</span>' if val else '<span class="badge critical">Missing</span>'
        social_rows += f'<tr><td>{_esc(tag)}</td><td>{status}</td><td>{_esc(val[:60]) if val else "—"}</td></tr>'
    for tag in ["twitter:card", "twitter:title", "twitter:description", "twitter:image", "twitter:site"]:
        val = tw.get(tag, "")
        status = '<span class="badge pass">✅</span>' if val else '<span class="badge warning">Missing</span>'
        social_rows += f'<tr><td>{_esc(tag)}</td><td>{status}</td><td>{_esc(val[:60]) if val else "—"}</td></tr>'

    # AI Crawlers details
    ai_rows = ""
    for crawler, status in rob.get("ai_crawler_status", {}).items():
        if "blocked" in status:
            badge = '<span class="badge pass">Blocked</span>'
        elif "not managed" in status:
            badge = '<span class="badge warning">Unmanaged</span>'
        else:
            badge = '<span class="badge info">Info</span>'
        ai_rows += f'<tr><td>{_esc(crawler)}</td><td>{badge}</td><td>{_esc(status)}</td></tr>'

    # Broken links details
    broken_rows = ""
    for link in bl.get("broken", [])[:20]:
        status = link.get("status") or link.get("error", "?")
        loc = "Internal" if link.get("is_internal") else "External"
        broken_rows += f'<tr><td><span class="badge {"critical" if link.get("is_internal") else "warning"}">{loc}</span></td><td class="mono">{_esc(status)}</td><td class="link-url">{_esc(link["url"][:80])}</td><td>{_esc(link.get("anchor_text", "")[:40])}</td></tr>'
    for link in bl.get("blocked", [])[:20]:
        status = link.get("status") or link.get("error", "?")
        broken_rows += f'<tr><td><span class="badge info">External</span></td><td class="mono">{_esc(status)} blocked</td><td class="link-url">{_esc(link["url"][:80])}</td><td>{_esc(link.get("anchor_text", "")[:40])}</td></tr>'

    bl_summary = bl.get("summary", {})
    bl_total = bl_summary.get("total", 0)
    bl_healthy = bl_summary.get("healthy", 0)
    bl_broken = bl_summary.get("broken", 0)
    bl_blocked = bl_summary.get("blocked", 0)

    # Internal links details
    orphan_rows = ""
    for orphan in il.get("orphan_candidates", [])[:15]:
        orphan_rows += f'<tr><td class="link-url">{_esc(orphan["url"][:80])}</td><td>{orphan["incoming_links"]}</td></tr>'

    il_pages = il.get("pages_crawled", 0)
    il_total = il.get("total_internal_links", 0)
    il_dist = il.get("link_distribution", {})

    # Redirect details
    redirect_rows = ""
    for hop in red.get("chain", []):
        status = hop.get("status", "?")
        time_ms = hop.get("time_ms", 0)
        if hop.get("final"):
            icon_c = "pass" if 200 <= status < 300 else "critical"
            redirect_rows += f'<tr><td>{hop["step"]}</td><td><span class="badge {icon_c}">{status}</span></td><td class="link-url">{_esc(hop["url"][:80])}</td><td>{time_ms}ms</td><td>FINAL</td></tr>'
        else:
            redirect_rows += f'<tr><td>{hop["step"]}</td><td><span class="badge warning">{status}</span></td><td class="link-url">{_esc(hop["url"][:80])}</td><td>{time_ms}ms</td><td>{_esc(hop.get("redirect_type", ""))}</td></tr>'

    # Anchor text chart data
    anchor_data = il.get("anchor_texts", {})
    anchor_items = list(anchor_data.items())[:10]
    anchor_bars = ""
    if anchor_items:
        max_val = max(v for _, v in anchor_items) if anchor_items else 1
        for text, count in anchor_items:
            pct = round(count / max_val * 100)
            anchor_bars += f'<div class="bar-row"><span class="bar-label">{_esc(text[:25])}</span><div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div><span class="bar-value">{count}</span></div>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_prefix} — {_esc(domain)}</title>
<style>
:root {{
    color-scheme: dark;
    --bg: {theme["bg"]};
    --surface: {theme["surface"]};
    --surface-elevated: {theme["surface_elevated"]};
    --card: {theme["card"]};
    --card-border: {theme["card_border"]};
    --text: {theme["text"]};
    --text-muted: {theme["text_muted"]};
    --accent: {theme["accent"]};
    --accent-strong: {theme["accent_2"]};
    --accent-glow: {theme["accent_glow"]};
    --green: {theme["positive"]};
    --yellow: {theme["warning"]};
    --red: {theme["danger"]};
    --orange: {theme["orange"]};
    --info: {theme["info"]};
    --radius: 30px;
    --radius-sm: 20px;
    --font-ui: {theme["font_ui"]};
    --font-display: {theme["font_display"]};
    --font-body: {theme["font_body"]};
    --hero-gradient: {theme["hero_gradient"]};
    --hero-domain: {theme["hero_domain"]};
    --hero-timestamp: {theme["hero_timestamp"]};
}}
[data-theme="light"] {{
    color-scheme: light;
    --bg: {theme["light_bg"]};
    --surface: {theme["light_surface"]};
    --surface-elevated: {theme["light_surface_elevated"]};
    --card: {theme["light_card"]};
    --card-border: {theme["light_card_border"]};
    --text: {theme["light_text"]};
    --text-muted: {theme["light_text_muted"]};
    --accent-glow: {theme["light_accent_glow"]};
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
    font-family: var(--font-ui);
    background:
        radial-gradient(circle at top right, color-mix(in srgb, var(--accent-strong) 24%, transparent) 0%, transparent 28%),
        radial-gradient(circle at bottom left, color-mix(in srgb, var(--accent) 18%, transparent) 0%, transparent 32%),
        linear-gradient(180deg, var(--bg), color-mix(in srgb, var(--bg) 88%, #000 12%) 100%);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
}}
body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(circle at 20% 20%, rgba(255,255,255,0.035), transparent 22%),
        radial-gradient(circle at 80% 12%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 20%);
    pointer-events: none;
}}
.container {{ max-width: 1280px; margin: 0 auto; padding: 24px; position: relative; z-index: 1; }}

/* Fixed controls */
.top-controls {{
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 100;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.report-download,
.theme-toggle {{
    appearance: none;
    border: 1px solid var(--card-border);
    background: var(--surface);
    color: var(--text);
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}}
.report-download {{
    border-radius: 999px;
    padding: 0 18px;
    height: 46px;
    font-family: var(--font-ui);
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.3s;
}}
.report-download:hover,
.theme-toggle:hover {{
    transform: translateY(-2px) scale(1.02);
    border-color: var(--accent);
}}

/* Header */
.header {{
    padding: 28px 0 18px;
    position: relative;
}}
.hero-shell {{
    background: var(--hero-gradient);
    border: 2px solid var(--card-border);
    border-radius: 40px;
    padding: 38px 36px;
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(150px, 210px) minmax(260px, 0.68fr);
    gap: 18px;
    align-items: center;
    overflow: hidden;
    position: relative;
    box-shadow: 0 24px 56px rgba(0, 0, 0, 0.28);
}}
.hero-shell::before {{
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at top right, rgba(255,255,255,0.1), transparent 28%),
        radial-gradient(circle at bottom left, color-mix(in srgb, var(--accent-strong) 18%, transparent), transparent 35%);
    pointer-events: none;
}}
.hero-copy,
.hero-meta,
.hero-bridge-mark {{
    position: relative;
    z-index: 1;
}}
.hero-copy {{
    min-width: 0;
    max-width: 760px;
}}
.hero-eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.14);
    background: rgba(255,255,255,0.06);
    padding: 8px 14px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--hero-domain);
}}
.hero-title-block {{
    margin-top: 18px;
}}
.hero-title-row {{
    display: block;
}}
.hero-title-copy {{
    min-width: 0;
}}
.hero-brand-mark {{
    width: auto;
    height: 162px;
    max-width: min(30vw, 220px);
    object-fit: contain;
    filter: drop-shadow(0 12px 24px rgba(0, 0, 0, 0.22));
    flex: 0 0 auto;
}}
.hero-bridge-mark {{
    align-self: center;
    justify-self: center;
    margin-inline: -10px 2px;
    transform: translateX(-22px);
}}
.hero-title-row h1 {{
    font-family: var(--font-display);
    font-size: clamp(2.8rem, 5vw, 4.8rem);
    line-height: 0.92;
    font-weight: 700;
    color: var(--text);
    margin: 0;
}}
.hero-title-line {{
    display: block;
}}
.hero-tagline {{
    margin-top: 18px;
    max-width: 46rem;
    font-size: 1.06rem;
    color: var(--hero-domain);
}}
.header .domain {{
    margin-top: 14px;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--hero-domain);
}}
.header .timestamp {{
    margin-top: 14px;
    font-size: 0.84rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--hero-timestamp);
}}
.hero-meta {{
    display: grid;
    gap: 14px;
    align-content: center;
}}
.hero-meta-card {{
    border-radius: 26px;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(4, 18, 31, 0.34);
    padding: 18px;
    backdrop-filter: blur(10px);
}}
.hero-meta-label {{
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--hero-timestamp);
}}
.hero-meta-value {{
    margin-top: 6px;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text);
}}
.hero-meta-detail {{
    margin-top: 6px;
    font-size: 0.95rem;
    color: var(--hero-domain);
}}
@keyframes pulse {{ 0%,100% {{ opacity: 0.7; }} 50% {{ opacity: 1; }} }}

/* Theme Toggle */
.theme-toggle {{
    border-radius: 999px; width: 46px; height: 46px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; font-size: 1.2rem; transition: all 0.3s;
}}

/* Overall Score */
.score-hero {{
    display: flex; justify-content: center; align-items: center;
    gap: 48px; padding: 34px 32px; flex-wrap: wrap;
    margin: -18px 0 10px;
    background: var(--surface);
    border: 2px solid var(--card-border);
    border-radius: 34px;
    box-shadow: 0 18px 45px rgba(0, 0, 0, 0.22);
    backdrop-filter: blur(10px);
}}
.score-gauge {{ position: relative; width: 180px; height: 180px; }}
.score-gauge svg {{ width: 100%; height: 100%; }}
.score-gauge .gauge-value {{
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    text-align: center;
}}
.score-gauge .gauge-number {{
    font-family: var(--font-display);
    font-size: 3.5rem;
    font-weight: 700;
    line-height: 0.9;
    color: {grade_color};
}}
.score-gauge .gauge-grade {{ font-size: 1rem; color: var(--text-muted); }}
.score-stats {{ display: flex; gap: 24px; }}
.stat-card {{
    background: linear-gradient(160deg, var(--surface-elevated), var(--card));
    border: 1px solid var(--card-border);
    border-radius: 22px; padding: 20px 28px; text-align: center;
    min-width: 100px;
}}
.stat-value {{ font-size: 2rem; font-weight: 700; }}
.stat-label {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }}
.stat-critical .stat-value {{ color: var(--red); }}
.stat-warning .stat-value {{ color: var(--yellow); }}
.stat-pass .stat-value {{ color: var(--green); }}

/* Category Cards Grid */
.categories {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; margin: 32px 0; }}
.category-card {{
    background: linear-gradient(160deg, var(--surface), var(--card));
    border: 1px solid var(--card-border);
    border-radius: 26px; padding: 20px; text-align: center;
    cursor: pointer; transition: all 0.3s;
    position: relative;
}}
.category-card:hover {{ transform: translateY(-4px); box-shadow: 0 14px 28px var(--accent-glow); border-color: var(--accent); }}
.category-card .ring {{ width: 70px; height: 70px; margin: 0 auto 8px; }}
.category-card .ring-label {{
    position: absolute; top: 52px; left: 50%; transform: translate(-50%, -50%);
    font-size: 1.1rem; font-weight: 700;
}}
.ring-progress {{ transition: stroke-dasharray 1s ease; }}
.category-icon {{ font-size: 1.3rem; margin: 4px 0; }}
.category-name {{ font-size: 0.8rem; color: var(--text-muted); font-weight: 500; }}

/* Sections */
.section {{
    background: linear-gradient(180deg, var(--surface), var(--card));
    border: 1px solid var(--card-border);
    border-radius: 28px; margin: 24px 0; overflow: hidden;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.16);
}}
.section-header {{
    padding: 20px 24px; cursor: pointer; display: flex;
    align-items: center; justify-content: space-between;
    transition: background 0.2s;
}}
.section-header:hover {{ background: color-mix(in srgb, var(--accent) 8%, transparent); }}
.section-header h2 {{ font-size: 1.15rem; font-weight: 600; display: flex; align-items: center; gap: 10px; }}
.section-header .chevron {{ transition: transform 0.3s; font-size: 1.2rem; color: var(--text-muted); }}
.section-header .chevron.open {{ transform: rotate(180deg); }}
.section-body {{ padding: 0 24px 24px; display: none; }}
.section-body.open {{ display: block; animation: fadeIn 0.3s; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(-8px); }} to {{ opacity: 1; transform: translateY(0); }} }}

/* Tables */
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.9rem; }}
th {{ text-align: left; padding: 10px 12px; border-bottom: 2px solid var(--card-border); color: var(--text-muted); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; }}
td {{ padding: 10px 12px; border-bottom: 1px solid var(--card-border); vertical-align: top; }}
tr:last-child td {{ border-bottom: none; }}
tr:hover td {{ background: color-mix(in srgb, var(--accent) 7%, transparent); }}
.mono {{ font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.85rem; }}
.link-url {{ word-break: break-all; max-width: 400px; color: var(--accent); }}

/* Badges */
.badge {{
    display: inline-block; padding: 2px 10px; border-radius: 100px;
    font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
}}
.badge.critical {{ background: color-mix(in srgb, var(--red) 18%, transparent); color: var(--red); }}
.badge.warning {{ background: color-mix(in srgb, var(--yellow) 16%, transparent); color: var(--yellow); }}
.badge.pass {{ background: color-mix(in srgb, var(--green) 18%, transparent); color: var(--green); }}
.badge.info {{ background: color-mix(in srgb, var(--info) 18%, transparent); color: var(--info); }}

/* Issues */
.issue-item {{
    padding: 12px 16px; border-radius: 8px; margin: 6px 0;
    font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px;
}}
.issue-item.critical {{ background: color-mix(in srgb, var(--red) 10%, transparent); border-left: 3px solid var(--red); }}
.issue-item.warning {{ background: color-mix(in srgb, var(--yellow) 10%, transparent); border-left: 3px solid var(--yellow); }}
.issue-item.info {{ background: color-mix(in srgb, var(--info) 10%, transparent); border-left: 3px solid var(--info); }}
.issue-badge {{ flex-shrink: 0; }}

/* Bar Chart */
.bar-row {{ display: flex; align-items: center; gap: 10px; margin: 6px 0; }}
.bar-label {{ width: 150px; font-size: 0.85rem; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-muted); }}
.bar-track {{ flex: 1; height: 22px; background: color-mix(in srgb, var(--card-border) 90%, transparent); border-radius: 999px; overflow: hidden; }}
.bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--accent-strong), var(--accent)); border-radius: 999px; transition: width 1s ease; }}
.bar-value {{ width: 30px; font-size: 0.85rem; font-weight: 600; }}

/* Summary cards row */
.summary-row {{ display: flex; gap: 16px; margin: 16px 0; flex-wrap: wrap; }}
.summary-item {{
    flex: 1; min-width: 120px; background: color-mix(in srgb, var(--surface-elevated) 86%, transparent);
    border: 1px solid var(--card-border);
    border-radius: 22px;
    padding: 16px; text-align: center;
}}
.summary-item .val {{
    font-family: var(--font-display);
    font-size: 1.8rem;
    line-height: 1;
    font-weight: 700;
}}
.summary-item .lbl {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}

/* Footer */
.footer {{
    text-align: center;
    padding: 24px 0 40px;
    color: var(--text-muted);
    font-size: 0.8rem;
}}

@media (max-width: 768px) {{
    .hero-shell {{ grid-template-columns: 1fr; padding: 28px 24px; border-radius: 30px; }}
    .top-controls {{
        top: 12px;
        right: 12px;
        left: 12px;
        justify-content: flex-end;
        flex-wrap: wrap;
    }}
    .report-download {{
        padding: 0 16px;
    }}
    .hero-title-row {{
        display: block;
    }}
    .hero-title-row h1 {{ font-size: clamp(2.2rem, 12vw, 3.2rem); }}
    .hero-brand-mark {{
        height: 124px;
        max-width: 180px;
    }}
    .hero-bridge-mark {{
        justify-self: start;
        margin-inline: 0;
        transform: none;
    }}
    .score-hero {{ flex-direction: column; gap: 24px; }}
    .score-stats {{ flex-wrap: wrap; justify-content: center; }}
    .categories {{ grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); }}
    .container {{ padding: 16px; }}
}}
@page {{
    margin: 14mm;
}}
@media print {{
    html,
    body {{
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }}
    body::before,
    .top-controls {{
        display: none !important;
    }}
    .container {{
        max-width: none;
        padding: 0;
    }}
    .header {{
        padding: 0 0 12px;
    }}
    .hero-shell {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(118px, 150px);
        gap: 14px;
        align-items: center;
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 0 !important;
        overflow: visible !important;
    }}
    .hero-shell::before {{
        display: none !important;
    }}
    .hero-eyebrow,
    .timestamp {{
        display: none !important;
    }}
    .hero-title-block {{
        margin-top: 0;
    }}
    .hero-title-row {{
        display: block;
    }}
    .hero-brand-mark {{
        height: 112px;
        max-width: 148px;
    }}
    .hero-bridge-mark {{
        justify-self: center;
        margin-inline: 0;
        transform: translateX(-10px);
    }}
    .hero-meta {{
        display: block;
        grid-column: 1 / -1;
        margin-top: 12px;
    }}
    .hero-meta-card:first-child {{
        display: none !important;
    }}
    .hero-meta-card {{
        background: color-mix(in srgb, var(--surface) 84%, transparent) !important;
        border: 1px solid var(--card-border) !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
        break-inside: avoid;
        page-break-inside: avoid;
    }}
    .section-body {{
        display: block !important;
    }}
    .chevron {{
        display: none !important;
    }}
    .score-hero {{
        margin: 12px 0 10px !important;
        padding: 22px 24px !important;
        gap: 24px !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
        overflow: visible !important;
    }}
    .score-gauge {{
        width: 150px;
        height: 150px;
    }}
    .score-gauge .gauge-number {{
        font-size: 3rem;
    }}
    .score-stats {{
        gap: 16px;
        flex-wrap: wrap;
        justify-content: center;
    }}
    .stat-card {{
        min-width: 84px;
        padding: 14px 18px;
    }}
    .stat-value {{
        font-size: 1.7rem;
    }}
    .categories {{
        margin-top: 20px;
    }}
    .header,
    .section,
    table,
    .summary-row,
    .categories {{
        break-inside: avoid;
        page-break-inside: avoid;
    }}
}}
</style>
{font_links}
</head>
<body>

<div class="top-controls">
    <button class="report-download" type="button" onclick="downloadPdf()">Download PDF</button>
    <div class="theme-toggle" onclick="toggleTheme()" title="Toggle theme">🌙</div>
</div>

<div class="header">
    <div class="container">
        <div class="hero-shell">
            <div class="hero-copy">
                {hero_eyebrow_markup}
                <div class="hero-title-block">
                    <div class="hero-title-row">
                        <div class="hero-title-copy">
                            <h1>{hero_title_lines_markup}</h1>
                        </div>
                    </div>
                </div>
                {hero_tagline_markup}
                <div class="timestamp">Generated: {datetime.fromisoformat(timestamp).strftime("%B %d, %Y at %I:%M %p")}</div>
            </div>
            {hero_brand_markup}
            <div class="hero-meta">
                <div class="hero-meta-card">
                    <div class="hero-meta-label">Live URL</div>
                    <div class="hero-meta-value">{_esc(domain)}</div>
                    <div class="hero-meta-detail">{_esc(url)}</div>
                </div>
                <div class="hero-meta-card">
                    <div class="hero-meta-label">Audit Grade</div>
                    <div class="hero-meta-value">{grade} / {overall}</div>
                    <div class="hero-meta-detail">Detected platform: {_esc(env_primary)}</div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="container">

    <!-- Overall Score -->
    <div class="score-hero">
        <div class="score-gauge">
            <svg viewBox="0 0 200 200">
                <circle cx="100" cy="100" r="85" fill="none" stroke="var(--card-border)" stroke-width="12"/>
                <circle cx="100" cy="100" r="85" fill="none" stroke="{grade_color}" stroke-width="12"
                    stroke-dasharray="{round(overall * 5.341, 1)} 534.07" stroke-linecap="round"
                    transform="rotate(-90 100 100)"/>
            </svg>
            <div class="gauge-value">
                <div class="gauge-number">{overall}</div>
                <div class="gauge-grade">Grade: {grade}</div>
            </div>
        </div>
        <div class="score-stats">
            <div class="stat-card stat-critical">
                <div class="stat-value">{critical_count}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat-card stat-warning">
                <div class="stat-value">{warning_count}</div>
                <div class="stat-label">Warnings</div>
            </div>
            <div class="stat-card stat-pass">
                <div class="stat-value">{pass_count}</div>
                <div class="stat-label">Info</div>
            </div>
        </div>
    </div>

    <!-- Category Cards -->
    <div class="categories">
        {category_cards}
    </div>

    <!-- Environment Detection -->
    <div class="section" id="section-environment">
        <div class="section-header" onclick="toggleSection('environment')">
            <h2>🧭 Environment Detection (LLM-Inferred)</h2>
            <span class="chevron" id="chevron-environment">▼</span>
        </div>
        <div class="section-body" id="body-environment">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{env_primary}</div><div class="lbl">Primary Platform</div></div>
                <div class="summary-item"><div class="val">{env_runtime}</div><div class="lbl">Runtime Type</div></div>
                <div class="summary-item"><div class="val">{env_confidence}</div><div class="lbl">Confidence</div></div>
                <div class="summary-item"><div class="val">{len(env.get("signals", []))}</div><div class="lbl">Matched Signals</div></div>
            </div>
            <h3 style="margin: 16px 0 8px; font-size: 0.95rem;">Detection Signals</h3>
            <ul style="padding-left:20px;">{env_signals_html}</ul>
            {f'<p style="margin-top:10px;color:var(--text-muted)"><strong>Alternative matches:</strong> {", ".join(env_alts)}</p>' if env_alts else ''}
        </div>
    </div>

    <!-- Environment-specific Fix Plan -->
    <div class="section" id="section-env_fixes">
        <div class="section-header" onclick="toggleSection('env_fixes')">
            <h2>🛠️ Environment-Specific Fix Plan</h2>
            <span class="chevron" id="chevron-env_fixes">▼</span>
        </div>
        <div class="section-body" id="body-env_fixes">
            {env_fixes_html}
        </div>
    </div>

    <!-- Issues Summary -->
    <div class="section" id="section-issues">
        <div class="section-header" onclick="toggleSection('issues')">
            <h2>🚨 All Issues ({len(all_issues)})</h2>
            <span class="chevron" id="chevron-issues">▼</span>
        </div>
        <div class="section-body" id="body-issues">
            {issues_html if issues_html else '<p style="color:var(--text-muted)">No issues found — excellent!</p>'}
        </div>
    </div>

    <!-- Security Headers -->
    <div class="section" id="section-security">
        <div class="section-header" onclick="toggleSection('security')">
            <h2>🔒 Security Headers <span class="badge {"pass" if scores["categories"].get("security",0) >= 80 else "warning" if scores["categories"].get("security",0) >= 50 else "critical"}">{scores["categories"].get("security",0)}/100</span></h2>
            <span class="chevron" id="chevron-security">▼</span>
        </div>
        <div class="section-body" id="body-security">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{"✅" if sec.get("https") else "❌"}</div><div class="lbl">HTTPS</div></div>
                <div class="summary-item"><div class="val">{len(sec.get("headers_present", {}))}</div><div class="lbl">Present</div></div>
                <div class="summary-item"><div class="val">{len(sec.get("headers_missing", {}))}</div><div class="lbl">Missing</div></div>
            </div>
            <table>
                <thead><tr><th>Header</th><th>Status</th><th>Value / Description</th></tr></thead>
                <tbody>{security_rows}</tbody>
            </table>
        </div>
    </div>

    <!-- Social Meta -->
    <div class="section" id="section-social">
        <div class="section-header" onclick="toggleSection('social')">
            <h2>📱 Social Meta Tags <span class="badge {"pass" if scores["categories"].get("social",0) >= 80 else "warning" if scores["categories"].get("social",0) >= 50 else "critical"}">{scores["categories"].get("social",0)}/100</span></h2>
            <span class="chevron" id="chevron-social">▼</span>
        </div>
        <div class="section-body" id="body-social">
            <table>
                <thead><tr><th>Tag</th><th>Status</th><th>Value</th></tr></thead>
                <tbody>{social_rows}</tbody>
            </table>
        </div>
    </div>

    <!-- AI Crawlers -->
    <div class="section" id="section-robots">
        <div class="section-header" onclick="toggleSection('robots')">
            <h2>🤖 Robots & AI Crawlers <span class="badge {"pass" if scores["categories"].get("robots",0) >= 80 else "warning" if scores["categories"].get("robots",0) >= 50 else "critical"}">{scores["categories"].get("robots",0)}/100</span></h2>
            <span class="chevron" id="chevron-robots">▼</span>
        </div>
        <div class="section-body" id="body-robots">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{rob.get("status", "?")}</div><div class="lbl">robots.txt</div></div>
                <div class="summary-item"><div class="val">{len(rob.get("sitemaps", []))}</div><div class="lbl">Sitemaps</div></div>
                <div class="summary-item"><div class="val">{len(rob.get("user_agents", {}))}</div><div class="lbl">User-Agents</div></div>
            </div>
            <h3 style="margin: 16px 0 8px; font-size: 0.95rem;">AI Crawler Management</h3>
            <table>
                <thead><tr><th>Crawler</th><th>Status</th><th>Details</th></tr></thead>
                <tbody>{ai_rows}</tbody>
            </table>
        </div>
    </div>

    <!-- Broken Links -->
    <div class="section" id="section-broken_links">
        <div class="section-header" onclick="toggleSection('broken_links')">
            <h2>🔗 Broken Links <span class="badge {"pass" if bl_broken == 0 else "critical"}">{bl_broken} broken / {bl_total} total</span></h2>
            <span class="chevron" id="chevron-broken_links">▼</span>
        </div>
        <div class="section-body" id="body-broken_links">
            <div class="summary-row">
                <div class="summary-item"><div class="val" style="color:var(--green)">{bl_healthy}</div><div class="lbl">Healthy</div></div>
                <div class="summary-item"><div class="val" style="color:var(--red)">{bl_broken}</div><div class="lbl">Broken</div></div>
                <div class="summary-item"><div class="val" style="color:var(--info)">{bl_blocked}</div><div class="lbl">Blocked</div></div>
                <div class="summary-item"><div class="val" style="color:var(--yellow)">{bl_summary.get("redirected", 0)}</div><div class="lbl">Redirected</div></div>
                <div class="summary-item"><div class="val" style="color:var(--orange)">{bl_summary.get("timeout", 0)}</div><div class="lbl">Timeout</div></div>
            </div>
            {"<table><thead><tr><th>Type</th><th>Status</th><th>URL</th><th>Anchor</th></tr></thead><tbody>" + broken_rows + "</tbody></table>" if broken_rows else '<p style="color:var(--green);margin-top:12px">✅ No broken or blocked links found</p>'}
        </div>
    </div>

    <!-- Internal Links -->
    <div class="section" id="section-internal_links">
        <div class="section-header" onclick="toggleSection('internal_links')">
            <h2>🕸️ Internal Link Structure <span class="badge {"pass" if scores["categories"].get("internal_links",0) >= 80 else "warning" if scores["categories"].get("internal_links",0) >= 50 else "critical"}">{scores["categories"].get("internal_links",0)}/100</span></h2>
            <span class="chevron" id="chevron-internal_links">▼</span>
        </div>
        <div class="section-body" id="body-internal_links">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{il_pages}</div><div class="lbl">Pages Crawled</div></div>
                <div class="summary-item"><div class="val">{il_total}</div><div class="lbl">Internal Links</div></div>
                <div class="summary-item"><div class="val">{il_dist.get("avg", 0)}</div><div class="lbl">Avg Links/Page</div></div>
                <div class="summary-item"><div class="val">{len(il.get("orphan_candidates", []))}</div><div class="lbl">Orphan Pages</div></div>
            </div>
            {f'<h3 style="margin:16px 0 8px;font-size:0.95rem;">Top Anchor Texts</h3>' + anchor_bars if anchor_bars else ''}
            {f'<h3 style="margin:16px 0 8px;font-size:0.95rem;">Potential Orphan Pages</h3><table><thead><tr><th>URL</th><th>Incoming Links</th></tr></thead><tbody>{orphan_rows}</tbody></table>' if orphan_rows else ''}
        </div>
    </div>

    <!-- Redirects -->
    <div class="section" id="section-redirects">
        <div class="section-header" onclick="toggleSection('redirects')">
            <h2>↪️ Redirect Chain <span class="badge {"pass" if red.get("total_hops", 0) <= 1 else "warning"}">{red.get("total_hops", 0)} hops</span></h2>
            <span class="chevron" id="chevron-redirects">▼</span>
        </div>
        <div class="section-body" id="body-redirects">
            {f'<table><thead><tr><th>#</th><th>Status</th><th>URL</th><th>Time</th><th>Type</th></tr></thead><tbody>{redirect_rows}</tbody></table>' if redirect_rows else '<p style="color:var(--green)">✅ No redirects — direct access</p>'}
        </div>
    </div>

    <!-- llms.txt -->
    <div class="section" id="section-llms_txt">
        <div class="section-header" onclick="toggleSection('llms_txt')">
            <h2>🧠 AI Search Readiness (llms.txt) <span class="badge {"pass" if llm.get("exists") else "critical"}">{"Found" if llm.get("exists") else "Not Found"}</span></h2>
            <span class="chevron" id="chevron-llms_txt">▼</span>
        </div>
        <div class="section-body" id="body-llms_txt">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{"✅" if llm.get("exists") else "❌"}</div><div class="lbl">llms.txt</div></div>
                <div class="summary-item"><div class="val">{"✅" if llm.get("full_exists") else "❌"}</div><div class="lbl">llms-full.txt</div></div>
                <div class="summary-item"><div class="val">{llm.get("quality", {}).get("score", 0)}</div><div class="lbl">Quality Score</div></div>
            </div>
            {"".join(f'<div class="issue-item warning"><span class="issue-badge">TIP</span> {s}</div>' for s in llm.get("quality", {}).get("suggestions", []))}
        </div>
    </div>

    <!-- PageSpeed / Core Web Vitals -->
    <div class="section" id="section-pagespeed">
        <div class="section-header" onclick="toggleSection('pagespeed')">
            <h2>⚡ Performance & Core Web Vitals <span class="badge {"pass" if scores["categories"].get("pagespeed",0) >= 80 else "warning" if scores["categories"].get("pagespeed",0) >= 50 else "critical"}">{scores["categories"].get("pagespeed",0)}/100</span></h2>
            <span class="chevron" id="chevron-pagespeed">▼</span>
        </div>
        <div class="section-body" id="body-pagespeed">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{psi.get("performance_score", "?")}</div><div class="lbl">Performance</div></div>
                <div class="summary-item"><div class="val">{psi.get("field_data", psi.get("lab_data", {})).get("LCP", "?")}</div><div class="lbl">LCP</div></div>
                <div class="summary-item"><div class="val">{psi.get("field_data", psi.get("lab_data", {})).get("INP", psi.get("field_data", psi.get("lab_data", {})).get("TBT", "?"))}</div><div class="lbl">INP/TBT</div></div>
                <div class="summary-item"><div class="val">{psi.get("field_data", psi.get("lab_data", {})).get("CLS", "?")}</div><div class="lbl">CLS</div></div>
            </div>
            {'<div class="issue-item warning"><span class="issue-badge">NOTE</span> <div><strong>PageSpeed API returned an error or was rate-limited.</strong><br><span style="color:var(--text-muted)">Set <code>PAGESPEED_API_KEY</code> (or pass <code>--api-key</code> to <code>pagespeed.py</code>) and rerun the report. The LLM can still analyze Core Web Vitals by reading the page directly.</span></div></div>' if psi.get('error') or psi.get('performance_score', 0) == 0 else ''}
            {render_recommendations(psi)}
        </div>
    </div>

    <!-- On-Page SEO -->
    <div class="section" id="section-onpage">
        <div class="section-header" onclick="toggleSection('onpage')">
            <h2>📝 On-Page SEO <span class="badge {"pass" if scores["categories"].get("onpage",0) >= 80 else "warning" if scores["categories"].get("onpage",0) >= 50 else "critical"}">{scores["categories"].get("onpage",0)}/100</span></h2>
            <span class="chevron" id="chevron-onpage">▼</span>
        </div>
        <div class="section-body" id="body-onpage">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{'✅' if op.get('title') else '❌'}</div><div class="lbl">Title Tag</div></div>
                <div class="summary-item"><div class="val">{'✅' if op.get('meta_description') else '❌'}</div><div class="lbl">Meta Desc</div></div>
                <div class="summary-item"><div class="val">{'✅' if op.get('h1') else '❌'}</div><div class="lbl">H1</div></div>
                <div class="summary-item"><div class="val">{'✅' if op.get('canonical') else '❌'}</div><div class="lbl">Canonical</div></div>
            </div>
            <table>
                <thead><tr><th>Element</th><th>Value</th><th>Length</th></tr></thead>
                <tbody>
                    <tr><td>Title</td><td>{(op.get('title','') or '—')[:70]}</td><td>{len(op.get('title','') or '')}</td></tr>
                    <tr><td>Meta Description</td><td>{(op.get('meta_description','') or '—')[:100]}</td><td>{len(op.get('meta_description','') or '')}</td></tr>
                    <tr><td>H1</td><td>{(op.get('h1',[''])[0] if isinstance(op.get('h1'), list) and op.get('h1') else op.get('h1','') or '—')[:70]}</td><td>—</td></tr>
                    <tr><td>Canonical</td><td class="link-url">{(op.get('canonical') or '—')[:80]}</td><td>—</td></tr>
                </tbody>
            </table>
            {render_recommendations(op)}
        </div>
    </div>

    <!-- Readability -->
    <div class="section" id="section-readability">
        <div class="section-header" onclick="toggleSection('readability')">
            <h2>📖 Readability <span class="badge {"pass" if scores["categories"].get("readability",0) >= 80 else "warning" if scores["categories"].get("readability",0) >= 50 else "critical"}">{scores["categories"].get("readability",0)}/100</span></h2>
            <span class="chevron" id="chevron-readability">▼</span>
        </div>
        <div class="section-body" id="body-readability">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{rd.get('flesch_reading_ease', '?')}</div><div class="lbl">Flesch Score</div></div>
                <div class="summary-item"><div class="val">{rd.get('flesch_kincaid_grade', '?')}</div><div class="lbl">Grade Level</div></div>
                <div class="summary-item"><div class="val">{rd.get('word_count', '?')}</div><div class="lbl">Words</div></div>
                <div class="summary-item"><div class="val">{rd.get('estimated_reading_time_min', '?')} min</div><div class="lbl">Read Time</div></div>
            </div>
            {render_recommendations(rd)}
            {render_readability_rewrites(rd)}
        </div>
    </div>

    <!-- Article SEO Extractor -->
    <div class="section" id="section-article">
        <div class="section-header" onclick="toggleSection('article')">
            <h2>📄 Article Info & Keywords <span class="badge {"pass" if scores["categories"].get("article",0) >= 80 else "warning" if scores["categories"].get("article",0) >= 50 else "critical"}">{scores["categories"].get("article",0)}/100</span></h2>
            <span class="chevron" id="chevron-article">▼</span>
        </div>
        <div class="section-body" id="body-article">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{art.get('word_count', '?')}</div><div class="lbl">Words</div></div>
                <div class="summary-item"><div class="val">{len(art.get('headings', dict()).get('h2', []))}</div><div class="lbl">H2 Headings</div></div>
                <div class="summary-item"><div class="val">{len(art.get('images', []))}</div><div class="lbl">Images</div></div>
            </div>
            <h3 style="margin: 16px 0 8px; font-size: 0.95rem;">Extracted Keywords</h3>
            <table>
                <thead><tr><th>Target Keyword</th><th>LSI / Related Keywords</th></tr></thead>
                <tbody>
                    <tr>
                        <td style="font-weight: 600; color: var(--accent);">{art.get('target_keyword', '—')}</td>
                        <td>{', '.join(art.get('lsi_keywords', [])) if art.get('lsi_keywords') else '—'}</td>
                    </tr>
                </tbody>
            </table>
            {render_recommendations(art)}
        </div>
    </div>

    <!-- Entity SEO -->
    <div class="section" id="section-entity">
        <div class="section-header" onclick="toggleSection('entity')">
            <h2>🏛️ Entity SEO <span class="badge {"pass" if scores["categories"].get("entity",0) >= 50 else "warning" if scores["categories"].get("entity",0) >= 20 else "critical"}">{scores["categories"].get("entity",0)}/100</span></h2>
            <span class="chevron" id="chevron-entity">▼</span>
        </div>
        <div class="section-body" id="body-entity">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{'✅' if ent.get('wikidata', {}).get('found') else '❌'}</div><div class="lbl">Wikidata</div></div>
                <div class="summary-item"><div class="val">{'✅' if ent.get('wikipedia', {}).get('found') else '❌'}</div><div class="lbl">Wikipedia</div></div>
                <div class="summary-item"><div class="val">{ent.get('sameas_analysis', {}).get('total_found', 0)}</div><div class="lbl">sameAs Links</div></div>
                <div class="summary-item"><div class="val">{len(ent.get('issues', []))}</div><div class="lbl">Issues</div></div>
            </div>
            {render_recommendations(ent)}
        </div>
    </div>

    <!-- Link Profile -->
    <div class="section" id="section-link_profile">
        <div class="section-header" onclick="toggleSection('link_profile')">
            <h2>🔗 Link Profile <span class="badge {"pass" if scores["categories"].get("link_profile",0) >= 70 else "warning" if scores["categories"].get("link_profile",0) >= 40 else "critical"}">{scores["categories"].get("link_profile",0)}/100</span></h2>
            <span class="chevron" id="chevron-link_profile">▼</span>
        </div>
        <div class="section-body" id="body-link_profile">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{lp.get('pages_crawled', '?')}</div><div class="lbl">Pages Crawled</div></div>
                <div class="summary-item"><div class="val">{lp.get('avg_internal_links_per_page', '?')}</div><div class="lbl">Avg Links/Page</div></div>
                <div class="summary-item"><div class="val">{lp.get('orphan_pages', {}).get('count', 0)}</div><div class="lbl">Orphan Pages</div></div>
                <div class="summary-item"><div class="val">{lp.get('dead_end_pages', {}).get('count', 0)}</div><div class="lbl">Dead Ends</div></div>
            </div>
            {render_recommendations(lp)}
        </div>
    </div>

    <!-- Hreflang -->
    <div class="section" id="section-hreflang">
        <div class="section-header" onclick="toggleSection('hreflang')">
            <h2>🌍 Hreflang / International SEO <span class="badge {"pass" if hf.get('hreflang_tags_found', 0) > 0 else "info"}">{hf.get('hreflang_tags_found', 0)} tags</span></h2>
            <span class="chevron" id="chevron-hreflang">▼</span>
        </div>
        <div class="section-body" id="body-hreflang">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{hf.get('implementation_method', 'none')}</div><div class="lbl">Method</div></div>
                <div class="summary-item"><div class="val">{hf.get('hreflang_tags_found', 0)}</div><div class="lbl">Tags Found</div></div>
            </div>
            {'<p style="color:var(--text-muted);margin-top:12px">No hreflang tags found — this is expected for single-language sites.</p>' if hf.get('hreflang_tags_found', 0) == 0 else render_recommendations(hf)}
        </div>
    </div>

    <!-- Duplicate Content -->
    <div class="section" id="section-duplicate_content">
        <div class="section-header" onclick="toggleSection('duplicate_content')">
            <h2>📋 Content Uniqueness <span class="badge {"pass" if len(dc.get('near_duplicates', [])) == 0 else "warning"}">{len(dc.get('near_duplicates', []))} dupes / {len(dc.get('thin_pages', []))} thin</span></h2>
            <span class="chevron" id="chevron-duplicate_content">▼</span>
        </div>
        <div class="section-body" id="body-duplicate_content">
            <div class="summary-row">
                <div class="summary-item"><div class="val">{dc.get('pages_analyzed', '?')}</div><div class="lbl">Pages Analyzed</div></div>
                <div class="summary-item"><div class="val">{len(dc.get('near_duplicates', []))}</div><div class="lbl">Near Duplicates</div></div>
                <div class="summary-item"><div class="val">{len(dc.get('thin_pages', []))}</div><div class="lbl">Thin Pages</div></div>
            </div>
            {render_recommendations(dc)}
        </div>
    </div>

    <!-- Recommendations Summary -->
    <div class="section" id="section-recs">
        <div class="section-header" onclick="toggleSection('recs')">
            <h2>💡 All Recommendations</h2>
            <span class="chevron" id="chevron-recs">▼</span>
        </div>
        <div class="section-body" id="body-recs">
            {render_all_recommendations(data)}
        </div>
    </div>

</div>

<div class="footer">
    <p>Generated by SEO Skill · {footer_theme_name} · {datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")}</p>
</div>

<script>
let sectionsClosedForPrint = null;

function toggleSection(id) {{
    const body = document.getElementById('body-' + id);
    const chevron = document.getElementById('chevron-' + id);
    body.classList.toggle('open');
    chevron.classList.toggle('open');
}}
function scrollToSection(id) {{
    const el = document.getElementById('section-' + id);
    if (el) {{
        el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        // Auto-open
        const body = document.getElementById('body-' + id);
        const chevron = document.getElementById('chevron-' + id);
        if (!body.classList.contains('open')) {{
            body.classList.add('open');
            chevron.classList.add('open');
        }}
    }}
}}
function toggleTheme() {{
    const html = document.documentElement;
    const btn = document.querySelector('.theme-toggle');
    if (html.getAttribute('data-theme') === 'light') {{
        html.removeAttribute('data-theme');
        btn.textContent = '🌙';
    }} else {{
        html.setAttribute('data-theme', 'light');
        btn.textContent = '☀️';
    }}
}}
function prepareForPrint() {{
    if (sectionsClosedForPrint !== null) {{
        return;
    }}
    sectionsClosedForPrint = [];
    document.querySelectorAll('.section-body').forEach((body) => {{
        if (!body.classList.contains('open')) {{
            sectionsClosedForPrint.push(body.id.replace('body-', ''));
            body.classList.add('open');
        }}
    }});
    document.querySelectorAll('.chevron').forEach((chevron) => {{
        chevron.classList.add('open');
    }});
}}
function restoreAfterPrint() {{
    if (sectionsClosedForPrint === null) {{
        return;
    }}
    sectionsClosedForPrint.forEach((id) => {{
        const body = document.getElementById('body-' + id);
        const chevron = document.getElementById('chevron-' + id);
        if (body) {{
            body.classList.remove('open');
        }}
        if (chevron) {{
            chevron.classList.remove('open');
        }}
    }});
    sectionsClosedForPrint = null;
}}
function downloadPdf() {{
    const previousTitle = document.title;
    prepareForPrint();
    document.title = '{pdf_filename}';
    window.print();
    window.setTimeout(() => {{
        document.title = previousTitle;
    }}, 250);
}}
window.addEventListener('beforeprint', prepareForPrint);
window.addEventListener('afterprint', restoreAfterPrint);
// Auto-open issues section
document.getElementById('body-issues').classList.add('open');
document.getElementById('chevron-issues').classList.add('open');
</script>

</body>
</html>'''

    return html


def main():
    parser = argparse.ArgumentParser(description="Generate interactive SEO HTML report")
    parser.add_argument("url", help="Website URL to analyze")
    parser.add_argument("--output", "-o", help="Output filename (default: seo-report-<domain>.html)")
    parser.add_argument(
        "--theme",
        choices=sorted(REPORT_THEMES.keys()),
        default="shadewater",
        help="Report theme profile. Defaults to the branded Shadewater theme.",
    )
    parser.add_argument(
        "--brand-logo",
        help="Optional local image path to inline in the report header. Shadewater reports auto-detect a local Labs mark when available.",
    )
    parser.add_argument(
        "--audit-report-output",
        help="Optional filename for FULL-AUDIT-REPORT.md. Defaults beside the HTML report.",
    )
    parser.add_argument(
        "--action-plan-output",
        help="Optional filename for ACTION-PLAN.md. Defaults beside the HTML report.",
    )
    parser.add_argument(
        "--claude-handoff-output",
        help="Optional filename for CLAUDE-HANDOFF.md. Defaults beside the HTML report.",
    )
    parser.add_argument(
        "--codex-handoff-output",
        help="Optional filename for CODEX-HANDOFF.md. Defaults beside the HTML report.",
    )
    parser.add_argument(
        "--public-root",
        help="Optional local public directory for resolving image src values into a Webp Me Daddy handoff. Defaults to ./public when present.",
    )
    parser.add_argument(
        "--image-handoff-output",
        help="Optional filename for the auto-generated image remediation handoff. Defaults to seo-image-handoff.json beside the report.",
    )
    parser.add_argument(
        "--no-image-handoff",
        action="store_true",
        help="Disable automatic seo-image-handoff.json generation.",
    )
    parser.add_argument(
        "--no-markdown-artifacts",
        action="store_true",
        help="Disable automatic FULL-AUDIT-REPORT.md and ACTION-PLAN.md generation.",
    )

    args = parser.parse_args()

    public_root = resolve_public_root(args.public_root)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        domain = urlparse(args.url).netloc.replace(".", "_")
        output_path = f"seo-report-{domain}.html"

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    report_dir = Path(output_dir) if output_dir else Path.cwd()
    image_handoff_output = (
        Path(args.image_handoff_output).resolve()
        if args.image_handoff_output
        else (report_dir / "seo-image-handoff.json").resolve()
    )
    audit_report_output = (
        Path(args.audit_report_output).resolve()
        if args.audit_report_output
        else (report_dir / "FULL-AUDIT-REPORT.md").resolve()
    )
    action_plan_output = (
        Path(args.action_plan_output).resolve()
        if args.action_plan_output
        else (report_dir / "ACTION-PLAN.md").resolve()
    )
    claude_handoff_output = (
        Path(args.claude_handoff_output).resolve()
        if args.claude_handoff_output
        else (report_dir / "CLAUDE-HANDOFF.md").resolve()
    )
    codex_handoff_output = (
        Path(args.codex_handoff_output).resolve()
        if args.codex_handoff_output
        else (report_dir / "CODEX-HANDOFF.md").resolve()
    )

    # Collect all data
    data = collect_data(
        args.url,
        public_root=public_root,
        image_handoff_output=image_handoff_output,
        emit_image_handoff=not args.no_image_handoff,
    )

    # Calculate scores
    scores = calculate_overall_score(data)
    findings_bundle = build_report_findings(data)

    # Generate HTML
    brand_logo_uri = resolve_brand_logo_uri(args.theme, explicit_brand_logo=args.brand_logo)
    html = generate_html(data, scores, theme_name=args.theme, brand_logo_uri=brand_logo_uri)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    if not args.no_markdown_artifacts:
        write_markdown_artifacts(
            data=data,
            scores=scores,
            findings_bundle=findings_bundle,
            audit_report_path=audit_report_output,
            action_plan_path=action_plan_output,
            claude_handoff_path=claude_handoff_output,
            codex_handoff_path=codex_handoff_output,
            html_report_path=Path(output_path),
        )

    print(f"\n[done] Report saved to: {os.path.abspath(output_path)}")
    print(f"   Overall Score: {scores['overall']}/100")
    if not args.no_markdown_artifacts:
        print(f"   Full audit report: {audit_report_output}")
        print(f"   Action plan: {action_plan_output}")
        print(f"   Claude handoff: {claude_handoff_output}")
        print(f"   Codex handoff: {codex_handoff_output}")
    image_handoff = data.get("artifacts", {}).get("image_handoff", {})
    if isinstance(image_handoff, dict) and image_handoff.get("generated"):
        print(f"   Image handoff: {image_handoff.get('path')}")
    elif isinstance(image_handoff, dict) and image_handoff.get("reason") and not args.no_image_handoff:
        print(f"   Image handoff: skipped ({image_handoff.get('reason')})")
    print(f"   Open in browser to view the interactive report")


if __name__ == "__main__":
    main()
