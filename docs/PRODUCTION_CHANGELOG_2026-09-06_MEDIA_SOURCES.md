# INTILY Production Change Log — Sources + Media — 2026-09-06

## Approved scope

Implemented approved plan items:

1. add CNews, TechCult and Euronews to discovery;
5. implement article-main-image attachment;
6. production verification path;
7. documentation.

## Source changes

CNews, TechCult and Euronews are added to `DIRECT_RSS_FEEDS` at runtime by `intily_ai_news_runner.py`. They do not bypass scoring, quality, semantic deduplication or admission gates.

The three sources are visible in the existing direct-source telemetry (`RSS_DIRECT`, `source_counts`, `direct_raw_items`). Their incremental value must be judged after real cycles by unique admissions, not raw item count.

## Media changes

`scripts/intily_image_pipeline.py` implements best-effort article image extraction and Telegram `sendPhoto` delivery.

Resolver 2.0 now:

1. resolves Google News RSS links to the publisher page via redirects;
2. if the wrapper does not redirect, attempts canonical/`og:url` publisher references;
3. refuses to use `news.google.com` as the article source;
4. parses metadata with the standard-library HTML parser, so attribute order is not significant;
5. extracts `og:image`, `og:image:url`, JSON-LD image/contentUrl, `image_src`, Twitter image, lazy HTML images and `srcset`;
6. ranks candidates by source quality and publisher-host affinity and penalizes obvious logo/placeholder/generic assets;
7. validates candidates independently and tries up to eight candidates before falling back to text.

Validation includes content type, maximum 10 MB, and minimum 200×150 dimensions. The existing text sender remains the fallback for every extraction/download/validation/upload failure.

The selected article URL is bound immediately before editorial rendering through a runtime wrapper around `edit()`. This avoids capturing the URL during priority sorting, where multiple candidates are evaluated.

## Incidents found after real publication observation

### SecurityLab

A SecurityLab story published to Intily around 22:06 was observed with a generic Google-like image instead of the article's expected main image. The source article was a Google News-originated item.

Root cause: the first media implementation used the RSS `link` directly as the HTML page to scrape. For Google News RSS, that link is an aggregator/redirect URL.

Fix: publisher URL resolution is now mandatory; a Google News wrapper is never accepted as the image source.

### Tekedia

A second real chain was observed where a Tekedia article had a representative publisher image but Intily published without a photo. This exposed the next failure class: selecting only one metadata candidate is brittle even after publisher resolution.

Fix: Resolver 2.0 extracts multiple candidate families and validates them independently. No Tekedia-specific URL or exception was added.

## Durable media analytics

The runtime now persists image telemetry in every bounded `run_history` record under `admission.image`. The schema remains backward compatible with historical records that have no media block.

Recorded fields:

- `attempts`;
- `found`;
- `validated`;
- `photo_sent`;
- `text_fallback`;
- `fallback_reasons`;
- `sources`;
- `last` provenance containing resolved publisher URL, selected image URL, extraction method, dimensions and error when applicable.

Production Monitor now aggregates these metrics for 24h, 7d and stored history and shows resolution rate, Telegram photo rate, fallback rate, fallback reasons and extraction methods.

This is durable KPI telemetry, not log scraping.

## Regression tests

Added deterministic standard-library `unittest` coverage for:

- HTML metadata attribute-order variations;
- JSON-LD and lazy HTML image extraction;
- Google News canonical publisher fallback;
- retrying a later valid image when the first candidate is broken.

The production workflow now runs `py_compile` plus these tests before the news engine starts.

## CI / production verification

Run #423 (`34055888118`) was automatically triggered against commit `32b7ba0d5c5929a8f6cef272286f6ac58f88df29` after the media changes. At the latest inspection it was still running; its verification step had already completed successfully. Therefore syntax/regression-test execution is confirmed, while final Telegram media delivery from this run is not yet claimed until the publisher step finishes and its logs/state are inspected.

The earlier run #422 (`34055739496`) is not media verification for Resolver 2.0: it executed before the final media commits and published one text fallback with `ARTICLE_SOURCE_UNRESOLVED` under the older implementation.

Acceptance for the corrected integration remains:

- `TELEGRAM_PHOTO_SENT` — image path verified;
- or `IMAGE_FALLBACK_TEXT` — media limitation handled without breaking publication;
- for Google News-originated articles, `IMAGE_SOURCE_RESOLVED` must point to the publisher domain, never `news.google.com`;
- `IMAGE_KPI` must be present in the persisted `run_history` record.

A green workflow without these media markers is not considered full media verification.

## Current status

- Source expansion: implemented; runtime yield measurement continues.
- Image resolver 2.0: implemented with regression tests.
- Durable photo KPI analytics: implemented for current and historical monitor windows.
- Production workflow #423: in progress at the time of this documentation update; final Telegram evidence still pending.
- Editorial score threshold: remains operator-controlled at the user's current temporary value of 50 until calibration telemetry is sufficient.
- No scoring change is coupled to the media work.
