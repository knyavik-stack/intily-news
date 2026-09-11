# INTILY — AI News Publisher Operations

**Актуализация: 2026-09-11**

## 1. Production contract

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

GitHub Actions не использует собственный cron. Production scheduler — Cloudflare.

Текущий versioned Cloudflare worker использует cron `* * * * *` UTC и 1/3 dispatch gate. Это вероятностная частота запуска, а не гарантированные 3 или 5 минут. Cadence считается подтверждённым только по серии реальных `workflow_dispatch` runs.

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

`article URL → metadata/JSON-LD/HTML candidates → validation → Telegram sendPhoto → text fallback`

Hardening:

- browser-like request headers;
- one-level HTML indirection;
- nested candidate deduplication;
- bounded fetch budget;
- Google-hosted image prohibition;
- MIME validation;
- minimum dimensions;
- Telegram payload cap ≤1 MB.

Production acceptance requires telemetry:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`

If the complete editorial post exceeds Telegram's 1024-byte photo-caption limit, the production guard rejects the photo caption rather than truncating or rewriting editorial content. The current open gate is a real successful photo-send path.

## 8. Regression Gate reliability

The dedicated `Intily Regression Gate` is **non-production CI**. It must not be coupled to production state persistence.

Current policy:

- triggers on `scripts/**` or the regression workflow itself;
- does not trigger on `data/**` analytics/state commits;
- no Pillow installation is required by regression tests;
- image fixtures are generated with Python stdlib only;
- concurrency cancellation is limited to superseded regression changes.

This removes the previous CI dependency on a mutable Pillow version for test-fixture generation and reduces workflow churn caused by production analytics commits.

Fresh green verification after commit `8c8b52d18705b1085a08b1d3a0fe5559844bfeb5` is required before this gate is considered closed.

## 9. Production evidence

Run #1018 completed successfully.

Historical run #1002 exposed the provider retry-budget defect; it was fixed in `75cdc250cf3e03546aa4583c74d047a61dfd1a3c` with regression coverage in `ae3d283e030f0d27324ec88f1157664608aa5853`.

## 10. Monitoring

Publisher analytics describe the current cycle. Production Monitor describes historical health across cycles.

Required operational sequence:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation.**

A green commit or unit test is not sufficient production evidence.
