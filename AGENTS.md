# Shadewater SEO Tool — Agent Guide

Agent-neutral. Tools that read `AGENTS.md` load this file natively; Claude Code loads
it through the `@`-import in `CLAUDE.md` beside it. Edit here, keep it agent-neutral.
(Roles swapped 2026-08-06: this content previously lived in `CLAUDE.md` with a pointer
here — two files, one of which drifted. Now there is one copy.)

This project generates SEO audit reports, including an interactive HTML dashboard, markdown audit artifacts, action plans, and AI-agent handoff files.

## Start Here

- Main generator: `scripts/generate_report.py`
- Tests: `scripts/test_seo_skill.py`
- Freshness lint: `scripts/lint_freshness.py`
- Generated reports: `reports/<domain>/SEO-REPORT.html`

## Common Commands

Run the test suite from `scripts`:

```powershell
python -m unittest test_seo_skill
```

Run the documentation freshness lint from the project root:

```powershell
python 'scripts\lint_freshness.py'
```

Generate a report from a report folder:

```powershell
python path/to/shadewater-seo-skill/scripts/generate_report.py 'https://example.com' --output 'SEO-REPORT.html'
```

Use a Python 3.11+ with `requests` and `beautifulsoup4` installed.

## PageSpeed Keys

PageSpeed keys must stay in environment variables, not in source files or generated reports. The report generator checks a domain-specific key first, then global fallback keys:

- `PAGESPEED_API_KEY_<YOUR_DOMAIN>`
- `GOOGLE_PAGESPEED_API_KEY_<YOUR_DOMAIN>`
- `PAGESPEED_API_KEY`
- `GOOGLE_PAGESPEED_API_KEY`
- `GOOGLE_API_KEY`

## Design Constraints

- The Summary tab is for novice SEO readability: plain language, grouped priorities, impact/effort labels, and a clear fix sequence.
- The Findings tab remains the technical source of truth for filtering and evidence details.
- The report should stay printable/PDF-friendly, with evidence details expanded during print.
- Generated handoff files should be deterministic from audit data so the project can later become a hosted service.

## Safety Rules

- Do not read, print, copy, or summarize secrets, `.env` files, API keys, cookies, tokens, or credentials.
- Do not push, delete, reset, or rewrite history without explicit approval.
- Before meaningful edits, inspect the current code and tests.
- Run tests before and after changes.
