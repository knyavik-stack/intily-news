# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE.** Core publication works end-to-end, but the latest production gate exposed a regression in the newly added image-hardening tests. The regression is now fixed in `5415478c418263ab3e8233ff731584a90b5ee198`; a fresh workflow run is required to prove the corrected gate and then the real media path.

The current production contract is:

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

Telegram posts contain **editorial content only**. Queue statistics, queue-next information and operational diagnostics remain disabled in posts (`SHOW_QUEUE_DIAGNOSTICS = False`).

## Latest incident — production gate regression

The first live run after adding the HTML-image-indirection tests was GitHub Actions **run #951**. It failed in the regression gate before the publisher started.

Root cause was precise and local: `scripts/test_intily_image_hardening.py` mocked `extract_image_candidates()` as a list, while the production function returns `(ranked_candidates, final_url)`. This caused:

`ValueError: not enough values to unpack (expected 2, got 1)`

Both affected tests used the wrong mock contract. No production publication was attempted in #951 because the regression gate correctly stopped the run.

The test contract was corrected in commit `5415478c418263ab3e8233ff731584a90b5ee198`.

**Required verification:** one fresh workflow run on the corrected commit must show the full regression suite passing and the publisher starting normally.

## Provider status

### Groq model incident

The production log previously showed:

`llama-3.1-8b-instant → 404 → svgmodel_not_found`

The old Groq model is retired. INTILY now uses `openai/gpt-oss-20b` as the Groq fallback through `scripts/sitecustomize.py`; the runtime override was observed in production logs as:

`GROQ_MODEL_RUNTIME_OVERRIDE openai/gpt-oss-20b`

The current production failover order remains:

1. Gemini — primary;
2. Groq GPT-OSS 20B — fallback;
3. OpenAI — fallback when its key/quota is usable.

GitHub Models is not part of the fallback pool.

**Open gate:** a real production fallback request must show `AI_PROVIDER_ATTEMPT GROQ` followed by `AI_PROVIDER_OK GROQ`, or a bounded and correctly classified Groq failure.

## Photo/media status

The last completed publisher run before the test-gate regression proved Telegram text delivery but still failed to attach a photo:

- image attempts: `1`;
- found: `0`;
- validated: `0`;
- Telegram photo sent: `0`;
- text fallback: `1`;
- publisher image candidates included invalid HTML responses.

### Media hardening deployed

`intily_image_hardening.py` now:

- keeps deterministic publisher-first extraction;
- keeps browser-like retries;
- follows one level of HTML image indirection when an image candidate actually returns HTML/XHTML;
- deduplicates nested candidates;
- caps the image retrieval budget at 12 seconds;
- caps individual image requests at 6 seconds;
- rejects Google-hosted image candidates;
- retains MIME, dimensions and Telegram ≤1 MB validation.

The implementation is deployed in GitHub. The first regression run exposed only the test-mock contract defect; that defect is now corrected.

**Open gate:** a real production post must show `IMAGE_FOUND`, `IMAGE_VALIDATED` and `TELEGRAM_PHOTO_SENT`.

If publisher-page extraction still fails after this corrected deployment, the next architectural step is first-class RSS/Atom media extraction (`media:content`, `media:thumbnail`, `enclosure`) passed into the image runtime. No random Google-image substitution is allowed.

## Production verification evidence

### Successful run #949

Run #949 proved:

- workflow/job completed;
- 47 regression tests passed at that revision;
- `GROQ_MODEL_RUNTIME_OVERRIDE openai/gpt-oss-20b` loaded;
- Gemini edited candidates successfully;
- Telegram publication succeeded: `TELEGRAM_SENT 1134`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics persisted.

It did **not** prove Groq live fallback and did **not** prove photo delivery.

### Failed run #951

Run #951 stopped at the regression gate because of the image-hardening test mock mismatch described above. This is a CI regression, not evidence of a provider or Telegram outage.

## Scheduler / cadence

GitHub Actions has **no cron**; the workflow is `workflow_dispatch` only. Cloudflare is the production scheduler.

The versioned Cloudflare worker currently uses a one-minute cron with a 1-in-3 dispatch gate. Therefore the dispatch interval is probabilistic rather than an exact five-minute cadence. Several consecutive real dispatches are required before declaring cadence stable.

Do not describe this as a guaranteed 5-minute or 3-minute interval without fresh production evidence.

## Editorial / queue policy

Current Python runtime values are authoritative over older historical documents:

- lookback: 12h;
- search interval when queue is healthy: 30m;
- urgent search when queue ≤1;
- maximum publication per cycle: 1;
- importance threshold: 60;
- queue cap: 20;
- Russian target share: 60% when sufficient qualifying RU supply exists;
- queue diagnostics in Telegram: disabled.

Final mathematical score remains the canonical ordering mechanism; geography must not manufacture a score advantage.

## GREEN / YELLOW / RED

### 🟢 GREEN

- Cloudflare → GitHub Actions → Python → Telegram architecture;
- Gemini primary path;
- Telegram text delivery;
- durable state persistence;
- queue/deduplication and final-score invariant;
- regression coverage for the main pipeline;
- Groq runtime override to a current fallback model is loaded;
- image-hardening test contract has been corrected in source.

### 🟡 YELLOW / OPEN

- **Fresh CI proof:** run the corrected regression gate after `5415478...`;
- **Groq live proof:** real fallback request;
- **Photo live proof:** real `TELEGRAM_PHOTO_SENT`;
- **Cadence proof:** several consecutive Cloudflare-dispatched cycles;
- image source resilience if the corrected hardening still cannot obtain a valid publisher image.

### 🔴 RED

No known critical blocker in the core publication architecture. The latest failure was a correctly caught test regression and has been fixed.

## Acceptance rule

Production readiness is closed only by:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

A green commit or unit test alone is never treated as production proof.
