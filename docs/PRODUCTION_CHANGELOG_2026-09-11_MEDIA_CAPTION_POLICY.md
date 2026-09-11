# Production Changelog — 2026-09-11 Media Caption Policy

## Incident

A production post was observed with the article image as one Telegram message and the full editorial text as a second message. The image retrieval and Telegram delivery paths themselves were healthy; the split was caused by the Telegram `sendPhoto` caption limit.

## Root cause

Telegram photo captions are limited to 1024 **characters after entities parsing**. The project must not solve this by truncating editorial text or by intentionally publishing an image without its editorial context.

## Decision

The production media policy is now:

1. If the sanitized editorial text fits within 1024 visible Telegram caption characters, send the image and complete text as one `sendPhoto` message.
2. If it exceeds 1024 visible characters, skip the image and send the complete editorial text exactly once through the normal text sender.
3. If image retrieval, validation or photo delivery fails, fall back to the complete text.

This guarantees that an editorial unit is never published as an orphan image plus a second text message.

## Implementation

Commit `b4ddc428f517dbfc5dfdc2889bac61371c9c5d3b` adds the production no-orphan guard in `scripts/intily_audience_policy.py`.

The guard:

- sanitizes Telegram HTML before measuring;
- counts visible characters rather than UTF-8 bytes;
- logs `IMAGE_SKIPPED_CAPTION_LIMIT` for the long-post branch;
- calls the normal text sender exactly once;
- does not call `sendPhoto` for the long-post branch;
- reports `caption_mode=text_only_caption_limit`.

Regression tests were updated in commit `cc0fee92747d99b6a08cce25aebe849946a8a0eb`.

## Regression contract

Short post:

- `status=sent`;
- `caption_mode=full`;
- exactly one `sendPhoto` call;
- no text fallback.

Long post:

- `status=sent`;
- `caption_mode=text_only_caption_limit`;
- zero `sendPhoto` calls;
- exactly one full-text fallback call.

The existing Cyrillic regression remains important: Russian text may exceed 1024 UTF-8 bytes while remaining within Telegram's 1024-character caption limit and must still be accepted as a photo caption.

## Production acceptance still required

CI green is necessary but not sufficient. A fresh production run must confirm both branches where naturally exercised:

- a short Russian post with image attached in the same Telegram message;
- a genuinely long post with no image and exactly one complete text message.

The editorial prompt, scoring, scheduler and provider order are not changed by this fix.
