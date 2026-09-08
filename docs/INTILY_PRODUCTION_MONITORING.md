# Intily — производственный мониторинг и аналитика

**Актуализировано:** 2026-09-08

## Назначение

Production Monitor отделяет технический результат GitHub Actions от бизнес-результата издателя. `SUCCESS` означает, что workflow технически завершился; бизнес-метрика показывает, была ли фактически выполнена публикация.

## Актуальные редакционные пороги

- **Pre-AI gate: 40/100.**
- **Base score: 0–70.**
- **AI audience-fit: 1–10 → +3…+30.**
- **AI layer: 30% максимальной шкалы.**
- **Final publication gate: 55/100.**

Материал 40–54 проходит в AI-редактор, но не публикуется без итогового score ≥55. Финализированный <55 не должен оставаться в durable queue.

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
- **caption не обрезается**;
- если полный sanitized caption >1024, используется полный text-only fallback;
- если изображения нет или photo path не проходит, text fallback допустим при успешном editorial gate.

KPI `admission.image` должен различать: attempts, found, validated, photo_sent, text_fallback, fallback_reasons, source/method, dimensions и payload sizes.

## Queue monitoring

Критический invariant:

```text
score_stage=final  AND  score < 55  →  не допускается в durable queue
```

`pre_ai` 40–54 — нормальное состояние. Это означает, что AI ещё не добавил свои 30% оценки.

`final_below_threshold` должен быть 0. Run #680 показал четыре таких элемента в очереди; это теперь закрывается queue guard во время rebalancing.

## Мониторинг provider latency

Run #577 показал, что workflow может быть успешным, но занимать почти четыре минуты из-за AI provider retry/failover. Поиск был пропущен (`SEARCH_SKIPPED`), а задержку создали Gemini timeout/503, Groq 403/1010 и OpenAI 429/no credits.

Если все провайдеры недоступны, повторные попытки по каждому queued item не должны создавать неоправданную задержку. Контролируются `AI_PROVIDER_ATTEMPT`, `AI_PROVIDER_FAILED`, `AI_PROVIDER_BLOCKED`, retry count и итоговый provider usage.

## Production facts

Run #680 (`34219243075`) прошёл 21 regression test и опубликовал один материал на final 69.1. Это было ещё до перехода с ×2 на ×3 audience layer. Он также показал `final_below_threshold=4` и image HTTP 403 fallback.

После #680 исправлены:

- AI contribution ×2 → **×3**;
- base model → **0–70**;
- finalized queue <55 → удаление;
- длинный photo caption → полный text-only fallback вместо обрезания;
- сохранение Telegram HTML formatting;
- 1 MB candidate hard cap и candidate fallback.

Следующий production cycle должен подтвердить одновременно:

`IMAGE_FOUND → IMAGE_VALIDATED → TELEGRAM_PHOTO_SENT`

и сохранение полного текста/форматирования при допустимом photo caption.

## Географический портфель

Цель — примерно **40% RUSSIA / 60% WORLD** при наличии соответствующего качественного supply. География не меняет математическую релевантность новости.

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
