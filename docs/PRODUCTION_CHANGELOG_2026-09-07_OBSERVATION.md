# Production Changelog — 2026-09-07 Observation Cycle

## Changes

1. Final publication threshold changed from 60 to **55/100**.
2. Pre-AI gate remains **40/100**.
3. Audience score remains **1–10**, with exact linear bonus **+2…+20**.
4. Policy analytics and audience monitor now read live threshold constants rather than stale hard-coded 60 values.
5. Publisher settings/analytics documentation refreshed to distinguish current policy from historical records.
6. Image delivery remains strict **≤1,000,000 bytes** with no compression/resizing of oversized source images.
7. Hardened image resolver skips oversized candidates and continues to the next candidate.
8. Photo caption generation now strips source HTML, safely escapes the final text, and enforces the 1024-character limit after escaping.
9. Regression coverage added for the final escaped-caption length contract.

## Production verification

### Run #577

3m57s wall-clock. Search was skipped. The dominant latency was AI provider retry/failover: Gemini timeout/503, Groq 403/1010, OpenAI 429/no credits. The cycle ended with `PUBLISH_FAILED`; no evidence indicates RSS search was responsible for the delay.

### Run #578

~28s. A publisher image of 48,472 bytes was found and validated, but the old `CAPTION_TOO_LONG` guard blocked `sendPhoto`. This exposed a real media-delivery defect.

### Run #579

~15s. CI correctly stopped production execution because the new caption regression test found that HTML escaping could expand a nominally 1024-character raw caption to 1028 characters. This was fixed by bounding the escaped result itself.

## Next observation gate

The next production cycle must prove:

- all regression tests green;
- final gate 55 visible in runtime analytics;
- no `CAPTION_TOO_LONG` for a valid image;
- `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`;
- photo payload ≤1,000,000 bytes;
- oversized images skipped without transformation;
- durable state and analytics persist;
- provider degradation does not cause uncontrolled retry latency.

## Security/quality review

No new secret exposure was introduced. Provider keys remain environment secrets and are not written to telemetry. External media remains constrained by host policy, content type, dimensions and byte limits. Telegram payloads are bounded before delivery.
