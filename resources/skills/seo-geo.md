---
name: seo-geo
description: >
  Optimize content for AI Overviews (formerly SGE), ChatGPT web search,
  Perplexity, and other AI-powered search experiences. Generative Engine
  Optimization (GEO) analysis including brand mention signals, AI crawler
  accessibility, llms.txt compliance, passage-level citability scoring, and
  platform-specific optimization. Use when user says "AI Overviews", "SGE",
  "GEO", "AI search", "LLM optimization", "Perplexity", "AI citations",
  "ChatGPT search", or "AI visibility".
---

<!-- Updated: 2026-07-28 -->

# AI Search / GEO Optimization

Read first:

- `resources/references/search-provider-canon.md`
- `resources/references/provider-guidance-matrix.md`
- `resources/references/google-ai-optimization-guide.md`
- `resources/references/bing-search-and-ai.md`

## Core Position

GEO is a useful workflow label, but provider behavior differs. For Google Search, generative AI visibility is still grounded in normal Search systems: crawlable, indexed, snippet-eligible, helpful, unique content with a good user experience. For Bing, use Bing Webmaster Tools and AI Performance data when available. For other AI systems, label emerging tactics as `Experimental` unless supported by official provider documentation.

Do not present `llms.txt`, AI-only rewrites, artificial chunking, or special AI schema as Google requirements.

---

## Provider-Specific Audit Model

| Provider Scope | What To Check | What Not To Claim |
|---|---|---|
| Google-specific | Crawlability, indexing, snippet eligibility, helpful unique content, page experience, JavaScript SEO, useful media, duplicate reduction. | Do not say Google requires `llms.txt`, AI-only markup, or special chunking. |
| Bing-specific | Bingbot access, Bing Webmaster Tools, AI Performance, IndexNow, sitemaps, duplicate/content quality. | Do not invent Bing AI citation status without Bing data. |
| Regional | Yandex/Naver/Baidu market fit, verification, crawling/indexing docs, language/locale signals. | Do not apply regional checks to every audit. |
| Experimental | `llms.txt`, AI content maps, third-party citation heuristics, platform-specific brand mention research. | Do not score as required without primary provider support. |

---

## GEO Analysis Criteria

### 1. Google AI Search Readiness

Provider scope: `Google-specific`

**Strong signals:**
- Important pages are crawlable and indexable.
- Pages can appear with snippets; snippets are not blocked accidentally.
- Main content is visible in rendered and source-accessible form.
- Content is helpful, distinct, and non-commodity.
- The page has clear headings, readable structure, and accurate metadata.
- Images/videos support the user task and are accessible.
- Duplicate pages are consolidated or clearly canonicalized.
- JavaScript-rendered content follows Google's JavaScript SEO guidance.

**Weak signals:**
- Client-only content that search crawlers cannot reliably discover.
- Thin or duplicated pages created mainly to capture variants.
- Generic text that adds no original value beyond existing search results.
- Blocked snippets or accidental noindex/canonical conflicts.

### 2. Bing AI And Search Readiness

Provider scope: `Bing-specific`

**Strong signals:**
- Bingbot can crawl important pages.
- Bing Webmaster Tools is configured.
- AI Performance reporting is available or recommended for review.
- IndexNow is configured for frequently changed URLs.
- XML sitemaps are submitted and current.
- Duplicate/near-duplicate content is reduced.

**Weak signals:**
- No Bing data access for claims about AI citations.
- Freshness-sensitive pages rely only on passive crawling.
- Important pages are orphaned or weakly linked.

### 3. Citability And Extractability

Provider scope: `Universal` or `Experimental`, depending on claim source.

Use this as a human readability and answer clarity check, not a hard Google AI ranking rule.

**Strong signals:**
- Direct answers near relevant headings.
- Claims backed by primary sources or visible evidence.
- Definitions and summaries that stand on their own.
- Tables, lists, and examples where they genuinely help users.
- Original research, experience, screenshots, product details, or expert perspective.

### 4. Authority And Entity Signals

**Strong signals:**
- Author byline with credentials
- Publication date and last-updated date
- Citations to primary sources (studies, official docs, data)
- Organization credentials and affiliations
- Expert quotes with attribution
- Entity presence in Wikipedia, Wikidata
- Mentions on Reddit, YouTube, LinkedIn

**Weak signals:**
- Anonymous authorship
- No dates
- No sources cited
- No brand presence across platforms

### 5. Technical Accessibility

Search and AI systems vary in rendering capability. Prefer crawlable HTML and server-rendered or statically rendered critical content for important pages.

**Check for:**
- Server-side rendering (SSR) vs client-only content
- AI crawler access in robots.txt
- `/llms.txt` presence and configuration as optional/experimental
- RSL/licensing terms only when relevant to publisher strategy

---

## AI Crawler Detection

Check `robots.txt` for these AI crawlers:

| Crawler | Owner | Purpose |
|---------|-------|---------|
| GPTBot | OpenAI | ChatGPT web search |
| OAI-SearchBot | OpenAI | OpenAI search features |
| ChatGPT-User | OpenAI | ChatGPT browsing |
| ClaudeBot | Anthropic | Claude web features |
| PerplexityBot | Perplexity | Perplexity AI search |
| CCBot | Common Crawl | Training data (often blocked) |
| anthropic-ai | Anthropic | Claude training |
| Bytespider | ByteDance | TikTok/Douyin AI |
| cohere-ai | Cohere | Cohere models |

**Recommendation:** Allow GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot for AI search visibility. Block CCBot and training crawlers if desired.

---

## llms.txt Standard

The emerging **llms.txt** standard provides AI crawlers with structured content guidance.

Provider scope: `Experimental/Optional`

Important: Google does not require `llms.txt` for Google Search generative AI features. Do not report a missing `llms.txt` file as a Google SEO failure.

**Location:** `/llms.txt` (root of domain)

**Format:**
```
# Title of site
> Brief description

## Main sections
- [Page title](url): Description
- [Another page](url): Description

## Optional: Key facts
- Fact 1
- Fact 2
```

**Check for:**
- Presence of `/llms.txt`
- Structured content guidance
- Key page highlights
- Contact/authority information

---

## RSL 1.0 (Really Simple Licensing)

New standard (December 2025) for machine-readable AI licensing terms.

**Backed by:** Reddit, Yahoo, Medium, Quora, Cloudflare, Akamai, Creative Commons

**Check for:** RSL implementation and appropriate licensing terms.

---

## Platform-Specific Optimization

| Platform | Key Citation Sources | Optimization Focus |
|----------|---------------------|-------------------|
| **Google AI Search** | Google Search index and ranking systems | Foundational SEO, helpful unique content, snippet eligibility, page experience |
| **Bing AI Search** | Bing-powered systems and Webmaster Tools reporting | Bingbot access, Bing Webmaster Tools, AI Performance, IndexNow |
| **ChatGPT / Perplexity** | Provider-specific web/search systems | Treat platform claims as experimental unless verified by official docs or observed citations |
| **Regional engines** | Provider and market specific | Activate only for target market or user request |

---

## Output

Generate `GEO-ANALYSIS.md` with:

1. **GEO Readiness Score: XX/100**
2. **Platform breakdown** (Google AIO, ChatGPT, Perplexity scores)
3. **AI Crawler Access Status** (which crawlers allowed/blocked)
4. **llms.txt Status** (present, missing, recommendations)
5. **Brand Mention Analysis** (presence on Wikipedia, Reddit, YouTube, LinkedIn)
6. **Passage-Level Citability** (answer clarity and extractability, not a hard Google AI rule)
7. **Server-Side Rendering Check** (JavaScript dependency analysis)
8. **Top 5 Highest-Impact Changes**
9. **Schema Recommendations** (for AI discoverability)
10. **Content Reformatting Suggestions** (specific passages to rewrite)

---

## Passage Indexing / Answer Clarity

Use passage-level checks to improve clarity and usefulness. Do not treat fixed word counts or artificial chunking as Google AI requirements.

### Rules for Passage-Optimized Content
1. **Self-contained sections**: Each H2 block should fully answer one clear question without requiring context from other sections
2. **Readable passage length**: keep sections concise enough to answer one user intent without forcing arbitrary word counts
3. **Question-answer structure**: Use question-phrased H2/H3 followed by a direct answer in the first sentence
4. **No pronoun-heavy openings**: Start sections with the full subject, not "It" or "This" referring to previous sections
5. **Speakable schema**: Add `speakable` CSS selectors for your top answer passages

### Speakable Schema Implementation

```json
{
  "@type": "WebPage",
  "speakable": {
    "@type": "SpeakableSpecification",
    "cssSelector": [".answer-block", "#key-definition", ".summary-paragraph"]
  }
}
```

### Passage vs Full-Page Ranking

| Scenario | Google Behavior |
|----------|----------------|
| Strong overall page, weak section | Full page ranks |
| Weak overall page, one excellent section | That **passage** can rank for specific queries |
| Long FAQ page with 20 questions | Individual Q&A passages rank independently |

---

## Quick Wins

1. Add "What is [topic]?" definition in first 60 words
2. Create self-contained answer blocks where they help users
3. Add question-based H2/H3 headings
4. Include specific statistics with sources
5. Add publication/update dates
6. Implement Person schema for authors
7. Confirm important pages are crawlable, indexable, and snippet-eligible

## Medium Effort

1. Create `/llms.txt` file only as optional/experimental AI content-map support
2. Add author bio with credentials + Wikipedia/LinkedIn links
3. Ensure server-side rendering for key content
4. Build real entity presence through authentic public profiles and references
5. Add comparison tables with data
6. Implement FAQ sections (structured, not schema for commercial sites)

## High Impact

1. Create original research/surveys (unique citability)
2. Build Wikipedia presence for brand/key people
3. Establish YouTube channel with content mentions
4. Implement comprehensive entity linking (sameAs across platforms)
5. Develop unique tools or calculators
