> **CANONICAL CURRENT STATE — 2026-09-06**
>
> This file contains historical operational material. The current production contract is: **Cloudflare `intily-ai-news` JavaScript scheduler → GitHub Actions `workflow_dispatch` → Python `scripts/intily_ai_news.py` → Telegram**. Cloudflare production is **not Python**.
>
> Cloudflare baseline source recovered from v54 (`8d9de9eb-7e28-4880-a46f-881fce654f8f`) is versioned in `cloudflare/intily-ai-news.worker.js`; production currently serves v87 (`b20948d7-c11c-4495-a9ca-421c9fb58dcc`), with the only intentional runtime change being the GitHub repository target `knyavik-stack/intily-news`. Cron is `* * * * *` UTC with the original 1/3 dispatch gate.
>
> Read `docs/PROJECT_STATUS_2026-09-06.md` and `docs/INTILY_RUNTIME_RESTORATION_2026-09-05.md` before making runtime changes. Those documents override older historical values in this file.

# SynapseMax — Инструкция для владельца проекта

## Где смотреть реальное состояние

1. GitHub Actions — последние результаты Immediate QA, Production Smoke и Intily AI News Publisher.
2. docs/PROJECT_STATUS_2026-09-02.md — актуальная карта проекта и GREEN/YELLOW/RED.
3. docs/INTILY_OPERATIONS.md — техническая эксплуатация news pipeline.
4. docs/NEW_CHAT_START_PROMPT.md — перенос контекста в новый чат.

## Для нового чата

Открой новый чат и отправь содержимое docs/NEW_CHAT_START_PROMPT.md. Новый исполнитель должен самостоятельно прочитать связанные документы и проверить текущий main, а не просить пересказывать историю.

## Когда вмешательство владельца действительно нужно

Только если:
- требуется новый секрет/API key;
- требуется авторизация внешнего сервиса;
- внешний сервис изменил доступ или требует ручного подтверждения;
- есть необратимое бизнес-решение, которое нельзя принять автоматически.

Во всех остальных случаях работа продолжается самостоятельно.
