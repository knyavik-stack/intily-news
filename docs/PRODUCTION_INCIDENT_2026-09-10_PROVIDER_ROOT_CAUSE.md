# INTILY — production incident: AI providers and missing publications

**Дата:** 2026-09-10  
**Статус:** RESOLVED for Gemini / OpenAI requires secret rotation or credits

## Executive summary

Новости не публиковались не потому, что discovery сломался и не потому, что Telegram недоступен.

Основная непосредственная причина была в **persisted provider circuit state**: Gemini, Groq, OpenAI и GitHub Models были сохранены как disabled в durable state после предыдущих ошибок. Следующие production cycles не делали реального vendor request и сразу получали `*_CIRCUIT_OPEN`.

Run #900 использовал одноразовый recovery utility, очистил persisted provider circuits и сделал реальные запросы. Результат доказал:

- **Gemini реально работает**: несколько последовательных `AI_PROVIDER_OK GEMINI`;
- **Telegram реально работает**: `TELEGRAM_SENT 1096`, затем `PUBLISHED`;
- **OpenAI реально получает запрос**, но текущий GitHub Actions secret отвечает `HTTP 429` с сообщением `You have no credits remaining`;
- **Groq** отвечает HTTP 403 / code 1010;
- **GitHub Models** отвечает HTTP 410 `github_models_retirement_brownout`.

Таким образом, Gemini уже является рабочим production provider и способен поддерживать публикацию без OpenAI/Groq.

## Evidence

Run #899 до recovery:

- `AI_PROVIDER_BLOCKED GEMINI 16987`
- `AI_PROVIDER_BLOCKED GROQ 14447`
- `AI_PROVIDER_BLOCKED OPENAI 14174`
- `AI_PROVIDER_BLOCKED GITHUB_MODELS 14447`
- `BUSINESS_RESULT NO_PUBLISH no_eligible_item`

Это означало, что провайдеры даже не доходили до внешнего API.

Run #900 после recovery:

```text
AI_PROVIDER_RECOVERY_RESET ...
GEMINI remaining_seconds: 16608
GROQ remaining_seconds: 14067
OPENAI remaining_seconds: 13795
GITHUB_MODELS remaining_seconds: 14067
```

После очистки:

```text
AI_PROVIDER_ATTEMPT GEMINI
AI_PROVIDER_OK GEMINI
...
AI_PROVIDER_ATTEMPT GEMINI
AI_PROVIDER_OK GEMINI
...
AI_PROVIDER_ATTEMPT OPENAI
AI_PROVIDER_FAILED OPENAI OPENAI_HTTP_429: You have no credits remaining
```

Критический end-to-end результат:

```text
TELEGRAM_SENT 1096
PUBLISHED Anthropic Discloses Four Incidents of Claude Models Accessing Real Systems - Hokanews importance 71.0
BUSINESS_RESULT PUBLISHED telegram_delivery_ok
QUEUE_SCORE_AUDIT ... invariant_ok:true
```

## Root causes

### 1. Persisted circuit state became a recovery deadlock

Circuit breaker correctly защищал production от повторных неудачных vendor calls, но не имел безопасного operator recovery path. Поэтому смена/исправление API key не могла быть проверена до истечения cooldown.

### 2. OpenAI credential/billing issue remains

Production runner использует `secrets.OPENAI_API_KEY`. Сам secret не доступен для чтения через GitHub connector, поэтому его содержимое нельзя проверить напрямую.

Фактический внешний ответ текущего secret:

`HTTP 429 — You have no credits remaining.`

Следовательно, если Boss создал новый OpenAI API key, его необходимо установить именно в GitHub Actions secret `OPENAI_API_KEY`. Если новый key относится к той же организации без доступных credits, одна только ротация key проблему не решит.

### 3. Gemini is not blocked

После принудительного recovery Gemini успешно обработал editorial requests. Один отдельный request позже получил timeout, после чего следующий Gemini request снова успешно завершился. Это нормальный transient failure, а не подтверждение блокировки API.

## Remediation

- Added `scripts/intily_provider_recovery.py` as a one-shot emergency recovery utility.
- Added `scripts/test_intily_provider_recovery.py`.
- Verified recovery in live production run #900.
- Removed temporary recovery mode and temporary push trigger immediately after successful probe.
- Added recovery utility to normal CI test suite.
- Preserved durable queue and publication/story memory during recovery.

## Required manual action for OpenAI

Do **not** paste the key into chat.

In GitHub repository `knyavik-stack/intily-news`:

1. `Settings` → `Secrets and variables` → `Actions`.
2. Find `OPENAI_API_KEY`.
3. Replace it with the newly created OpenAI API key.
4. Save.

Then the next production cycle can test the new key. No other OpenAI secret is used by the workflow.

OpenAI documents that API keys are project-scoped and that usage/limits can be reviewed by project; API usage is shown in the Usage Dashboard, while credit balance is separate from usage. See the official OpenAI documentation.

## Current provider policy

Primary: **Gemini**.  
Fallback: Groq → OpenAI.  
Emergency GitHub Models fallback remains disabled by its observed HTTP 410 retirement brownout.

The Gemini runtime keeps bounded request timeout, minimum request spacing and retry behavior. Google's current documentation confirms that Gemini rate limits are project/model/tier dependent and that `429 quota_exceeded` differs from transient rate limiting.

## Acceptance after incident

- provider recovery: **PASS**
- real Gemini request: **PASS**
- real AI audience scoring: **PASS**
- Telegram delivery: **PASS**
- queue score invariant: **PASS**
- workflow timeout: **PASS**
- OpenAI current key: **FAIL — no credits**
- fresh-discovery acceptance: **pending next scheduled collection cycle**
