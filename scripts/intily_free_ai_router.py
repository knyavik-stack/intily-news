"""Free-first production AI router for INTILY.

Technical policy only: editorial prompt and post format remain in intily_ai_news.py.
This wrapper reduces AI evaluations per cycle and adds OpenRouter's $0 free-model
router as an optional emergency provider. It never silently publishes unedited text.
"""

import json
import os
import time
import urllib.error
import urllib.request

import intily_ai_news as publisher
import intily_production_entrypoint as hardened
import intily_scoring_runtime_guard as guard


OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
OPENROUTER_MODEL = 'openrouter/free'
OPENROUTER_COOLDOWN_SECONDS = 6 * 3600
MAX_AI_EVAL_PER_CYCLE = 2


def _openrouter_chat(prompt, token):
    body = json.dumps({
        'model': OPENROUTER_MODEL,
        'messages': [
            {'role': 'system', 'content': 'Ты профессиональный редактор русского Telegram-канала об AI. Отвечай только валидным JSON.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.25,
        'max_tokens': 900,
        'response_format': {'type': 'json_object'},
    }).encode()
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        headers={
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/knyavik-stack/intily-news',
            'X-Title': 'INTILY AI News',
            'User-Agent': 'IntilyAI-News/8.0',
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode())
        content = data['choices'][0]['message'].get('content')
        if not content or len(content.strip()) <= 20:
            raise RuntimeError('OPENROUTER_EMPTY_OR_INVALID_CONTENT')
        return content
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode('utf-8', 'replace')
        raise RuntimeError(f'OPENROUTER_HTTP_{exc.code}: {raw[:500]}') from exc


def _quota_reason(name, message):
    lowered = message.lower()
    markers = (
        'tokens per day', 'rate limit reached', 'daily limit',
        'quota_exceeded', 'exceeded your current quota', 'no credits',
        'credits remaining', 'daily quota', 'insufficient_quota',
    )
    if any(marker in lowered for marker in markers):
        return 'DAILY_QUOTA_OR_CREDITS'
    if 'http_429' in lowered:
        return 'HTTP_429_RATE_LIMIT'
    if 'http_403' in lowered:
        return 'HTTP_403_PROVIDER_LIMIT'
    return None


def _block(name, state, message):
    reason = _quota_reason(name, message)
    if reason == 'DAILY_QUOTA_OR_CREDITS':
        cooldown = 24 * 3600
    elif reason:
        cooldown = publisher.PROVIDER_COOLDOWN.get(name, 3600)
    else:
        cooldown = 3600
    publisher.PROVIDER_COOLDOWN[name] = cooldown
    publisher.block_provider(state, name, reason or message[:180])


def _ai(prompt, state):
    telemetry = state.setdefault('_cycle_provider', {
        'attempts': [], 'used': None, 'failovers': 0, 'failures': 0,
        'blocked': 0, 'skipped_no_key': 0, 'retries': 0,
    })
    providers = [
        ('GEMINI', os.environ.get('GEMINI_API_KEY')),
        ('GROQ', os.environ.get('GROQ_API_KEY')),
        ('OPENROUTER', os.environ.get('OPENROUTER_API_KEY')),
        ('OPENAI', os.environ.get('OPENAI_API_KEY')),
    ]
    errors = []
    for name, token in providers:
        if not token:
            telemetry['skipped_no_key'] += 1
            print(name + '_SKIPPED_NO_KEY')
            continue
        if publisher.provider_blocked(state, name):
            telemetry['blocked'] += 1
            continue
        telemetry['attempts'].append(name)
        print('AI_PROVIDER_ATTEMPT', name)
        try:
            if name == 'GEMINI':
                result = hardened._gemini_chat(prompt, token)
            elif name == 'GROQ':
                result = hardened._groq_chat(publisher.GROQ_URL, publisher.GROQ_MODEL, token, prompt)
            elif name == 'OPENROUTER':
                result = _openrouter_chat(prompt, token)
            else:
                result = publisher.chat(publisher.OPENAI_URL, publisher.OPENAI_MODEL, token, prompt, 'OPENAI')
            if result and len(result.strip()) > 20:
                publisher.clear_provider(state, name)
                telemetry['used'] = name
                telemetry['failovers'] = max(0, len(telemetry['attempts']) - 1)
                print('AI_PROVIDER_OK', name)
                print('AI_PROVIDER_USAGE', json.dumps(telemetry, ensure_ascii=False, separators=(',', ':')))
                return result
            raise RuntimeError('EMPTY_RESPONSE')
        except Exception as exc:
            message = str(exc)
            errors.append(name + ': ' + message[:180])
            telemetry['failures'] += 1
            print('AI_PROVIDER_FAILED', name, message[:180])
            _block(name, state, message)
    raise RuntimeError('AI_PROVIDERS_UNAVAILABLE | ' + ' | '.join(errors))


def main():
    hardened.install_runtime_hardening()
    publisher.MAX_ATTEMPTS_PER_RUN = MAX_AI_EVAL_PER_CYCLE
    publisher.ai = _ai
    guard.AI_EVALUATION_DEADLINE = time.monotonic() + hardened.AI_EVALUATION_BUDGET_SECONDS
    print('AI_EVALUATION_BUDGET', int(hardened.AI_EVALUATION_BUDGET_SECONDS))
    print('AI_EVALUATION_CAP', MAX_AI_EVAL_PER_CYCLE)
    print('AI_FREE_ROUTER', OPENROUTER_MODEL, 'configured', bool(os.environ.get('OPENROUTER_API_KEY')))
    guard.run_production()


if __name__ == '__main__':
    main()
