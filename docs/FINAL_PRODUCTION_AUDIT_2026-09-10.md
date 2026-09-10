# INTILY — Final Production Audit — 2026-09-10

## Executive status

**Overall readiness: 80% — YELLOW / production verification mode.**

Core publication has been proven end-to-end. The remaining production gates are Groq live fallback, photo delivery and several consecutive scheduler cycles. A CI regression introduced by the new media tests was detected by the production gate and fixed before publisher execution could proceed.

## Product decision

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics are disabled in posts and remain internal.

`SHOW_QUEUE_DIAGNOSTICS = False`

## Latest incident — run #951

Run #951 completed with `failure`, but the publisher itself was **not started**: the regression gate stopped the job first.

The exact failure was in `scripts/test_intily_image_hardening.py`. The test mocked `extract_image_candidates()` as a list, while the production function returns `(ranked_candidates, final_url)`. This produced:

`ValueError: not enough values to unpack (expected 2, got 1)`

Both affected tests used the same incorrect mock contract.

### Fix

Commit `5415478c418263ab3e8233ff731584a90b5ee198` corrects both mocks to the real two-value return contract.

This was a genuine CI defect in the new tests, not a provider or Telegram outage. The gate behaved correctly by preventing a potentially unverified production run.

## Live production evidence — run #949

Run #949 proved:

- 47 regression tests passed at that revision;
- runtime loaded `GROQ_MODEL_RUNTIME_OVERRIDE openai/gpt-oss-20b`;
- Gemini successfully edited candidates;
- Telegram publication succeeded: `TELEGRAM_SENT 1134`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

Run #949 did not prove a real Groq fallback because Gemini handled live requests first. It also did not prove photo delivery.

## Groq gate

The retired `llama-3.1-8b-instant` produced the historical real `404 svgmodel_not_found`. Production runtime now targets `openai/gpt-oss-20b` through `scripts/sitecustomize.py`.

Required closure evidence:

`AI_PROVIDER_ATTEMPT GROQ` → `AI_PROVIDER_OK GROQ`

or a bounded, correctly classified Groq failure.

## Photo gate

The previous live run still ended in text fallback:

- found: `0`;
- validated: `0`;
- photo sent: `0`;
- text fallback: `1`.

The deployed hardening adds:

- browser-like retries;
- one-level HTML image indirection;
- nested candidate deduplication;
- 12s total image-fetch budget;
- 6s individual request timeout;
- Google-hosted image prohibition;
- MIME/dimension checks;
- Telegram ≤1 MB payload cap.

Required closure evidence:

`IMAGE_FOUND` → `IMAGE_VALIDATED` → `TELEGRAM_PHOTO_SENT`

If this still fails in live production, implement first-class RSS/Atom media extraction (`media:content`, `media:thumbnail`, `enclosure`) and pass those hints into the image runtime. Do not use random Google Images as a fallback.

## Cadence

GitHub Actions is `workflow_dispatch` only. Cloudflare is the scheduler.

The current versioned worker uses `* * * * *` with a 1/3 dispatch gate. This is probabilistic dispatch, not a guaranteed 3- or 5-minute interval. Cadence must be judged from several real workflow runs, not from the cron expression alone.

## Current editorial runtime

- discovery lookback: 12h;
- healthy-queue search interval: 30m;
- urgent search: queue ≤1;
- max publish per cycle: 1;
- importance threshold: 60;
- queue cap: 20;
- RU target share: 60% when enough qualifying RU supply exists;
- Telegram queue diagnostics: disabled.

## Remaining production gates

1. Fresh regression run on commit `5415478...` with all tests passing.
2. Real Groq fallback proof.
3. Real Telegram photo proof.
4. Several consecutive successful scheduler-dispatched cycles.
5. Confirm acceptable publication cadence under normal queue conditions.

## Final assessment

**80% — YELLOW. Production-capable, but not fully GREEN.**

Acceptance remains:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

A commit or green unit test is never treated as production evidence by itself.
