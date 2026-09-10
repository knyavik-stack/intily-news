# INTILY — START PROMPT FOR A NEW CHAT

Продолжаем существующий проект **INTILY Telegram AI News Publisher**. Ничего не начинать с нуля и не просить пользователя пересказывать историю.

## Обязательное начало

Самостоятельно изучить в GitHub `knyavik-stack/intily-news`:

1. `docs/PROJECT_STATUS_2026-09-10.md` — текущий канонический статус;
2. `docs/FINAL_PRODUCTION_AUDIT_2026-09-10.md` — последний production audit;
3. `docs/INTILY_OPERATIONS.md` — эксплуатационная модель;
4. `docs/USER_HANDOFF.md` — правила продолжения;
5. `docs/INTILY_PRODUCTION_MONITORING.md` — мониторинг;
6. текущий `main`, последние commits и GitHub Actions.

После чтения сразу работать по фактам.

## Главные правила

- Уже согласованные задачи выполнять самостоятельно.
- Если обнаружена проблема: **inspect → root cause → fix → verify → document**.
- Commit ≠ production evidence.
- Не ослаблять тесты ради зелёного CI.
- После существенного изменения обновлять документацию в GitHub.
- Не просить пользователя о ручном действии, если его доступ/секрет/авторизация реально не требуется.
- Не смешивать INTILY с другими проектами.
- Не использовать случайные внешние прокси или Google Images как источник фотографий.

## Текущий production-контур

`Cloudflare intily-ai-news scheduler → GitHub Actions workflow_dispatch → Python production entrypoint → Telegram @intily → durable GitHub state`

GitHub workflow не имеет собственного cron. Cloudflare является production scheduler.

## Текущий продуктовый контракт

- один production cycle публикует максимум одну новость;
- Telegram-пост содержит только редакционный контент;
- queue statistics / queue-next / operational diagnostics в постах отключены;
- AI provider failover: Gemini → Groq GPT-OSS 20B → OpenAI;
- discovery lookback: 12h;
- healthy-queue search interval: 30m;
- urgent search при queue ≤1;
- importance threshold: 60;
- durable queue cap: 20;
- RU target share: 60% при наличии достаточного качественного RU supply.

## Текущие открытые production gates

### P1 — CI regression closure

Последний run **#951** завершился failure на regression gate до запуска publisher. Причина была в тесте: mock `extract_image_candidates()` не соответствовал реальному контракту `(ranked_candidates, final_url)`. Исправление закоммичено в `5415478c418263ab3e8233ff731584a90b5ee198`.

Следующий исполнитель должен проверить свежий workflow run на исправленном commit.

### P2 — Groq live proof

Runtime override уже загружается как `openai/gpt-oss-20b`. Нужен реальный fallback request с telemetry `AI_PROVIDER_ATTEMPT GROQ` + `AI_PROVIDER_OK GROQ` либо корректно классифицированной ошибкой.

### P3 — Photo live proof

Image hardening включает browser-like retry, one-level HTML image indirection и bounded 12s fetch budget. Нужен реальный production `IMAGE_FOUND` → `IMAGE_VALIDATED` → `TELEGRAM_PHOTO_SENT`.

### P4 — Scheduler cadence

Текущий versioned Cloudflare worker использует cron `* * * * *` и 1/3 dispatch gate. Это не гарантированные 3 или 5 минут. Подтвердить cadence только по нескольким реальным GitHub workflow_dispatch runs.

## Что не делать

- не возвращать queue diagnostics в Telegram без отдельного решения пользователя;
- не считать зелёный commit доказательством production readiness;
- не возвращать retired `llama-3.1-8b-instant`;
- не объявлять photo pipeline GREEN до реального `TELEGRAM_PHOTO_SENT`;
- не удалять исторические monitoring failures — это audit trail.

## Формат отчёта

Коротко и по делу:

🟢 сделано
🟡 в работе / требует live verification
🔴 блокеры

Сначала выполнить максимально возможный объём работы, затем отчитаться.
