<!-- Updated: 2026-09-03 -->

# Search Provider Guidance Matrix

Use this matrix to keep audit recommendations honest when search providers differ. Do not present provider-specific guidance as universal SEO doctrine.

| Topic | Google Search | Bing / Microsoft Search | Other Providers | Skill Behavior |
|---|---|---|---|---|
| Generative AI visibility | Treat as normal SEO: crawlable, indexed, snippet-eligible, helpful, unique content. No special AI-only markup is required. | Bing exposes AI citation reporting through Webmaster Tools AI Performance and recommends clear structure, evidence, freshness, and IndexNow. | Yandex, Naver, Baidu, and DuckDuckGo guidance varies by market and published docs. | Label findings as `Google-specific`, `Bing-specific`, `regional`, or `experimental` instead of merging them. |
| `llms.txt` | Not required for Google generative AI features and not treated as special markup for Google Search. | May be useful for non-Google AI crawlers or internal content maps, but Bing guidance should not be overstated without a primary source. | Experimental ecosystem signal. | Optional only. Never make missing `llms.txt` a Google SEO failure. |
| AI crawler access | Google AI Search uses content from the Search index; focus on Googlebot crawlability and snippet eligibility. | Respect Bingbot and supported content controls; Bing AI experiences draw from Bing-powered systems. | Provider crawler names and controls differ. | Check crawler controls, but report blocked AI crawlers as provider-scoped and confidence-labeled. |
| IndexNow | Not a Google indexing signal. | Recommended for faster discovery of added, updated, or deleted URLs. | Supported by participating engines including Yandex. | Recommend for Bing/Yandex freshness workflows, especially news, ecommerce, programmatic, and frequently updated sites. |
| Structured data | Helps eligibility for rich results and page understanding; no special schema is required for generative AI. | Bing can use structured markup for understanding and diagnostics. | Support varies. | Recommend valid JSON-LD when it maps to real page content; avoid "AI schema" claims. |
| Content quality | Helpful, reliable, people-first, non-commodity content with original experience and clear organization. | Clear purpose, quality, credibility, relevance, freshness, and intent clarity. | Yandex and Naver also emphasize useful answers, usability, indexing, and site structure. | Prioritize human usefulness and distinct intent over keyword/page multiplication. |
| Duplicate content | Reduce duplication to improve user experience, crawling efficiency, and canonical clarity. | Duplicate and near-duplicate pages blur authority, intent, AI grounding, and freshness signals. | Similar concerns generally apply. | Flag as canonicalization, consolidation, and intent clarity work. |
| Page experience | Helpful across devices, low latency, clear main content, and Core Web Vitals context. | Usability and presentation contribute to quality/credibility signals. | Yandex/Naver emphasize usability and mobile-friendly access. | Treat as user experience plus crawl/render confidence, not a standalone ranking guarantee. |
| Regional engines | Google guidance is global but not sufficient for all markets. | Bing powers or influences several partner experiences. | Yandex, Naver, Baidu, and DuckDuckGo require market-specific handling. | Activate regional checks only when target market or user request warrants it. |

## Audit Language Rules

- Use `Required` only for eligibility, indexing, security, or policy blockers supported by primary provider docs.
- Use `Recommended` for provider-backed best practices that improve clarity, discoverability, or eligibility.
- Use `Optional` for useful enhancements that are not required for the scoped provider.
- Use `Experimental` for emerging AI-search tactics, third-party claims, or provider behavior without official documentation.
