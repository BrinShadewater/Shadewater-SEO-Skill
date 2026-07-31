# Shadewater SEO Tool Handoff

## Current State

The SEO tool audits a public URL and writes a report folder containing:

- `SEO-REPORT.html`
- `FULL-AUDIT-REPORT.md`
- `ACTION-PLAN.md`
- `CLAUDE-HANDOFF.md`
- `CODEX-HANDOFF.md`
- `seo-image-handoff.json` when image remediation is available

The Shadewater dashboard is dark-blue themed, printable, and designed for a novice SEO reader while preserving technical evidence for implementation.

## Important Files

- `scripts/generate_report.py`: audit orchestration, report rendering, markdown artifact generation, handoff generation.
- `scripts/test_seo_skill.py`: regression tests for scoring, report UI, artifacts, and handoff behavior.
- `scripts/lint_freshness.py`: checks SEO guidance freshness metadata.

## Verification Commands

From `scripts`:

```powershell
python -m unittest test_seo_skill
```

From the project root:

```powershell
python 'scripts\lint_freshness.py'
```

## PageSpeed Configuration

Do not write PageSpeed API keys into source files, report files, or prompts. Configure them as environment variables before running reports. Domain-specific variables are preferred:

- `PAGESPEED_API_KEY_SHADEWATERLABS_COM`
- `PAGESPEED_API_KEY_STRANGEHARVESTMOVIE_COM`

The generator also supports `GOOGLE_PAGESPEED_API_KEY_<DOMAIN>`, `PAGESPEED_API_KEY`, `GOOGLE_PAGESPEED_API_KEY`, and `GOOGLE_API_KEY`.

## Agent Notes

- Claude Code should read `CLAUDE.md` first.
- Codex should also read applicable `AGENTS.md` and Shadewater memory notes when available.
- Treat generated report JSON/markdown artifacts as implementation context, not as secrets.
- Do not expose `.env`, API keys, tokens, cookies, or credentials.
- Do not push or run destructive git commands without explicit approval.

## Future SaaS Direction

Keep audit collection, normalized audit data, HTML rendering, PDF export, and agent handoff generation separable. This keeps the local tool compatible with a future hosted product that may add auth, queued audits, report history, Stripe billing, rate limits, and public/private report sharing.
