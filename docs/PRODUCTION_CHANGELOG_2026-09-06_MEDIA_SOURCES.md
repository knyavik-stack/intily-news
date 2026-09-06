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

Image extraction order:

1. `og:image`;
2. `twitter:image`;
3. text-only fallback.

Validation includes content type, maximum 10 MB, and minimum 200×150 dimensions. The existing text sender remains the fallback for every extraction/download/validation/upload failure.

The selected article URL is bound immediately before editorial rendering through a runtime wrapper around `edit()`. This avoids the incorrect approach of capturing the URL during priority sorting, where multiple candidates are evaluated.

## CI verification

The production workflow now compiles the new image module before running the publisher.

A GitHub Actions publisher run after the first media-module commit completed successfully (`run #407`, GitHub run `34053497700`). That run proves the repository/workflow could execute successfully with the new module present, but it predates the final runner integration and therefore is **not** accepted as proof that Telegram photo delivery is working.

The acceptance test for the final integration is a production run containing one of:

- `TELEGRAM_PHOTO_SENT` — image path verified;
- `IMAGE_FALLBACK_TEXT` — media path handled a source/image limitation without breaking publication.

A green workflow without these markers is not considered media verification.

## Current status

- Source expansion: implemented; awaiting final runtime yield measurement.
- Image pipeline: implemented; awaiting final integrated production-cycle evidence.
- Editorial score threshold: remains operator-controlled at the user's current temporary value of 50 until calibration telemetry is sufficient.
- No scoring change is coupled to the media work.
