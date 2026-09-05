# START PROMPT FOR NEW CHAT — SYNAPSEMAX

Продолжаем **существующий SynapseMax project**. Ничего не начинай с нуля и не проси пользователя повторять историю.

## Обязательное начало

Самостоятельно прочитай в GitHub repository knyavik-stack/synapsemax:

1. docs/PROJECT_STATUS_2026-09-02.md — главный актуальный статус.
2. docs/INTILY_OPERATIONS.md — news production architecture.
3. docs/DECISION_LOG.md — принятые решения.
4. docs/PROJECT_OPERATING_SYSTEM.md — operating rules.
5. docs/RC_CHAT_TRANSITION_2026-08-30.md — RC continuity.
6. текущий main, последние commits и GitHub Actions.

После чтения **сразу работай по фактам**. Не выдавай пользователю длинный пересказ плана.

## Главные правила

- Пользователь хочет результат, а не разговоры о том, что будет сделано.
- Уже согласованные задачи выполнять самостоятельно.
- Если обнаружена проблема: inspect → root cause → fix → verify → document.
- Commit ≠ production evidence.
- Не ослаблять тест, чтобы получить зелёный CI.
- Документацию после существенных изменений обновлять в GitHub.
- Просить пользователя о действии только когда без его доступа/секрета/авторизации это реально невозможно.

## Текущая архитектура

### Website

Cloudflare Worker synapsemax, frontend/runtime в src/, build/QA в scripts/, visual assets в assets/.

### Intily AI News

Canonical production trigger:

Cloudflare Worker intily-ai-news → cron */6 * * * * → GitHub workflow_dispatch → scripts/intily_ai_news.py → Telegram → persisted state.

GitHub publisher workflow **не имеет собственного cron**.

Worker intily-news-trigger был проверен как duplicate: schedules пусты, routes отсутствовали, поэтому он удалён из Cloudflare.

## Текущая editorial policy

- freshness: 6h;
- MAX_PUBLISH: 1;
- MIN_SCORE: 9;
- target queue: 24; hard cap 30;
- target mix: 60% WORLD / 40% RUSSIA;
- Russian reserved capacity: 10;
- semantic story memory: 24h;
- known-item memory: 6h;
- failed items use exponential retry.

Тематика включает AI business adoption, automation, practical use, architecture, inference, reliability, cost, developer tools, security, incidents, robotics, chips, research, funding и российские AI кейсы.

## Последнее фактическое состояние

На последней проверке:
- published 133;
- stories 118;
- queue 22;
- WORLD 20 / RUSSIA 2;
- health OK;
- consecutive_failures 0.

Последние CI проверки на a42cf92:
- Immediate QA success;
- Production Smoke success.

## Открытые задачи

### Priority 1 — scheduler runtime evidence

Cloudflare API подтверждает один cron */6, но следующий исполнитель должен проверить несколько последующих фактических GitHub workflow_dispatch runs и подтвердить cadence.

### Priority 2 — Russian supply quality

Текущий queue snapshot не достиг 60/40. Не публиковать слабые новости ради квоты. Сначала наблюдать несколько реальных cycles. Если дефицит устойчивый — добавить проверенные прямые RSS/API российские источники и только затем корректировать policy.

### Priority 3 — RC / product roadmap

Продолжать только после сверки PROJECT_STATUS, DECISION_LOG, RC documents и фактического production evidence. Не начинать DEX v4 автоматически без visual approval DEX v3.

## Формат отчёта пользователю

Коротко:

🟢 сделано
🟡 в работе / требует наблюдения
🔴 блокеры

Но сначала выполнить максимально возможный объём работы, затем сообщать результат.
