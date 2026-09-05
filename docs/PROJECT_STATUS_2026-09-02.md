# SynapseMax — Project Status

**Дата:** 2026-09-02
**Статус:** production-capable RC, с одним наблюдаемым operational item.

## Что это за проект

SynapseMax — продуктовая веб-платформа с интерактивными диагностическими DEX-проходами и production-подсистемой Intily AI News Publisher. Репозиторий содержит сайт, frontend/runtime, QA-automation, Cloudflare deployment и автономный AI news pipeline.

## Архитектура

### Website

- Cloudflare Worker 'synapsemax' обслуживает production-сайт.
- Основные runtime-файлы: src/index.js, src/immediate-logic.js, index.html.
- Сборка и проверки находятся в scripts/.
- Visual/reference assets находятся в assets/.

### Quality system

GitHub Actions:
- Immediate QA — runtime/browser/quality gates.
- Production Smoke — production-level smoke verification.
- Intily AI News Publisher — запускается через workflow_dispatch; GitHub сам не содержит cron schedule для publisher.

Последние проверки на commit a42cf92 завершились успешно:
- Immediate QA — success;
- Production Smoke — success.

## Intily AI News Publisher

### Production flow

1. Один Cloudflare Worker 'intily-ai-news' запускается по cron '*/6 * * * *'.
2. Он dispatches GitHub workflow Intily AI News Publisher.
3. Python engine scripts/intily_ai_news.py собирает новости через Google News RSS.
4. Материалы проходят scoring, AI relevance, editorial value, freshness и story dedup.
5. Лучшие истории попадают в durable queue.
6. За один cycle публикуется максимум одна новость в Telegram.
7. State сохраняется обратно в data/intily-ai-news-state.json.

### Текущая policy

- freshness discovery: **6 часов**;
- MAX_PUBLISH: **1**;
- MIN_SCORE: **9**;
- target queue: **24**;
- hard queue cap: **30**;
- target mix: **60% WORLD / 40% RUSSIA**;
- Russia minimum queue reservation: **10**;
- story memory: **24 часа**;
- exact known-item memory: **6 часов**;
- failed queue items retry with exponential backoff from 5 minutes up to 6 hours.

### Тематика

Кроме model launches и крупных компаний, pipeline ищет:
- внедрение AI в бизнес;
- реальные кейсы и automation;
- AI workflows и productivity;
- продажи, маркетинг, финансы;
- healthcare, education, manufacturing, logistics;
- developer tools и coding;
- architecture, inference, latency, reliability и cost;
- безопасность, vulnerabilities, privacy, incidents и failures;
- funding, acquisitions, chips, robotics и research;
- российские AI-компании и практическое внедрение.

## Последние исправления

### Duplicate prevention

Исправлены syndicated duplicates: одна история, опубликованная несколькими СМИ с разными заголовками, теперь дополнительно ловится через:
- normalized title similarity;
- shared bigrams;
- named company/model anchors;
- queue-level story rebalance dedup.

Проверка реальной очереди после последнего изменения показала remaining_same_story_pairs = 0.

### Queue policy

Старые low-quality legacy items больше не должны сохраняться только потому, что когда-то прошли прежние правила. Durable queue revalidates current editorial policy.

### Cloudflare cleanup

Удалён Worker 'intily-news-trigger'. Перед удалением проверено:
- schedules: пусто;
- routes: отсутствуют;
- он дублировал news-trigger функцию.

После удаления inventory содержит только:
- intily-ai-news;
- neurogeroy;
- synapsemax.

intily-ai-news сохраняет единственный news cron '*/6 * * * *'.

## Фактический текущий state

На момент последней проверки GitHub state:
- published: 133;
- stories: 118;
- known: 69;
- queue: 22;
- WORLD queue: 20;
- RUSSIA queue: 2;
- last_published: 1;
- health: OK;
- consecutive_failures: 0.

## Что ещё требует наблюдения

### YELLOW — Russian supply

Алгоритм имеет target 60/40 и reserved Russian capacity, но текущая фактическая очередь всё ещё 20 WORLD / 2 RUSSIA. Это не повод публиковать слабые российские материалы ради цифры. Следующий инженерный приоритет — наблюдать несколько реальных циклов и, если дефицит сохраняется, добавить проверенные прямые RSS/API источники российских изданий вместо дальнейшего расширения broad Google queries.

### YELLOW — scheduler runtime observation

Cloudflare API подтверждает единственный cron '*/6', но после изменения scheduler необходимо продолжить наблюдение фактических GitHub workflow_dispatch runs на нескольких интервалах, чтобы подтвердить cadence именно по runtime evidence. Наличие schedule в API само по себе не считается достаточным доказательством.

## GREEN / YELLOW / RED

### GREEN
- production site deployed;
- GitHub CI работает;
- последние Immediate QA и Production Smoke — success;
- news discovery реально работает;
- Telegram publication подтверждался production state;
- AI provider failover работает;
- durable state работает;
- queue retry работает;
- duplicate protection усилена и проверена на queue;
- один duplicate Cloudflare Worker удалён;
- один canonical news scheduler '*/6' подтверждён API.

### YELLOW
- фактический 60/40 mix пока не достигнут в текущем queue snapshot;
- cadence нового Cloudflare cron требует ещё нескольких runtime cycles наблюдения.

### RED
- критических production blockers сейчас не выявлено.

## Правило для продолжения

Следующий исполнитель сначала проверяет факты, а не пересказывает старый план. После каждого изменения:

**inspect → root cause → fix → verify → document**

Нельзя считать commit доказательством production readiness.
