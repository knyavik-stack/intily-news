# Intily Production Changelog — 2026-09-07 — Media 1 MB Hardening

## Product decision

Intily treats **1,000,000 bytes (1 MB decimal) as a hard image acceptance limit**.

- Image `<= 1,000,000` bytes: eligible for Telegram photo publication.
- Image `> 1,000,000` bytes: **reject; do not resize; do not recompress; do not rescue it**.
- If the image is rejected or otherwise unusable, the story may continue through the existing text-only fallback path.
- The 8 MiB source-read ceiling is only a safety bound for fetching source media; it is not an allowed delivery size.

## Problem

Intily had a publisher-first image resolver and Telegram photo path, but production proof of photo delivery was still missing. The previous runtime attempted to resize/compress oversized images to fit the 1 MB budget. That is not the desired product behavior.

## Changes implemented

1. `scripts/intily_image_runtime.py` now rejects any fetched image above 1,000,000 bytes with `IMAGE_TOO_LARGE`.
2. No resizing or recompression is performed by the runtime.
3. `scripts/test_intily_image_runtime.py` now verifies oversized images are rejected and small JPEGs pass unchanged.
4. The existing publisher-first resolver remains responsible for discovery, validation, Google-host rejection and source fetch limits.
5. The existing text fallback remains the expected behavior when media is unavailable.

## Acceptance rule

```text
candidate image
  → download
  → size <= 1,000,000 bytes ?
       YES → validate → sendPhoto
       NO  → reject → continue without this image
```

The product does not need an oversized image. It is not compressed merely to make it fit.

## Verification status

The code and regression tests have been updated. The latest known production Run #505 was green, but it predates this exact hard-reject change and did not publish a fresh qualifying story, so it cannot be used as proof of live photo delivery for this change.

The next Cloudflare-triggered production cycle is the final live verification gate for the media path.
