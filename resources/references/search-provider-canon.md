<!-- Updated: 2026-05-17 -->

# Search Provider Canon

Use official search-provider documentation before third-party SEO claims. When guidance comes from a specific provider, keep the recommendation scoped to that provider.

## Canonical Sources

| Provider | Primary docs | Use for |
|---|---|---|
| Google | https://developers.google.com/search/docs | General SEO, Search Essentials, crawling/indexing, structured data, snippets, page experience, Search Console, ecommerce, international SEO, Google AI Search guidance. |
| Bing / Microsoft | https://www.bing.com/webmasters/help/guidelines-30fba23a and https://support.microsoft.com/en-us/bing/how-bing-delivers-search-results | Bing crawling/indexing, ranking guidance, Bing Webmaster Tools, AI Performance, IndexNow workflows. |
| IndexNow | https://www.indexnow.org/documentation | Faster URL change notification for participating engines. |
| Yandex | https://yandex.ru/support/webmaster/en/recommendations/intro | Regional SEO for Yandex markets, content quality, indexing, snippets, site structure, and usability. |
| Naver | https://searchadvisor.naver.com/guide | Korean-market search visibility, Search Advisor setup, crawling/indexing, and site verification. |
| DuckDuckGo | https://duckduckgo.com/help/webmasters | Crawler identity, webmaster contact paths, and general inclusion behavior. DuckDuckGo does not publish a full SEO playbook comparable to Google/Bing. |
| Baidu | Baidu Search Resource Platform | Chinese-market SEO requires official Chinese-language review. Do not rely on weak secondary English summaries for client-critical recommendations. |

## Documentation Layers

Use these local references first:

- `resources/references/provider-guidance-matrix.md`
- `resources/references/google-ai-optimization-guide.md`
- `resources/references/bing-search-and-ai.md`
- `resources/references/indexnow.md`
- `resources/references/google-seo-reference.md`
- `resources/references/cwv-thresholds.md`
- `resources/references/schema-types.md`
- `resources/references/quality-gates.md`
- `resources/references/llm-audit-rubric.md`

## Provider Scope Labels

Every provider-sensitive finding should include one of:

- `Universal`: broadly supported across major search providers or basic web accessibility/crawlability.
- `Google-specific`: based on Google Search Central guidance or Search Console behavior.
- `Bing-specific`: based on Bing Webmaster, Microsoft Search, Bingbot, Bing Webmaster Tools, or IndexNow guidance.
- `Regional`: applies to market-specific engines such as Yandex, Naver, or Baidu.
- `Experimental`: emerging AI-search tactic or third-party claim without strong primary documentation.

## Conflict Rule

When providers differ, report the difference instead of smoothing it away. Example:

> `llms.txt` may be useful as an optional AI content map, but Google does not require it for generative AI Search. Treat it as `Experimental/Optional`, not a Google ranking requirement.

## Research Hygiene

- Prefer provider docs, official blogs, and webmaster tooling docs.
- Use third-party SEO studies only as context, never as hard requirements.
- Include source URLs and last-reviewed dates in new reference files.
- If a source cannot be verified from official documentation, label the recommendation `Hypothesis` or `Experimental`.
