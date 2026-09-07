# Intily Production Changelog — 2026-09-07 — Media 1 MB Hardening

## Problem
Intily had a publisher-first image resolver and Telegram photo path, but production proof of photo delivery was still missing. The implementation also used Telegram's API upload ceiling (10 MB) as its internal image-size ceiling. That is too large for the channel's intended media budget.

## Root cause found during verification
The latest pre-release workflow run (#503) failed in the CI regression suite before the publisher started. The failing test was an image fallback test coupled to the internal candidate-method label rather than the actual invariant that matters: a valid later publisher image must be selected after the first candidate fails.

## Changes implemented

1. Added `scripts/intily_image_runtime.py`.
2. Set Intily's outgoing image payload ceiling to **1,000,000 bytes**.
3. Bounded source image download at 8 MiB so optimization can operate on legitimate larger publisher images without unbounded downloads.
4. Added automatic resize/compression to JPEG when the source exceeds 1 MB.
5. Kept minimum dimensions at 200×150.
6. Preserved Google-hosted image rejection and publisher Referer retry.
7. Activated the runtime in production CI.
8. Activated the same runtime for direct runner invocation.
9. Added regression tests covering strict 1 MB output and optimized large images.
10. Added `IMAGE_PAYLOAD_BYTES` telemetry with source size and optimization flag.
11. Corrected the brittle image-pipeline regression test so it validates the successful fallback image URL and dimensions rather than an internal method label.
12. Updated canonical project status and CMO documentation.

## Acceptance criteria

A live production cycle is accepted only if it demonstrates:

```text
IMAGE_SOURCE_RESOLVED
→ IMAGE_FOUND
→ IMAGE_VALIDATED
→ IMAGE_PAYLOAD_BYTES <= 1,000,000
→ TELEGRAM_PHOTO_SENT
```

If the source image cannot be resolved, validated or optimized, the post falls back to text and records the exact reason. Google-hosted images are never accepted.

## Status

**Code: implemented.**

**CI: awaiting verification on the new commit.**

**Production: awaiting the next Cloudflare-triggered cycle for real Telegram photo proof.**
