# Intily — производственный мониторинг и аналитика

**Актуализировано:** 2026-09-07

## Назначение

Production Monitor отделяет технический результат GitHub Actions от бизнес-результата издателя. `SUCCESS` означает, что workflow технически завершился; бизнес-метрика показывает, была ли фактически выполнена публикация.

## Где смотреть

### Publisher
GitHub → `intily-news` → **Actions → Intily AI News Publisher** → запуск → **Summary**.

Показывается только текущий cycle: вход, фильтры, кандидаты, admission, очередь, публикация, provider, audience-fit и media telemetry.

### Production Monitor
GitHub → **Actions → Intily Production Monitor → Run workflow**.

Показывается историческая картина: 24 часа, 7 дней, сохранённые циклы, публикации, причины отсутствия публикаций, source health, audience-fit, media delivery и provider/failover.

## Актуальные редакционные пороги

- **Pre-AI gate: 40/100.**
- **Final publication gate: 55/100.**
- AI audience-fit: **1–10**.
- Audience bonus: **+2…+20**, строго `audience_score × 2`.

Материал 40–54 проходит в AI-редактор, но не публикуется без итогового score ≥55.

## Media monitoring

Цепочка успеха:

```text
publisher article
→ publisher image candidate
→ candidate payload <= 1,000,000 bytes
→ validation
→ Telegram sendPhoto
```

Контрольные правила:

- Google-hosted image запрещено;
- Google News — только discovery transport;
- >1,000,000 bytes — hard reject, без сжатия и ресайза;
- oversized/broken candidate пропускается, следующий candidate проверяется;
- caption сохраняет поддерживаемую Telegram HTML-разметку исходной публикации;
- небезопасные HTML-теги/ссылки удаляются или обезвреживаются;
- caption ограничивается безопасной версией ≤1024 символов после escaping;
- если изображения нет или Telegram photo path не проходит, допускается text fallback при успешном editorial gate.

KPI `admission.image` должен различать: attempts, found, validated, photo_sent, text_fallback, fallback_reasons, source/method, dimensions и payload sizes.

## Мониторинг provider latency

Run #577 показал, что workflow может быть успешным, но занимать почти четыре минуты из-за AI provider retry/failover. В конкретном цикле поиск был пропущен (`SEARCH_SKIPPED`), а Gemini дал timeout/503, Groq — 403/1010, OpenAI — 429/no credits. Поэтому RSS не был причиной задержки.

Для дальнейшего наблюдения важны `AI_PROVIDER_ATTEMPT`, `AI_PROVIDER_FAILED`, `AI_PROVIDER_BLOCKED`, retry count и итоговый provider usage. Если все провайдеры недоступны, повторные попытки по каждому queued item не должны создавать неоправданную задержку.

## Production facts

Run #578 был значительно быстрее (~28 секунд) и успешно дошёл до publisher-hosted image: 48,472 bytes. Фото не ушло из-за старого `CAPTION_TOO_LONG`; этот guard заменён безопасным bounded Telegram-HTML caption path.

Run #579 остановился на regression gate примерно за 14 секунд: тест поймал ошибку, при которой длина caption контролировалась до escaping. Ошибка исправлена, и news engine в #579 не запускался.

После #579 дополнительно исправлена регрессия форматирования: предыдущий image caption helper превращал весь HTML-текст в plain text, поэтому пост с картинкой терял bold/italic/links/code. Теперь разрешённая Telegram HTML-разметка сохраняется, а небезопасная разметка санитизируется.

Следующий qualifying production cycle должен подтвердить одновременно:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`

и сохранение форматирования при payload ≤1 MB.

## Географический портфель

Цель — примерно **40% RUSSIA / 60% WORLD** при наличии соответствующего качественного supply. География не меняет математическую релевантность новости.

## Состояния

- `PUBLISHED` → **ОПУБЛИКОВАНО**
- `NO_PUBLISH` → **НЕ ОПУБЛИКОВАНО**
- `PUBLISH_FAILED` → **ОШИБКА ПУБЛИКАЦИИ**

## Правила безопасности и качества

- секреты не выводятся в telemetry/analytics;
- source-fetch ограничен отдельным техническим ceiling;
- Telegram payload изображения жёстко ограничен 1 MB;
- внешние HTML/image responses проходят content-type, host и dimension validation;
- analytics не делает дополнительных сетевых обращений к RSS/AI/Telegram;
- история bounded и хранится в durable state;
- невалидные provider responses не превращаются в публикации;
- GitHub Actions `SUCCESS` не трактуется как доказательство успешной публикации.

## Правило эксплуатации

**Проверить факты → найти причину → исправить → тесты → production verification → документация.**
