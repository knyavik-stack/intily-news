# INTILY Project Status — 2026-09-10

## Canonical current status

**🟡 PRODUCTION VERIFICATION MODE.** Core publication works end-to-end. Gemini is the confirmed primary AI provider. Groq is being migrated from a retired model to the currently supported free-tier `openai/gpt-oss-20b`. Photo delivery remains under live verification: the browser-like image retry is committed, but a real production `TELEGRAM_PHOTO_SENT` is still required before marking media GREEN.

## Current production contract

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram → durable GitHub state`.

## Provider status — verified against current Groq documentation on 2026-09-10

### Groq model incident

The production log showed:

`llama-3.1-8b-instant → 404 → svgmodel_not_found`

This is consistent with Groq's documented deprecation: `llama-3.1-8b-instant` was shut down on **2026-08-16**. Groq explicitly recommends `openai/gpt-oss-20b` as its replacement. The old model must not be used in production anymore.

The previous model was hard-coded in the legacy publisher. A production runtime override was therefore added in `scripts/sitecustomize.py`; because the workflow runs with `PYTHONPATH=scripts`, Python auto-loads the override before the production entrypoint imports the publisher.

Current runtime model:

`openai/gpt-oss-20b`

This model is listed by Groq as a production model and is included in the current Free Plan limits: **30 RPM, 1,000 RPD, 8K TPM, 200K TPD**. The same free-plan table also lists `openai/gpt-oss-120b`, `openai/gpt-oss-safeguard-20b`, `qwen/qwen3.6-27b`, and `qwen/qwen3.8-27b`. These are free-plan rate limits; Groq's separate Developer tier has paid token pricing. The project currently uses GPT-OSS 20B because it is the documented replacement for the retired Llama 3.1 8B and is production-class rather than preview.

The current production failover order remains:

1. Gemini — primary;
2. Groq GPT-OSS 20B — fallback;
3. OpenAI — fallback only when its key/quota is usable.

GitHub Models is not part of the fallback pool because GitHub retired the service on 2026-07-30.

## Groq model research conclusions

The user's supplied list is substantially aligned with Groq's current catalog, but it mixes production models, production systems, preview models, and speech models. It should not be treated as a single interchangeable pool.

- `openai/gpt-oss-20b` — production, current recommended fallback for retired Llama 3.1 8B; chosen for INTILY.
- `openai/gpt-oss-120b` — production and stronger, but not necessary for the current free-only fallback role.
- `openai/gpt-oss-safeguard-20b` — safety/moderation model; not a general editorial writer.
- `qwen/qwen3.6-27b` — preview, multimodal/vision capable; not the default fallback because it is a preview model.
- `qwen/qwen3.8-27b` — preview, multimodal/vision capable; not the default fallback for the same reason.
- `groq/compound` / `groq/compound-mini` — production systems, not ordinary text models; they add built-in tools and are unnecessary for INTILY's current editorial call.
- `meta-llama/llama-prompt-guard-2-22m` / `86m` — moderation/security models, not editorial generators.
- `canopylabs/orpheus-*` — speech/TTS models, not editorial text generation.
- `whisper-large-v3` — speech-to-text, not editorial text generation.

Groq's current documentation also confirms JSON mode for GPT-OSS 20B and strict Structured Outputs support, which makes it suitable for the publisher's JSON editorial contract. We are not enabling a new structured-output request shape in this change; the first objective is to restore a valid free fallback without changing the editorial pipeline simultaneously.

## Photo/media status

The last verified production run before the media hardening showed:

- image attempts: `1`;
- image found: `0`;
- image validated: `0`;
- Telegram photo sent: `0`;
- text fallback: `1`;
- source image request failed with HTTP 403.

A browser-like third fetch attempt was committed in `52b25d92971329fabb78092e340b1fb83eda0745`:

- Chrome-like User-Agent;
- Accept-Language;
- Referer;
- Sec-Fetch headers;
- candidate-by-candidate retry;
- Google-hosted image prohibition retained;
- MIME/dimension checks retained;
- Telegram 1 MB image cap retained.

This is an implementation fix, **not yet production proof**. The next authoritative verification is a real run with `photo_sent > 0` / `TELEGRAM_PHOTO_SENT`.

If publisher pages still reject all candidates, the next planned improvement is first-class extraction of RSS/Atom media fields (`media:content`, `media:thumbnail`, `enclosure`) before publisher-page extraction. No random Google-image substitution is allowed.

## Production verification rule

A green commit or green unit tests do not prove production readiness. For this project the acceptance sequence is:

**fact → root cause → implementation → tests → real production run → inspect telemetry → document result.**

## Current GREEN / YELLOW / RED

### GREEN

- Cloudflare → GitHub Actions → Python → Telegram architecture;
- Gemini production path;
- Telegram delivery;
- durable queue/state;
- deduplication;
- RSS/Google News discovery;
- analytics and production monitoring;
- Groq HTTP client User-Agent hardening;
- Groq model selection has been corrected in runtime to a currently supported free-plan model.

### YELLOW

- Groq GPT-OSS 20B still needs a real production request proving the account accepts it;
- image delivery still needs a real `TELEGRAM_PHOTO_SENT` proof;
- direct RSS has intermittent publisher errors such as VentureBeat HTTP 429;
- fresh-discovery/scoring supply remains under observation.

### RED

No known critical production blocker at the time of this update.
