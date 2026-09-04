---
name: seo-technical
description: >
  Technical SEO audit across 8 categories: crawlability, indexability, security,
  URL structure, mobile, Core Web Vitals, structured data, and JavaScript
  rendering. Use when user says "technical SEO", "crawl issues", "robots.txt",
  "Core Web Vitals", "site speed", or "security headers".
---

<!-- Updated: 2026-09-03 -->

# Technical SEO Audit

Read provider guidance before provider-sensitive recommendations:

- `resources/references/search-provider-canon.md`
- `resources/references/provider-guidance-matrix.md`
- `resources/references/google-ai-optimization-guide.md`
- `resources/references/bing-search-and-ai.md`
- `resources/references/indexnow.md`

## Categories

### 1. Crawlability
- robots.txt: exists, valid, not blocking important resources
- XML sitemap: exists, referenced in robots.txt, valid format
- Noindex tags: intentional vs accidental
- Crawl depth: important pages within 3 clicks of homepage
- JavaScript rendering: check if critical content requires JS execution
- Crawl budget: for large sites (>10k pages), efficiency matters

#### AI Crawler Management

As of 2025-2026, AI companies actively crawl the web to train models and power AI search. Managing these crawlers via robots.txt is a critical technical SEO consideration.

**Known AI crawlers:**

| Crawler | Company | robots.txt token | Purpose |
|---------|---------|-----------------|---------|
| GPTBot | OpenAI | `GPTBot` | Model training |
| ChatGPT-User | OpenAI | `ChatGPT-User` | Real-time browsing |
| ClaudeBot | Anthropic | `ClaudeBot` | Model training |
| Claude-User | Anthropic | `Claude-User` | Real-time fetches on a user's behalf |
| Claude-SearchBot | Anthropic | `Claude-SearchBot` | Search-result quality (not training) |
| PerplexityBot | Perplexity | `PerplexityBot` | Search index only — Perplexity states it is **not** used for model training |
| Perplexity-User | Perplexity | `Perplexity-User` | Real-time fetches on a user's behalf |
| Bytespider | ByteDance | `Bytespider` | Model training |
| Google-Extended | Google | `Google-Extended` | Gemini training (NOT search) |
| CCBot | Common Crawl | `CCBot` | Open dataset |

**Key distinctions:**
- Blocking `Google-Extended` prevents Gemini training use but does NOT affect Google Search indexing or AI Overviews (those use `Googlebot`)
- Blocking `GPTBot` prevents OpenAI training but does NOT prevent ChatGPT from citing your content via browsing (`ChatGPT-User`)
- Blocking `PerplexityBot` removes a site from Perplexity's search index; it is not a training opt-out, because Perplexity says the bot does not collect training data
- Adoption figures for AI-specific robots.txt rules vary by study and sample; do not quote a percentage without naming the study

**Example — selective AI crawler blocking:**
```
# Allow search indexing, block AI training crawlers
User-agent: GPTBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: Bytespider
Disallow: /

# Allow all other crawlers (including Googlebot for search)
User-agent: *
Allow: /
```

**Recommendation:** Consider your AI visibility strategy before blocking. For Google generative AI Search, prioritize Googlebot crawlability, indexing, and snippet eligibility; `Google-Extended` controls Gemini training/product use and does not block Google Search indexing. Cross-reference the `seo-geo` skill for provider-scoped AI visibility optimization.

### 2. Indexability
- Canonical tags: self-referencing, no conflicts with noindex
- Duplicate content: near-duplicates, parameter URLs, www vs non-www
- Thin content: pages below minimum word counts per type
- Pagination: Google does not use `rel="next"`/`rel="prev"` for indexing (confirmed 2019, absent from current docs). Give each paginated page its own self-referencing canonical and plain `<a href>` links between pages; do not canonicalize every page to page 1
- Hreflang: correct for multi-language/multi-region sites
- Index bloat: unnecessary pages consuming crawl budget

### 3. Security
- HTTPS: enforced, valid SSL certificate, no mixed content
- Security headers:
  - Content-Security-Policy (CSP)
  - Strict-Transport-Security (HSTS)
  - X-Frame-Options
  - X-Content-Type-Options
  - Referrer-Policy
- HSTS preload: check preload list inclusion for high-security sites

### 4. URL Structure
- Clean URLs: descriptive, hyphenated, no query parameters for content
- Hierarchy: logical folder structure reflecting site architecture
- Redirects: no chains (max 1 hop), 301 for permanent moves
- URL length: flag >100 characters
- Trailing slashes: consistent usage

### 5. Mobile Optimization
- Responsive design: viewport meta tag, responsive CSS
- Touch targets: minimum 48x48px with 8px spacing
- Font size: minimum 16px base
- No horizontal scroll
- Mobile-first indexing: Google indexes mobile version. **Mobile-first indexing is 100% complete as of July 5, 2024.** Google now crawls and indexes ALL websites exclusively with the mobile Googlebot user-agent.

### 6. Core Web Vitals
- **LCP** (Largest Contentful Paint): target <2.5s
- **INP** (Interaction to Next Paint): target <200ms
  - INP replaced FID on March 12, 2024. FID was fully removed from all Chrome tools (CrUX API, PageSpeed Insights, Lighthouse) on September 9, 2024. Do NOT reference FID anywhere.
- **CLS** (Cumulative Layout Shift): target <0.1
- Evaluation uses 75th percentile of real user data
- Use PageSpeed Insights API or CrUX data if MCP available

### 7. Structured Data
- Detection: JSON-LD (preferred), Microdata, RDFa
- Validation against Google's supported types
- See seo-schema skill for full analysis

### 8. JavaScript Rendering
- Check if content visible in initial HTML vs requires JS
- Identify client-side rendered (CSR) vs server-side rendered (SSR)
- Flag SPA frameworks (React, Vue, Angular) that may cause indexing issues
- Verify dynamic rendering setup if applicable

#### JavaScript SEO — Canonical & Indexing Guidance

Google clarified three points in its JavaScript SEO basics documentation on December 15–18, 2025 (page last updated 2026-03-04; changelog entries verified 2026-09-03):

1. **Canonical conflicts:** "You shouldn't use JavaScript to change the canonical URL to something else than the URL you specified as the canonical URL in the original HTML." Keep the canonical identical between server-rendered HTML and JS-rendered output.
2. **noindex with JavaScript:** "When Google encounters the `noindex` tag, it may skip rendering and JavaScript execution, which means using JavaScript to change or remove the robots `meta` tag from `noindex` may not work as expected." Serve the correct robots directive in the initial HTML.
3. **Non-200 status codes:** "If the HTTP status code is non-200 (for example, on error pages with 404 status code), rendering might be skipped." Content or meta tags injected by JS on error pages may never be seen.
4. **Structured data in JavaScript:** *Not stated in Google's JS documentation.* Serving Product, Article and other structured data in the initial HTML remains the recommendation here because it removes rendering-queue dependency, but label it `Recommended`, not a documented Google requirement.

**Best practice:** Serve critical SEO elements (canonical, meta robots, structured data, title, meta description) in the initial server-rendered HTML rather than relying on JavaScript injection.

### 9. IndexNow Protocol
- Check if site supports IndexNow for Bing/Yandex freshness workflows
- Supported by participating search engines; do not present as a Google indexing signal
- Recommend implementation for faster URL change discovery on non-Google engines when the site publishes frequent updates
- Mark as `Optional` for stable brochure sites and `Recommended` for news, ecommerce, programmatic, or frequently updated sites

### 10. Provider Scope
- Label findings `Universal`, `Google-specific`, `Bing-specific`, `Regional`, or `Experimental`
- Treat PageSpeed, Search Console, and Googlebot findings as Google-specific unless the issue is also a general web/crawlability problem
- Treat Bing Webmaster Tools, Bingbot, AI Performance, and IndexNow findings as Bing-specific
- Run Yandex/Naver/Baidu checks only when the target market or user request warrants it

## Output

### Technical Score: XX/100

### Category Breakdown
| Category | Status | Score |
|----------|--------|-------|
| Crawlability | ✅/⚠️/❌ | XX/100 |
| Indexability | ✅/⚠️/❌ | XX/100 |
| Security | ✅/⚠️/❌ | XX/100 |
| URL Structure | ✅/⚠️/❌ | XX/100 |
| Mobile | ✅/⚠️/❌ | XX/100 |
| Core Web Vitals | ✅/⚠️/❌ | XX/100 |
| Structured Data | ✅/⚠️/❌ | XX/100 |
| JS Rendering | ✅/⚠️/❌ | XX/100 |

### Critical Issues (fix immediately)
### High Priority (fix within 1 week)
### Medium Priority (fix within 1 month)
### Low Priority (backlog)

---

## Voice Search Optimization

Voice search (Google Assistant/Gemini, Siri, Alexa) selects answers primarily from **Featured Snippets** and requires specific optimization signals.

### Key Facts
- The commonly cited figures (roughly 40% of voice answers from Featured Snippets, 46% local intent, mobile-dominant, fast TTFB favoured) come from third-party studies of 2018–2019 vintage (Backlinko, BrightLocal). No provider publishes voice-answer statistics. Label any of them `Hypothesis` in a report and do not present them as current measurements.
- Cortana was retired by Microsoft in 2023; do not list it as a target.

### Checklist

| Check | Requirement | Pass Threshold |
|-------|-------------|----------------|
| Page speed | TTFB < 2s (critical — voice results heavily favor fast pages) | < 2000ms |
| HTTPS | Required for voice results | Must be HTTPS |
| Featured Snippet | Direct answer in first 40-55 words after H-tag | Present |
| FAQ phrasing | H2/H3 phrased as natural language questions | ≥ 3 question H-tags |
| Local schema | LocalBusiness with address, phone, hours (local intent queries) | If local business |
| `speakable` schema | Marks top answer paragraphs for Google Assistant | Recommended |
| Mobile accessibility | 100% accessible on mobile | Required |

### `speakable` Schema Implementation
```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "speakable": {
    "@type": "SpeakableSpecification",
    "cssSelector": [".article-summary", "h2 + p", "[itemprop='description']"]
  }
}
```

### Voice Search by Platform

| Platform | Index Source | Primary Optimization |
|----------|-------------|---------------------|
| **Google Assistant / Gemini** | Google index | Featured Snippet ownership, fast TTFB, `speakable` |
| **Siri** | Google (web results since September 2017; image results from Bing) | Same as Google Search |
| **Alexa** | Bing | Featured Snippet, Bing indexed content, Bing Webmaster Tools |

> **Note**: For Alexa, submit your site via **Bing Webmaster Tools** (separate from Google Search Console). Siri's web answers come from Google, not Bing — the older "Siri = Bing" advice is out of date.

## Execution Plan

When invoked as an agent, execute these steps:
1. Run `scripts/robots_checker.py "$URL" --json` for crawlability and AI crawler rules.
2. Run `scripts/security_headers.py "$URL" --json` for security posture.
3. Run `scripts/redirect_checker.py "$URL" --json` to verify redirect chains.
4. Run `scripts/pagespeed.py "$URL" --strategy mobile --json` for Core Web Vitals mapping.
5. Run `scripts/hreflang_checker.py "$URL" --json` for international setup.
6. Run `scripts/indexnow_checker.py "$URL" --key YOUR_KEY --json` if applicable.
7. Synthesize all outputs into the Technical Score and Category Breakdown.
