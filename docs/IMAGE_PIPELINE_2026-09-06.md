# INTILY Image Pipeline — 2026-09-06

## Status

Implemented in the production runner. The image layer is presentation-only and has a mandatory text fallback.

## Runtime flow

```text
selected article
  → resolve publisher URL (follow Google News redirect / canonical fallback)
  → publisher article HTML
  → OG / JSON-LD / image_src / Twitter / HTML image candidates
  → rank candidates and try them one by one
  → MIME + size + dimensions validation per candidate
  → Telegram sendPhoto(caption)
  → fallback to existing sendMessage on any image failure
```

## Resolver 2.0

The resolver no longer assumes that the first image candidate is usable.

Implemented safeguards:

1. Google News URLs are resolved to the real publisher page. If a wrapper does not redirect, canonical/`og:url` publisher references are attempted.
2. A Google News page is never accepted as the final article source.
3. Candidate extraction uses the standard-library HTML parser, so attribute order in `<meta>`/`<link>` tags does not matter.
4. Supported metadata includes `og:image`, `og:image:url`, `twitter:image`, `twitter:image:src`, `link rel=image_src`, and JSON-LD `image`/`contentUrl`.
5. Last-resort `<img>`, lazy-image attributes, and `srcset` candidates are supported.
6. Candidates are ranked by source quality and publisher-host affinity, with generic/logo/placeholder-looking URLs penalized.
7. Up to eight ranked candidates can be attempted; each candidate is independently downloaded and validated. A broken first candidate therefore no longer forces a text-only publication when a later valid article image exists.
8. No image candidate from Google News is accepted as the representative publisher image.

## Incidents covered

### SecurityLab

A real Intily publication was observed with a generic Google-like image instead of the article's representative image. The affected item originated from a Google News RSS link.

Root cause in the first media implementation: the RSS `link` was treated directly as an article page. The architectural fix is publisher URL resolution before image extraction.

### Tekedia

A second real chain was observed where the Tekedia article had a known representative image but Intily published without a photo. The article originated from a Google News RSS link and the expected publisher image was known from the article chain.

This exposed a second failure class: even after correct publisher URL resolution, selecting only one metadata candidate is brittle. Resolver 2.0 therefore extracts multiple candidate families and validates them independently before falling back to text.

These are source-agnostic fixes; no per-domain hardcoded image URL is used.

## Why the implementation is isolated

The legacy publisher remains the publication engine. `scripts/intily_ai_news_runner.py` injects the media behavior at runtime. This keeps existing queue/state/publication semantics unchanged while allowing the media layer to be tested and rolled back independently.

## Image source priority

1. `og:image` / `og:image:url`
2. JSON-LD `image` / `contentUrl`
3. `image_src`
4. `twitter:image` / `twitter:image:src`
5. publisher HTML image / lazy image / `srcset`
6. no acceptable image → text-only publication

RSS media extraction is intentionally not required for correctness: the publisher article remains the source of truth for the representative image.

## Validation

- HTTP fetch timeout is bounded.
- HTML fetch is capped at 2 MB.
- Image download is capped at 10 MB.
- Accepted image MIME types: JPEG, PNG, WebP, GIF.
- Minimum dimensions: 200×150.
- Image bytes are inspected for dimensions before upload.
- Telegram caption is rejected by the media path if it exceeds 1024 characters; the normal text sender is then used as fallback.
- No image is stored durably in the repository.

## Telegram delivery

The selected article is sent as one `sendPhoto` message with the existing HTML post as caption. If extraction, validation, or upload fails, the exact existing text publication path is used.

## Durable media analytics

Photo telemetry is now persisted into each bounded `run_history` record under `admission.image` so historical monitor windows can aggregate it without changing the legacy top-level KPI schema.

Per cycle:

- `attempts` — publication attempts for which image delivery was attempted;
- `found` — an acceptable image was resolved;
- `validated` — resolved image passed MIME/size/dimension checks;
- `photo_sent` — Telegram `sendPhoto` succeeded;
- `text_fallback` — publication used the normal text sender because media delivery failed;
- `fallback_reasons` — bounded error categories/messages;
- `sources` — extraction method used (`og_image`, `jsonld_image`, `image_src`, `twitter_image`, `html_img`);
- `last` — provenance of the last media attempt: resolved publisher URL, selected image URL, dimensions, method, and error if any.

Production Monitor now reports 24h, 7d, and stored-history values for:

- attempts;
- found;
- validated;
- photo sent;
- fallback;
- image resolution rate;
- Telegram photo rate;
- fallback rate;
- fallback reasons;
- image source methods.

The historical KPI is intentionally derived from durable cycle telemetry rather than from log scraping, so a rotated GitHub Actions log cannot erase the media history.

## Runtime markers

The implementation emits:

- `IMAGE_SOURCE_RESOLVED`
- `IMAGE_FOUND`
- `IMAGE_VALIDATED`
- `TELEGRAM_PHOTO_SENT`
- `IMAGE_FALLBACK_TEXT`
- `IMAGE_KPI`

For Google News items, `IMAGE_SOURCE_RESOLVED` must point to the publisher domain, not `news.google.com`.

## Important invariants

Image availability never changes editorial score, admission, duplicate handling, publication interval, or queue state. A strong story without an acceptable image remains publishable.

The image path is best-effort and must never turn a news story into a failed publication solely because its image is unavailable.

## Current limitation

Some publishers may block automated HTML access, require JavaScript rendering, or expose no representative image. Those cases intentionally fall back to text instead of failing the news publication.

## Verification requirement

A real production run must confirm the complete path:

`RSS → candidate → publisher URL resolution → image extraction → validation → Telegram photo/text fallback → durable state/analytics`.

A successful GitHub Actions run alone is not proof that an image was attached. Inspect `TELEGRAM_PHOTO_SENT` or `IMAGE_FALLBACK_TEXT`, and verify `IMAGE_KPI` was persisted into the resulting `run_history` entry.
