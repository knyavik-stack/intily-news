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

Image extraction order is now:

1. resolve the publisher URL by following the Google News RSS redirect;
2. `og:image`;
3. JSON-LD `image`;
4. `image_src`;
5. `twitter:image`;
6. text-only fallback.

Validation includes content type, maximum 10 MB, and minimum 200×150 dimensions. The existing text sender remains the fallback for every extraction/download/validation/upload failure.

The selected article URL is bound immediately before editorial rendering through a runtime wrapper around `edit()`. This avoids the incorrect approach of capturing the URL during priority sorting, where multiple candidates are evaluated.

## Incident found after real publication observation

A SecurityLab story published to Intily around 22:06 was observed with a generic Google-like image instead of the article's expected main image. The source article is SecurityLab's 21:45 story “Британия готовится к войне, где человек не успевает нажимать на спуск”; the expected image URL supplied for verification is the SecurityLab-hosted JPG.

Root cause: the first media implementation used the RSS `link` directly as the HTML page to scrape. For Google News RSS, that link is an aggregator/redirect URL. If the request remains on a Google News wrapper, the media layer can select a generic Google preview asset rather than the publisher's representative image.

Fix: the media layer now follows the URL and requires a real publisher final URL. If the final page is still `news.google.com`, it refuses to scrape that wrapper and falls back to text. It also records `IMAGE_SOURCE_RESOLVED` so production logs show the resolved publisher URL.

This is a general fix for Google News-originated items, not a SecurityLab-specific exception.

## CI verification

The production workflow compiles the new image module before running the publisher.

A GitHub Actions publisher run after the first media-module commit completed successfully (`run #407`, GitHub run `34053497700`). That run proves the repository/workflow could execute successfully with the first media module present, but it predates the final runner integration and the Google News source-resolution fix. It is **not** accepted as proof that the corrected Telegram photo delivery is working.

The acceptance test for the corrected integration is a production run containing one of:

- `TELEGRAM_PHOTO_SENT` — image path verified;
- `IMAGE_FALLBACK_TEXT` — media path handled a source/image limitation without breaking publication.

For Google News-originated articles, `IMAGE_SOURCE_RESOLVED` must point to the publisher domain and must not be `news.google.com`.

A green workflow without these markers is not considered media verification.

## Current status

- Source expansion: implemented; awaiting final runtime yield measurement.
- Image pipeline: corrected; awaiting final integrated production-cycle evidence.
- Editorial score threshold: remains operator-controlled at the user's current temporary value of 50 until calibration telemetry is sufficient.
- No scoring change is coupled to the media work.
