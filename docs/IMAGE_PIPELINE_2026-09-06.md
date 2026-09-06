# INTILY Image Pipeline — 2026-09-06

## Status

Implemented in production runner. The image layer is presentation-only and has a mandatory text fallback.

## Runtime flow

```text
selected article
  → article HTML
  → og:image / twitter:image
  → image download
  → MIME + size + dimensions validation
  → Telegram sendPhoto(caption)
  → fallback to existing sendMessage on any image failure
```

## Why the implementation is isolated

The legacy publisher remains the publication engine. `scripts/intily_ai_news_runner.py` injects the media behavior at runtime. This keeps the existing queue/state/publication semantics unchanged while allowing the media layer to be tested and rolled back independently.

## Image source priority

1. `og:image`
2. `twitter:image`
3. No image → text-only publication

The current RSS parser does not persist media fields, so the first production implementation resolves the representative image from the article HTML. RSS media extraction can be added later as an optimization without changing Telegram delivery.

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

The implementation emits:

- `IMAGE_FOUND`
- `IMAGE_VALIDATED`
- `TELEGRAM_PHOTO_SENT`
- `IMAGE_FALLBACK_TEXT`

These markers are intended for production verification and future media KPI telemetry.

## Important invariant

Image availability never changes editorial score, admission, duplicate handling, publication interval, or queue state. A strong story without an acceptable image remains publishable.

## Current limitation

The first version resolves the image from article HTML. Some publishers may block automated HTML access, require JavaScript rendering, or expose no representative image. Those cases intentionally fall back to text instead of failing the news publication.

## Verification requirement

A real production run must confirm the complete path:

`RSS → candidate → article URL → image extraction → validation → Telegram photo → state/analytics`.

A successful GitHub Actions run alone is not proof that an image was attached; `TELEGRAM_PHOTO_SENT` or an explicit `IMAGE_FALLBACK_TEXT` must be inspected.
