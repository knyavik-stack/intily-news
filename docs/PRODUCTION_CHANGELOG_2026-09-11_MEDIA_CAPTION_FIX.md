# INTILY production changelog — 2026-09-11 media caption limit

## Incident observed

A live Telegram publication successfully delivered the article image, but the image appeared as a separate Telegram message from the editorial text.

Production run #1025 proves the exact behavior:

- `IMAGE_FOUND og_image 1200 630`
- `IMAGE_VALIDATED image/jpeg 274452`
- `TELEGRAM_PHOTO_SENT 1192`
- `TELEGRAM_SENT 1193`
- `TELEGRAM_FULL_TEXT_SENT_AFTER_PHOTO`
- `IMAGE_KPI` reported `photo_sent=1`, `text_fallback=0`.

The image pipeline therefore worked; the split path was selected because the caption guard rejected the full text.

## Root cause

The production caption guard compared the sanitized Telegram HTML string length against `1024` as if Telegram's limit were 1024 UTF-8 bytes.

Telegram Bot API defines `sendPhoto.caption` as **0–1024 characters after entities parsing**, not 1024 UTF-8 bytes.

This matters especially for Russian text because Cyrillic characters consume multiple UTF-8 bytes. A Russian caption can therefore be valid under Telegram's 1024-character limit while being larger than 1024 UTF-8 bytes.

Source: Telegram Bot API `sendPhoto` documentation.

## Fix

Commit `c446d916647953bcc679ba4e0d7a6d0abc31b26e` changes the production audience-policy caption guard to:

1. sanitize Telegram HTML;
2. remove HTML tags from the visible-text count;
3. HTML-unescape entities;
4. compare the resulting visible character count with the 1024-character limit;
5. retain the existing `PHOTO_CAPTION_LIMIT_TEXT_SPLIT` behavior only when the real character limit is exceeded.

The editorial text is still never truncated.

Regression coverage was added in `fe526dc508e02a168388a18e461bd41b81a00070`, with a Cyrillic fixture that is >1024 UTF-8 bytes but <1024 characters. The first fixture was intentionally corrected in `e19a01e6bbb481d7b385acb5573ddcff7b794fe4` after the test correctly exposed that the initial fixture itself exceeded 1024 characters.

## Verification

Regression Gate #32:

- run: `34571826952`
- commit: `e19a01e6bbb481d7b385acb5573ddcff7b794fe4`
- result: **success**
- full regression suite: **52 tests passed**

Production run #1026 was not accepted as media proof because it checked out the earlier `fe526dc...` head and failed in the pre-publisher policy/analytics check before the news engine executed. No `IMAGE_*` or Telegram publication telemetry from that run is used as evidence for this media fix.

## Acceptance condition still open

A fresh production run on the corrected `main` head must show:

- `IMAGE_FOUND`
- `IMAGE_VALIDATED`
- `TELEGRAM_PHOTO_SENT`
- preferably `caption_mode=full` / no `TELEGRAM_FULL_TEXT_SENT_AFTER_PHOTO` for a post that fits within 1024 Telegram caption characters.

For a genuinely >1024-character editorial post, Telegram cannot attach the entire text as one photo caption; the documented split behavior remains the safe no-truncation fallback.
