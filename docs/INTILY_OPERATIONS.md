# INTILY — AI News Publisher Operations

**Актуализация: 2026-09-10**

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
- `IMPORTANCE_THRESHOLD = 60`;
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

Runtime override загружается через `scripts/sitecustomize.py` при production `PYTHONPATH=scripts`.

Требование production verification: реальный fallback должен дать `AI_PROVIDER_ATTEMPT GROQ` + `AI_PROVIDER_OK GROQ`, либо bounded correctly classified failure.

## 7. Media pipeline

Publisher-first media extraction:

`article URL → metadata/JSON-LD/HTML candidates → validation → Telegram sendPhoto → text fallback`

Hardening:

- browser-like request headers;
- one-level HTML image indirection;
- nested candidate deduplication;
- total fetch budget 12s;
- individual request timeout 6s;
- Google-hosted image prohibition;
- MIME validation;
- minimum dimensions;
- Telegram payload cap ≤1 MB.

Production acceptance requires telemetry:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`

If publisher pages continue to fail after the current hardening, next architectural step is first-class RSS/Atom media extraction (`media:content`, `media:thumbnail`, `enclosure`) passed into the image runtime. Random Google-image substitution is prohibited.

## 8. Current incident / CI gate

Run #951 failed correctly at the regression gate before publisher execution. Root cause: the new image-hardening tests mocked `extract_image_candidates()` as a list although the real function returns `(ranked_candidates, final_url)`.

Fixed in commit:

`5415478c418263ab3e8233ff731584a90b5ee198`

A fresh workflow run on the corrected commit is required before the CI gate can be considered green.

## 9. Production evidence

Run #949 proved end-to-end Telegram text publication, Gemini editorial processing, final-score queue invariant and state persistence. It did not prove Groq fallback or photo delivery.

Run #951 is a CI regression-gate failure and must not be interpreted as a Telegram/provider outage.

## 10. Monitoring

Publisher analytics describe the current cycle. Production Monitor describes historical health across cycles.

Required operational sequence:

**fact → root cause → implementation → tests → real production run → telemetry inspection → documentation**.

A green commit or unit test is not sufficient production evidence.
