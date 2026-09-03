# 🌊 Shadewater SEO

![Licence](https://img.shields.io/badge/licence-MIT-blue?style=flat-square) ![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?style=flat-square) ![Claude Skill](https://img.shields.io/badge/Claude-skill-d97757?style=flat-square) ![Shadewater Labs](https://img.shields.io/badge/Shadewater%20Labs-%E2%9A%97%EF%B8%8F-6b4fa2?style=flat-square)

The SEO audit skill for Shadewater Labs sites — [datagoblin.ca](https://datagoblin.ca),
shadewaterlabs.com, strangeharvestmovie.com, and whatever ships next. It runs LLM-first
audits backed by deterministic evidence scripts, then hands you a dark-blue Shadewater
dashboard, markdown artifacts, and agent handoff files so the fixes actually get done
instead of dying in a spreadsheet.

This started life as a fork (see [Attribution](#-attribution)) and has since grown its own
report generator, branding, test suite, and workflow. It installs into Claude Code and
Codex as the `shadewater-seo` skill.

The house rule: **no finding without evidence.** Every claim gets a confidence label —
`Confirmed`, `Likely`, or `Hypothesis` — and anything a script can verify, a script
verifies. SEO folklore doesn't make it into the report.

## 🔍 What it does

- **Website audits** — full-domain or single-page, findings prioritized by impact and effort
- **Technical SEO** — crawlability, indexability, security headers, redirects, Core Web
  Vitals, AI crawler access
- **Content & E-E-A-T** — quality assessment against the current Quality Rater Guidelines
- **Schema** — JSON-LD detection, validation, and generation (and it knows which types
  Google has quietly killed)
- **GEO / AEO** — AI search readiness: AI Overviews, ChatGPT, Perplexity, Featured
  Snippets, PAA — without the llms.txt snake oil
- **GitHub repo SEO** — metadata, topics, README quality, query benchmarking, traffic archival
- **Reports** — the Shadewater dashboard (`SEO-REPORT.html`), `FULL-AUDIT-REPORT.md`,
  `ACTION-PLAN.md`, plus `CLAUDE-HANDOFF.md` / `CODEX-HANDOFF.md` so an agent can pick up
  the fixes directly

## 🧰 Sub-skills

| Command | Description |
|---------|-------------|
| `seo audit` | Full website audit with evidence-backed scoring |
| `seo page` | Deep single-page analysis |
| `seo article` | Article extraction & content optimization |
| `seo technical` | Crawlability, indexability, security, Core Web Vitals |
| `seo content` | Content quality & E-E-A-T |
| `seo schema` | Schema.org detection, validation & JSON-LD generation |
| `seo sitemap` | XML sitemap analysis & generation |
| `seo images` | Image optimization audit |
| `seo geo` | Generative Engine Optimization (AI Overviews, ChatGPT, Perplexity) |
| `seo aeo` | Answer Engine Optimization (Featured Snippets, PAA, Knowledge Panel) |
| `seo links` | Link profile — internal links, backlinks, orphan pages |
| `seo hreflang` | International SEO / hreflang validation |
| `seo programmatic` | Programmatic SEO safeguards |
| `seo competitors` | Comparison & alternatives pages |
| `seo plan` | Strategic SEO planning |
| `seo github` | GitHub repository SEO |

Each maps to a doc under `resources/skills/`, with specialist agent definitions in
`resources/agents/` and evidence scripts in `scripts/`. The full prompt-to-script routing
table lives in [SKILL.md](SKILL.md).

## 📦 Install

```bash
git clone https://github.com/BrinShadewater/Shadewater-SEO-Skill.git
cd Shadewater-SEO-Skill

# Claude Code (installs to ~/.claude/skills/shadewater-seo)
bash install.sh --target claude

# Codex (installs to ~/.codex/skills/shadewater-seo)
bash install.sh --target codex

# Both
bash install.sh --target global
```

On Windows, use `install.ps1` with the same `--target` options.

Python dependencies:

```bash
pip install requests beautifulsoup4
```

Optional, for visual analysis (screenshots, above-the-fold checks):

```bash
pip install playwright && playwright install chromium
```

## 📊 Generating a report

```bash
python scripts/generate_report.py "https://example.com" --output SEO-REPORT.html
```

Produces the Shadewater dashboard plus markdown artifacts and agent handoffs in the report
folder. PageSpeed API keys come from environment variables only — domain-specific
(`PAGESPEED_API_KEY_<DOMAIN>`) first, then global fallbacks. Never put keys in source or
reports; see [CLAUDE.md](CLAUDE.md) for the full list.

## ✅ Verification

```bash
# Regression tests (from scripts/)
python -m unittest test_seo_skill

# Doc freshness lint (from repo root)
python scripts/lint_freshness.py

# Environment check
python scripts/doctor.py --json
```

The freshness lint is the reason this skill doesn't quietly rot: every reference doc
carries an `Updated:` tag and gets flagged at 90 days. Stale SEO advice is worse than
no SEO advice.

CI runs the regression tests and the doctor on every pull request and push to `main`,
and reports the freshness lint alongside them.

## ⚖️ Rules the audits enforce

The stuff SEO blogs keep getting wrong, hard-coded so the audits can't:

| Rule | Detail |
|------|--------|
| **INP not FID** | FID removed Sept 2024; INP is the sole interactivity metric |
| **FAQ rich results dead** | Fully retired May 2026 — never recommend FAQPage schema |
| **HowTo deprecated** | Rich results removed Sept 2023 |
| **JSON-LD only** | Never recommend Microdata or RDFa for new markup |
| **E-E-A-T everywhere** | Applies to all competitive queries since Dec 2025 |
| **Mobile-first complete** | 100% mobile-first indexing since July 2024 |
| **llms.txt is not magic** | Google's own AI guide (May 2026) says it does nothing for Google Search |

## 🙏 Attribution

This is a derivative work, gratefully built on:

- **[Agentic-SEO-Skill](https://github.com/Bhanunamikaze/Agentic-SEO-Skill)** by
  [Bhanu Namikaze](https://github.com/Bhanunamikaze) — the multi-IDE skill packaging,
  installers, and GitHub SEO workflows this fork started from
- **[claude-seo](https://github.com/AgriciDaniel/claude-seo)** by
  [AgriciDaniel](https://github.com/AgriciDaniel) — the original core SEO logic, reference
  data, agent definitions, and sub-skill instructions

Shadewater Labs additions: the Shadewater report dashboard and theming in
`scripts/generate_report.py`, agent handoff generation, domain-specific PageSpeed key
handling, the regression test suite, the freshness-lint discipline, and the rebrand to
`shadewater-seo`.

## 📄 License

MIT. See [LICENSE](LICENSE) — original copyright notices retained, Shadewater Labs
modifications added under the same terms.
