# INTILY — User Handoff

**Актуализация: 2026-09-11**

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

Production run #1018 завершился успешно.

Последний CI-инцидент касался не production publisher, а Regression Gate: предыдущая конфигурация устанавливала Pillow только ради генерации тестовых изображений и запускалась на каждом push в `main`, включая production state/analytics commits. Сейчас regression fixtures полностью stdlib-only, Pillow из Regression Gate удалён, а workflow запускается только при изменениях `scripts/**` или самого gate workflow.

Commits:

- `58ae14dc266fd9d0449ee72dee1005d8aaccfc24` — изоляция Regression Gate;
- `8c8b52d18705b1085a08b1d3a0fe5559844bfeb5` — финальная deterministic fixture.

## Открытые production gates

1. свежий зелёный Regression Gate после CI hardening;
2. реальный Groq fallback на `openai/gpt-oss-20b`;
3. реальная photo delivery telemetry `IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`;
4. несколько последовательных Cloudflare-dispatched cycles для подтверждения cadence.

## Provider policy

Failover: Gemini → Groq GPT-OSS 20B → OpenAI.

Retired `llama-3.1-8b-instant` не возвращать.

## Media policy

Publisher-first images only. Browser-like retries, one-level HTML indirection, bounded fetch budget and strict validation are enabled. Google-hosted image substitution запрещена.

Если caption превышает Telegram limit, editorial text не режется и не переписывается. Текущий production path использует полный text-only fallback; photo-send remains an explicit verification gate.

## CI policy

Regression Gate — non-production. Production state commits under `data/**` не должны запускать regression suite. Тесты не должны зависеть от случайной версии Pillow или другого внешнего fixture-generation runtime.

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
