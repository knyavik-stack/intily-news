# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE.** Core publication works end-to-end. The latest CI regression was fixed, the contaminated legacy editor prompt was corrected, and the next production run (#953) proved the corrected runtime loaded and published successfully. The photo pipeline has now been narrowed to a Telegram caption-length issue: a real valid image was found and validated, but the full caption exceeded Telegram's limit. A fresh production run after the latest 350-character prompt correction is required to close the photo gate.

Production contract:

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics remain disabled (`SHOW_QUEUE_DIAGNOSTICS = False`).

## Latest CI regression — fixed

Run #951 failed at the regression gate before publisher execution. The two new image-hardening tests mocked `extract_image_candidates()` as a list, while the production contract returns `(ranked_candidates, final_url)`. This caused:

`ValueError: not enough values to unpack (expected 2, got 1)`

Fixed in `5415478c418263ab3e8233ff731584a90b5ee198`.

A dedicated non-production `Intily Regression Gate` was added. Its run #2 on the latest media-caption commit completed successfully with **49 tests passed**.

## Latest production verification — run #953

Run #953 completed successfully on the corrected editor/runtime revision and proved:

- production regression gate passed: **49 tests**;
- `GROQ_MODEL_RUNTIME_OVERRIDE openai/gpt-oss-20b` loaded;
- `PUBLISH_INTERVAL_RUNTIME_OVERRIDE 180` loaded;
- `JOKE_RATE_RUNTIME_OVERRIDE 0.8` loaded;
- `EDITOR_PROMPT_RUNTIME_OVERRIDE clean_ru_voice` loaded;
- Gemini processed the live editorial candidates successfully;
- `TELEGRAM_SENT 1135`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

### Important media finding in #953

This run **did not fail image extraction**. It reached:

`IMAGE_PAYLOAD_BYTES 41356 source_bytes 41356 optimized False`

Then the image stage stopped with:

`IMAGE_FALLBACK_TEXT PHOTO_CAPTION_LIMIT_TEXT_FALLBACK`

Telemetry:

- attempts: 1;
- found: 0 at the final KPI layer;
- validated: 0 at the final KPI layer;
- photo sent: 0;
- text fallback: 1.

The underlying image payload was successfully obtained and was only 41 KB. The blocker was the full Telegram caption length, not the image URL, MIME type, dimensions or payload size.

## Media correction now deployed

The runtime editor prompt was tightened from a 700-character target to approximately **350 characters**, specifically so the complete editorial post can fit into a single Telegram photo caption under the 1024-byte caption limit.

Commit: `5f9a49ac83063957398c8267b124060e1d4fc00e`.

The non-production regression gate passed after this change.

**Open gate:** a fresh production post must show `IMAGE_FOUND`, `IMAGE_VALIDATED` and `TELEGRAM_PHOTO_SENT`.

If that still fails because of caption size, the next fix should be structural: make the photo caption intentionally compact while preserving the full editorial text as a separate message only if necessary. Do not silently truncate the editorial text and do not use random Google Images.

## Editor prompt correction

Inspection of the legacy publisher revealed an unsuitable historical prompt containing excessive profanity requirements and an inappropriate character instruction. That did not match the intended INTILY voice.

Runtime override in `scripts/sitecustomize.py` now enforces:

- natural human Russian;
- factual, non-invented reporting;
- no excessive profanity instruction;
- humor only where context permits;
- no humor for serious safety/law/accident/harm/incident topics;
- joke target probability 80%;
- publication minimum interval 3 minutes;
- Groq model `openai/gpt-oss-20b`.

Run #953 is live proof that these runtime overrides loaded.

## Groq

Historical evidence showed retired `llama-3.1-8b-instant → 404 → svgmodel_not_found`.

Current runtime target is `openai/gpt-oss-20b`.

**Open gate:** real fallback request must show `AI_PROVIDER_ATTEMPT GROQ` + `AI_PROVIDER_OK GROQ`, or a bounded correctly classified failure.

Run #953 used Gemini for all live editorial requests, so it still does not prove Groq fallback.

## Scheduler / cadence

GitHub Actions uses `workflow_dispatch` only. Cloudflare is the scheduler.

The versioned Cloudflare worker uses `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic dispatch, not a guaranteed 3- or 5-minute interval. Cadence must be confirmed from several real runs.

The Python publisher has a separate 3-minute minimum publication interval.

## Current editorial runtime

- discovery lookback: 12h;
- healthy-queue search interval: 30m;
- urgent search when queue ≤1;
- maximum publication per cycle: 1;
- importance threshold: 60;
- queue cap: 20;
- RU target share: 60% when sufficient qualifying RU supply exists;
- joke target probability: 80% where context permits;
- Telegram queue diagnostics: disabled.

## GREEN / YELLOW / RED

### 🟢 GREEN

- Cloudflare → GitHub Actions → Python → Telegram architecture;
- Gemini primary;
- Telegram text delivery;
- durable state;
- queue/dedup/final-score invariant;
- 49-test regression gate on the corrected revision;
- editor runtime voice correction is live-proven;
- image retrieval/validation reached a real 41 KB image in #953.

### 🟡 YELLOW / OPEN

- Groq live fallback proof;
- photo send proof after 350-character correction;
- several consecutive scheduler cycles;
- final cadence confirmation;
- media fallback architecture only if caption-bound production attempt still fails.

### 🔴 RED

No known critical blocker in the core architecture.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit or unit-test success alone is never production proof.
