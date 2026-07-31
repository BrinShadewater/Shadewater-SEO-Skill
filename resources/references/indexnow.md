<!-- Updated: 2026-05-17 -->

# IndexNow Reference

Source: https://www.indexnow.org/documentation  
Provider scope: Participating search engines, especially Bing and Yandex.

## What IndexNow Does

IndexNow is a protocol for notifying participating search engines when URLs are added, updated, or deleted. It is a discovery and freshness mechanism, not a ranking guarantee.

## When To Recommend It

Recommend IndexNow for:

- News, media, blogs, and other frequently updated content.
- Ecommerce inventory, pricing, availability, and product changes.
- Programmatic SEO pages where URLs are created or removed regularly.
- Sites targeting Bing or Yandex where freshness matters.
- Large sites where crawl budget or discovery latency is a known concern.

Treat IndexNow as optional for:

- Small brochure sites.
- Stable portfolios.
- Sites with very infrequent changes.
- Google-only audit scopes.

## Implementation Checklist

1. Generate a supported API key.
2. Host the key file at the site root or configured location.
3. Submit changed URLs through the IndexNow endpoint.
4. Submit only added, updated, or deleted URLs, not every URL on every deployment.
5. Log submission status and retry transient failures.
6. Keep XML sitemaps as a separate discovery mechanism.

## Audit Language

Use:

> IndexNow is recommended for Bing/Yandex freshness because this site publishes or changes URLs frequently.

Avoid:

> IndexNow is required for SEO rankings.
