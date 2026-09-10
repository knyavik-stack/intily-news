# INTILY — Final Production Audit — 2026-09-10

## Executive status

**Overall readiness: 80% — YELLOW / production verification mode.**

The core publisher is operational end-to-end, but the project is not yet GREEN because media delivery is still failing in live production and the fallback-provider migration has not yet been proven by a real Groq request.

## Boss product decision

Publication posts must contain only editorial content. Queue statistics, queue-next information and operational diagnostics are **disabled for the Telegram post** and remain only in internal analytics/state. This is the intended production behavior.

Current publisher setting:

`SHOW_QUEUE_DIAGNOSTICS = False`

Operational analytics remain available through GitHub Actions / Production Monitor and durable state.

## Live production evidence

### Run #949

GitHub Actions run `949` completed successfully.

Verified:

- workflow/job completed successfully;
- media runtime installed;
- 47 regression tests passed;
- `GROQ_MODEL_RUNTIME_OVERRIDE openai/gpt-oss-20b` was loaded;
- Gemini successfully edited two candidates;
- Telegram publication succeeded: `TELEGRAM_SENT 1134`;
- `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`;
- `QUEUE_SCORE_AUDIT invariant_ok:true`;
- state and analytics were persisted successfully.

The run did **not** prove Groq because Gemini handled the live requests first.

## Groq

The old `llama-3.1-8b-instant` model generated a real `404 svgmodel_not_found` and is retired by Groq as of 2026-08-16.

Current production runtime model:

`openai/gpt-oss-20b`

Groq documentation confirms this is the recommended replacement and that it is included in Free Plan limits. Current Free Plan limits are 30 RPM, 1,000 RPD, 8K TPM and 200K TPD.

The current code now loads the replacement through `scripts/sitecustomize.py` before the production publisher starts.

**Remaining proof:** a real production cycle must show `AI_PROVIDER_ATTEMPT GROQ` followed by `AI_PROVIDER_OK GROQ` or a bounded, correctly classified Groq failure.

## Photos — current incident

Run #949 still failed to deliver a photo:

- `IMAGE_FALLBACK_TEXT`;
- `found: 0`;
- `validated: 0`;
- `photo_sent: 0`;
- `text_fallback: 1`;
- errors were dominated by `IMAGE_CONTENT_TYPE_INVALID` and `IMAGE_DIMENSIONS_INVALID` on `html_img` candidates.

The previous browser-like retry did not solve the production case.

### New media hardening

Commit `e34008658894ca76b2e4973365d1ec68ad32a0a2` adds:

- one-level HTML image indirection: if an image URL actually returns HTML, the runtime extracts image metadata/candidates from that response;
- browser-like request headers retained;
- total image-fetch budget capped at 12 seconds;
- individual image requests capped at 6 seconds;
- candidate deduplication for nested URLs;
- Google-hosted image prohibition retained;
- existing MIME, dimensions and <=1 MB Telegram payload validation retained.

This is intentionally a bounded hardening change: it improves both reliability and latency without introducing a new paid image service or an unverified external proxy.

**Remaining proof:** a real production post must show `IMAGE_FOUND`, `IMAGE_VALIDATED` and `TELEGRAM_PHOTO_SENT`.

## Latency / delays

Observed run #949:

- first Gemini editorial evaluation: about 3.7 seconds;
- second Gemini editorial evaluation: about 6.8 seconds;
- image stage consumed roughly 33 seconds before text fallback;
- Telegram send completed immediately after image fallback.

The image stage was therefore a material latency contributor. The new hardening caps it at 12 seconds for the retrieval phase.

## Search cadence

Current publisher constants use a 30-minute search interval when the durable queue is healthy, with immediate search pressure when the queue is critically low. Publishing and searching are intentionally separate concerns.

Run #949 explicitly reported `SEARCH_SKIPPED next_in 1259`, which is consistent with the 30-minute search interval and a healthy queue.

The production scheduler is external to GitHub Actions: Cloudflare dispatches the `workflow_dispatch` publisher workflow. GitHub Actions itself is not the scheduler.

## Editorial / analytics integrity

Verified from the live run:

- base scoring and audience scoring tests passed;
- 40.0 pre-AI threshold and 55.0 final publication gate are enforced by the canonical runtime;
- final-score queue invariant passed;
- AI audience scoring is recorded internally;
- RU/WORLD portfolio analytics remain internal and do not alter the final mathematical relevance score in the canonical runtime;
- Telegram posts do not need operational queue diagnostics.

The durable monitor currently reports historical 24-hour publication failures from the preceding incidents. Those historical failures must not be silently deleted or rewritten; they remain part of the audit trail. Current-run behavior is materially healthier than the historical aggregate.

## Remaining GREEN gates

1. **Groq live proof** — one real fallback request using GPT-OSS 20B.
2. **Photo live proof** — at least one real `TELEGRAM_PHOTO_SENT` after the new hardening.
3. **Observe several consecutive production cycles** without workflow failure, provider deadlock or media regression.
4. Confirm that publication cadence remains acceptable under normal queue conditions.

## Readiness calculation

- Core execution / GitHub Actions: GREEN
- Telegram delivery: GREEN
- Gemini primary: GREEN
- Editorial scoring / audience analytics: GREEN
- Queue / dedup / score invariant: GREEN
- State persistence: GREEN
- Groq replacement code: GREEN by static/runtime-load verification; live provider proof: OPEN
- Image pipeline: YELLOW
- Media latency: YELLOW, bounded fix deployed
- Scheduler cadence: YELLOW until several consecutive cycles are observed

**Final readiness: 80%.**

The project should be considered **production-capable but not yet fully GREEN** until the Groq fallback and photo publication are both demonstrated by real production evidence.
