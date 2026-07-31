<!-- Updated: 2026-07-28 -->

# Image Remediation Handoff

Use this contract when the `seo` skill needs `webp-me-daddy` to turn image SEO findings into concrete asset work.

## Workflow

1. Collect page evidence with `fetch_page.py` and `parse_html.py`, or inspect the HTML directly.
2. Generate a handoff file:

```powershell
python <SKILL_DIR>/scripts/image_handoff.py `
  page.html `
  --url https://example.com/post `
  --public-root C:/path/to/project/public `
  --output seo-image-handoff.json
```

3. Apply or preview the handoff in `webp-me-daddy`:

```powershell
python ~/.claude/skills/webp-me-daddy/scripts/webp_me_daddy.py `
  seo-handoff seo-image-handoff.json `
  --dry-run `
  --json seo-image-apply-report.json
```

## Root Shape

```json
{
  "version": "1.0",
  "generated_at": "2026-03-15T00:00:00+00:00",
  "producer": {
    "skill": "seo",
    "script": "image_handoff.py"
  },
  "page": {
    "url": "https://example.com/post",
    "title": "Post title",
    "context": "Post title",
    "slug": "post"
  },
  "defaults": {
    "public_root": "C:/site/public",
    "write_sidecar": true,
    "overwrite_recommended": true
  },
  "summary": {
    "image_count": 3,
    "ready_count": 2,
    "manual_count": 1,
    "high_priority_count": 1
  },
  "items": []
}
```

## Item Shape

Each item represents one page image that can be routed into `webp-me-daddy prepare`.

```json
{
  "id": "post.hero-image",
  "status": "ready",
  "priority": "high",
  "recipe": "hero-banner",
  "reasons": [
    "missing_alt",
    "next_gen_format_recommended",
    "missing_dimensions"
  ],
  "source": {
    "src": "/images/hero.jpg",
    "url": "https://example.com/images/hero.jpg",
    "path": "C:/site/public/images/hero.jpg",
    "public_relative_path": "images/hero.jpg",
    "resolved": true,
    "format": "jpg"
  },
  "metadata": {
    "accessibility_mode": "descriptive",
    "subject": "Hero Image",
    "context": "Post title",
    "purpose": "hero image",
    "visible_text": null,
    "usage_key": "post.hero-image",
    "usage_alt": "Hero Image for Post title"
  },
  "markup": {
    "loading": "eager",
    "fetch_priority": "high",
    "needs_dimensions": true,
    "needs_responsive_variants": true,
    "has_srcset": false,
    "has_sizes": false,
    "sizes": "100vw"
  },
  "page_asset_index": 1,
  "notes": []
}
```

## Status Rules

- `ready`: local still-image asset resolved under `public_root` and supported by `webp-me-daddy prepare`
- `manual`: unresolved local asset, animated asset, SVG, or another case that needs human review before applying fixes

## Notes

- Treat the handoff as a recommendation file, not an autonomous permission slip.
- Preview with `--dry-run` first when the handoff touches many assets.
- Keep the `seo` skill focused on diagnosis and prioritization; keep `webp-me-daddy` focused on asset generation and snippet output.
