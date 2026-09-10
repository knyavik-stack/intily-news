# INTILY — User Handoff

**Актуализация: 2026-09-10**

## Где смотреть реальное состояние

1. `docs/PROJECT_STATUS_2026-09-10.md` — канонический текущий статус.
2. `docs/FINAL_PRODUCTION_AUDIT_2026-09-10.md` — последний production audit.
3. `docs/INTILY_OPERATIONS.md` — текущая эксплуатационная модель.
4. `docs/INTILY_PRODUCTION_MONITORING.md` — исторический мониторинг и здоровье системы.
5. `docs/NEW_CHAT_START_PROMPT.md` — инструкция для нового чата.
6. GitHub Actions — фактические production runs и telemetry.

## Production contract

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

GitHub workflow не имеет собственного cron. Cloudflare — production scheduler.

## Пользовательский контракт Telegram

Пост содержит только редакционный контент. Queue statistics, queue-next и operational diagnostics в постах отключены:

`SHOW_QUEUE_DIAGNOSTICS = False`

## Текущее состояние

Core pipeline доказан end-to-end. Последний успешный publisher run #949 отправил Telegram message `1134` и сохранил state/analytics.

Последующий run #951 остановился на regression gate до запуска publisher. Причина — ошибка mock-контракта в двух новых image-hardening tests. Исправление закоммичено в `5415478c418263ab3e8233ff731584a90b5ee198`.

## Открытые production gates

1. свежий workflow run после `5415478...` с полным зелёным regression gate;
2. реальный Groq fallback на `openai/gpt-oss-20b`;
3. реальная photo delivery telemetry `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`;
4. несколько последовательных Cloudflare-dispatched cycles для подтверждения cadence.

## Provider policy

Failover: Gemini → Groq GPT-OSS 20B → OpenAI.

Retired `llama-3.1-8b-instant` не возвращать.

## Media policy

Publisher-first images only. Browser-like retries, one-level HTML indirection, bounded fetch budget and strict validation are enabled. Google-hosted image substitution запрещена.

Если текущая hardening-цепочка не даст реальную photo delivery, следующий шаг — first-class RSS/Atom media hints (`media:content`, `media:thumbnail`, `enclosure`).

## Когда нужен пользователь

Только если требуется:

- новый секрет/API key;
- авторизация внешнего сервиса;
- ручное подтверждение внешнего сервиса;
- необратимое бизнес-решение.

В остальных случаях исполнитель продолжает самостоятельно.

## Правило проверки

**fact → root cause → fix → tests → real production run → telemetry → documentation**.

Commit/CI green без production evidence не считается закрытием задачи.
