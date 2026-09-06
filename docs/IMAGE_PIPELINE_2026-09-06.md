# INTILY Image Pipeline — 2026-09-06

## Status

Implemented in the production runner. The image layer is presentation-only and has a mandatory text fallback.

## Runtime flow

```text
selected article
  → resolve publisher URL (follow Google News RSS redirect)
  → publisher article HTML
  → og:image / JSON-LD image / image_src / twitter:image
  → image download
  → MIME + size + dimensions validation
  → Telegram sendPhoto(caption)
  → fallback to existing sendMessage on any image failure
```

## Incident found on 2026-09-06

A real Intily publication from SecurityLab was observed with a generic Google-like image instead of the article's representative image. The affected item originated from a Google News RSS link; the expected SecurityLab image was the article image supplied by the user.

Root cause in the first media implementation: the image pipeline received the RSS `link` and treated it directly as an article page. Google News URLs are aggregator/redirect URLs, not the publisher article itself. If the request remained on a Google News wrapper, the pipeline could extract a generic Google preview image rather than the publisher's `og:image`.

The fix is architectural rather than a per-source exception:

1. Follow the RSS URL through normal HTTP redirects.
2. Require the final page to be a real publisher URL rather than `news.google.com`.
3. Do not scrape a Google News wrapper image when the publisher URL cannot be resolved.
4. Prefer publisher `og:image`, then JSON-LD image, `image_src`, and finally `twitter:image`.
5. Emit `IMAGE_SOURCE_RESOLVED` so production logs expose the actual publisher page used for extraction.

This prevents a Google News logo/preview asset from being silently accepted as the article's main image.

## Why the implementation is isolated

The legacy publisher remains the publication engine. `scripts/intily_ai_news_runner.py` injects the media behavior at runtime. This keeps the existing queue/state/publication semantics unchanged while allowing the media layer to be tested and rolled back independently.

## Image source priority

1. `og:image`
2. JSON-LD `image`
3. `image_src`
4. `twitter:image`
5. No image → text-only publication

The current RSS parser does not persist media fields, so the production implementation resolves the representative image from the publisher article HTML after resolving the publisher URL. RSS media extraction can be added later as an optimization without changing Telegram delivery.

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

- `IMAGE_SOURCE_RESOLVED`
- `IMAGE_FOUND`
- `IMAGE_VALIDATED`
- `TELEGRAM_PHOTO_SENT`
- `IMAGE_FALLBACK_TEXT`

These markers are intended for production verification and future media KPI telemetry.

## Important invariant

Image availability never changes editorial score, admission, duplicate handling, publication interval, or queue state. A strong story without an acceptable image remains publishable.

## Current limitation

Some publishers may block automated HTML access, require JavaScript rendering, or expose no representative image. Those cases intentionally fall back to text instead of failing the news publication.

## Verification requirement

A real production run must confirm the complete path:

`RSS → candidate → publisher URL resolution → image extraction → validation → Telegram photo → state/analytics`.

A successful GitHub Actions run alone is not proof that an image was attached; `TELEGRAM_PHOTO_SENT` or an explicit `IMAGE_FALLBACK_TEXT` must be inspected. For a Google News item, `IMAGE_SOURCE_RESOLVED` must point to the publisher domain, not `news.google.com`.
