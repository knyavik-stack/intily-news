# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE.** Core publication works end-to-end. The latest CI regression in the new image-hardening tests was identified precisely and fixed. The production runtime also received a compatibility correction for the legacy editor prompt, publication interval and joke policy. Fresh production evidence is still required for the corrected revision.

Production contract:

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics remain disabled (`SHOW_QUEUE_DIAGNOSTICS = False`).

## Latest fixes

### CI regression

Run #951 failed at the regression gate before publisher execution. The two new image-hardening tests mocked `extract_image_candidates()` as a list, while the production contract returns `(ranked_candidates, final_url)`. This caused:

`ValueError: not enough values to unpack (expected 2, got 1)`

Fixed in `5415478c418263ab3e8233ff731584a90b5ee198`.

### Editor prompt contamination

Inspection of the legacy publisher revealed that its historical `build_edit_prompt()` contained an unsuitable character instruction and excessive profanity requirements. That did not match the current editorial contract of natural Russian, factual writing and controlled humor.

A production runtime override was added in `scripts/sitecustomize.py` and committed in `1060cf2971855a4bd4daa7ec7d3aa4e39443b89e`.

The override now enforces:

- natural human Russian;
- factual, non-invented reporting;
- no excessive profanity instruction;
- humor only when contextually appropriate;
- no humor for serious safety/law/accident/harm/incident topics;
- joke target probability: **80%**;
- publication minimum interval: **3 minutes**;
- Groq runtime model: `openai/gpt-oss-20b`.

This is deployed in source but requires fresh production evidence.

## Groq

Historical production evidence showed retired `llama-3.1-8b-instant → 404 → svgmodel_not_found`.

Current runtime target is `openai/gpt-oss-20b`, loaded through `sitecustomize.py`.

Open gate: real fallback request must show `AI_PROVIDER_ATTEMPT GROQ` + `AI_PROVIDER_OK GROQ`, or a bounded correctly classified failure.

## Photo/media

Run #949 still produced text fallback (`found=0`, `validated=0`, `photo_sent=0`). The deployed media hardening adds browser-like retries, one-level HTML image indirection, nested candidate deduplication, 12s total fetch budget, 6s request timeout, Google-host prohibition and strict MIME/dimension/≤1 MB validation.

Open gate: real `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`.

If that remains unsuccessful, next step is first-class RSS/Atom media extraction (`media:content`, `media:thumbnail`, `enclosure`) passed into the image runtime. No random Google-image substitution.

## Scheduler / cadence

GitHub Actions uses `workflow_dispatch` only. Cloudflare is the scheduler.

The current versioned Cloudflare worker uses `* * * * *` UTC with a 1/3 dispatch gate. This is probabilistic dispatch, not a guaranteed 3- or 5-minute interval. Cadence must be confirmed from several real runs.

The Python runtime now has a 3-minute minimum publication interval. It does not create a scheduler by itself.

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

## Production evidence

### Run #949 — successful publisher

Proved 47 regression tests, Gemini editorial processing, Telegram text publication (`TELEGRAM_SENT 1134`), final-score queue invariant and state/analytics persistence.

Did not prove Groq fallback or photo delivery.

### Run #951 — failed regression gate

Stopped before publisher execution because of the image-hardening test mock contract defect. Corrected in `5415478...`.

## GREEN / YELLOW / RED

### 🟢 GREEN

- core Cloudflare → GitHub Actions → Python → Telegram architecture;
- Gemini primary;
- Telegram text delivery;
- durable state;
- queue/dedup/final-score invariant;
- main regression coverage;
- Groq runtime override loads current fallback model;
- editor runtime voice correction is implemented;
- image-hardening test mock contract is corrected.

### 🟡 YELLOW / OPEN

- fresh CI proof after the latest fixes;
- Groq live fallback proof;
- photo live proof;
- several consecutive scheduler cycles;
- media source resilience if publisher pages still reject candidates.

### 🔴 RED

No known critical blocker in the core architecture.

## Acceptance rule

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

Commit or unit-test success alone is never production proof.
