# INTILY — AI News Publisher Operations

**Актуализация: 2026-09-12**

## 1. Production contract

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

GitHub Actions не использует собственный cron. Production scheduler — Cloudflare.

### Scheduler policy

Canonical worker source: `cloudflare/intily-ai-news.worker.js`.

Current source version: **6.0**.

Current cron: `*/5 * * * *` UTC.

The previous per-minute 1/3 random dispatch gate has been removed. Every Cloudflare scheduled tick at the five-minute boundary now attempts exactly one GitHub `workflow_dispatch` for `main`.

This gives a deterministic five-minute scheduler contract rather than a probabilistic average. Production cadence is considered restored only after the Worker is redeployed and several real workflow runs confirm it.

**Current incident:** GitHub evidence shows no production run after #1062 at 2026-09-11 12:32 UTC. The worker source was hardened in commit `29ced61d5ae78f1d699c98b64cf9abb0a016ff59`, but deployment to the live Cloudflare Worker is still required.

## 2. Publication contract

- максимум 1 публикация за production cycle;
- Telegram-пост содержит только редакционный материал;
- queue statistics / queue-next / operational diagnostics в посте отключены;
- целевой канал: `@intily`;
- ошибки одной новости не должны уничтожать остальные элементы durable queue.

Runtime setting:

`SHOW_QUEUE_DIAGNOSTICS = False`

## 3. Discovery

Основной discovery — Google News RSS search. Дополнительно используются прямые RSS publisher sources.

Текущие Python параметры:

- `LOOKBACK = 12h`;
- `SEARCH_INTERVAL_SECONDS = 30m` при здоровой очереди;
- немедленный поиск при `queue <= 1`;
- `IMPORTANCE_THRESHOLD = 60` до применения audience policy;
- `MAX_QUEUE = 20`.

Нулевой результат источника не считается технической ошибкой: важно различать отсутствие свежих материалов и `FEED_ERROR`.

## 4. Selection / dedup

Pipeline:

1. RSS fetch;
2. freshness filter;
3. deterministic relevance/importance score;
4. quality/relevance gate;
5. exact-item dedup;
6. semantic story dedup внутри discovery batch;
7. semantic dedup против durable queue;
8. semantic dedup против recent published story memory;
9. admission в durable queue;
10. AI editorial evaluation;
11. final score gate;
12. Telegram publication.

Canonical final-score invariant: очередь и публикация не могут отдавать приоритет pre-AI item над уже финализированным item с более высоким final score.

## 5. Durable state

Основной state: `data/intily-ai-news-state.json`.

В нём сохраняются queue, published history, semantic story memory, short-lived known-item memory, health/provider state и служебные telemetry fields.

State и production analytics сохраняются в GitHub после run. Исторические failure records не удаляются только ради улучшения KPI.

## 6. AI providers

Failover order:

1. Gemini — primary;
2. Groq `openai/gpt-oss-20b` — fallback;
3. OpenAI — fallback, если ключ/quota доступны.

Retired `llama-3.1-8b-instant` не использовать.

Runtime override в `scripts/sitecustomize.py` ограничен технической миграцией Groq model и не меняет editorial policy.

Требование production verification: реальный fallback должен дать `AI_PROVIDER_ATTEMPT GROQ` + `AI_PROVIDER_OK GROQ`, либо bounded correctly classified failure.

## 7. Media pipeline

Publisher-first media extraction:

`article URL → metadata/JSON-LD/HTML candidates → validation → Telegram sendPhoto → full editorial text`

Hardening:

- browser-like request headers;
- one-level HTML indirection;
- nested candidate deduplication;
- bounded fetch budget;
- Google-hosted image prohibition;
- MIME validation;
- minimum dimensions;
- Telegram payload cap ≤1 MB.

Caption handling is explicitly **no-truncation / no-orphan-image**:

- complete sanitized text **≤1024 visible Telegram characters** → `sendPhoto(caption=full_text)`;
- complete sanitized text **>1024 visible characters** → **do not call `sendPhoto`**; publish the complete unchanged editorial text exactly once through the existing Telegram text sender;
- image retrieval, validation or photo delivery failure → complete text fallback as before.

Telegram's `sendPhoto` caption limit is a character limit after entities parsing, not a UTF-8 byte limit. The runtime guard therefore measures visible characters after Telegram-style HTML sanitization/entity decoding.

## 8. Regression Gate reliability

The dedicated `Intily Regression Gate` is **non-production CI**. It must not be coupled to production state persistence.

Current policy:

- triggers on `scripts/**` or the regression workflow itself;
- does not trigger on `data/**` analytics/state commits;
- no Pillow installation is required by regression tests;
- image fixtures are generated with Python stdlib only;
- concurrency cancellation is limited to superseded regression changes.

Latest media-policy regression gate: **53/53 passed** in run `34592272934`.

## 9. Production evidence

Production run #1047 proved the ordinary image path: live editorial processing, real image retrieval/validation, `TELEGRAM_PHOTO_SENT`, Telegram publication and state/analytics persistence.

Production run #1062 completed successfully: 53 regression tests passed in the production preflight, Gemini successfully edited a live candidate, Telegram publication completed with `TELEGRAM_SENT`, `BUSINESS_RESULT PUBLISHED telegram_delivery_ok`, and `QUEUE_SCORE_AUDIT invariant_ok:true`.

Run #1062 did not exercise the long-caption branch because the selected post used text fallback due to unresolved article source.

No newer production run has been observed since #1062. This is the current live-scheduling incident, not evidence of a Python publisher failure.

## 10. Monitoring / incident response

When Telegram stops receiving posts:

1. inspect the latest GitHub production run timestamp;
2. if no recent run exists, inspect Cloudflare scheduler/Worker deployment before changing Python publisher code;
3. if a run exists, inspect its job logs and telemetry;
4. do not change editorial prompt, scoring or providers merely because scheduling is absent;
5. document the actual failure layer.

Required operational sequence:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

A green commit or unit test is not sufficient production evidence.
