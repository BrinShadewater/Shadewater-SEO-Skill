# Codex Context: Shadewater SEO Tool

**Read `CLAUDE.md` in this folder before working here.** Despite the filename it is
agent-neutral and is the full guide — entry points, commands, design constraints, and safety
rules. Every command in it already uses the Codex runtime Python. It is not duplicated here on
purpose: two copies drift, and a stale copy of a safety rule is worse than a pointer to a live
one.

Quick orientation:

- Main generator: `scripts/generate_report.py`
- Tests: `scripts/test_seo_skill.py` — run them before and after changes
- Freshness lint: `scripts/lint_freshness.py`
- Generated reports: `reports/<domain>/SEO-REPORT.html`

**PageSpeed keys live in environment variables only** — never in source files, never in a
generated report. Do not read, print, copy, or summarise API keys, `.env` contents, cookies,
tokens, or credentials, and do not paste a key into a report to "test" it.

This project is also published as the `seo` skill, which is kept in sync between
`~\.codex\skills` and `~\.claude\skills`. Check `Claude\skill-tools\sync_skills.py` before
assuming your copy is current.

Generic rails come from `Projects\AGENTS.md` one level up.
