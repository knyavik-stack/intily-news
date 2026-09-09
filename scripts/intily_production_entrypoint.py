"""Canonical production entrypoint hardening the legacy publisher at runtime.

This adapter is intentionally small and sits before the scoring runtime guard.
It fixes legacy collection/provider behavior and provides a GitHub Models
fallback when all external API providers are unavailable.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import intily_ai_news as publisher
import intily_scoring_runtime_guard as guard


CANONICAL_PRE_AI_THRESHOLD = 40.0
GEMINI_QUOTA_COOLDOWN_SECONDS = 6 * 3600
GEMINI_MIN_REQUEST_INTERVAL_SECONDS = 5.0
GEMINI_RETRY_DELAYS_SECONDS = (2.0, 4.0, 8.0, 16.0)
GEMINI_MAX_PROMPT_CHARS = 12000
GITHUB_MODELS_COOLDOWN_SECONDS = 6 * 3600
GITHUB_MODELS_URL = 'https://models.github.ai/inference/chat/completions'
GITHUB_MODELS_MODEL = 'openai/gpt-4o'
AI_EVALUATION_BUDGET_SECONDS = 180.0
GEMINI_REQUEST_TIMEOUT_SECONDS = 20

_gemini_last_request_at = 0.0
_active_provider_state = None


def _wait_for_gemini_slot():
    """Keep Gemini comfortably below a 15-RPM-style ceiling between calls."""
    global _gemini_last_request_at
    now = time.monotonic()
    wait = GEMINI_MIN_REQUEST_INTERVAL_SECONDS - (now - _gemini_last_request_at)
    if wait > 0:
        time.sleep(wait)
    _gemini_last_request_at = time.monotonic()


def _compact_gemini_prompt(prompt):
    """Bound model context without exceeding the configured character limit."""
    if not isinstance(prompt, str) or len(prompt) <= GEMINI_MAX_PROMPT_CHARS:
        return prompt
    truncation_marker = "\n[CONTEXT_TRUNCATED]\n"
    available_chars = GEMINI_MAX_PROMPT_CHARS - len(truncation_marker)
    head = available_chars * 2 // 3
    tail = available_chars - head
    return prompt[:head] + truncation_marker + prompt[-tail:]


def _gemini_chat(prompt, token):
    """Rate-limit Gemini and retry only transient 429s with bounded exponential backoff."""
    prompt = _compact_gemini_prompt(prompt)
    last_error = None

    for retry_index in range(len(GEMINI_RETRY_DELAYS_SECONDS) + 1):
        _wait_for_gemini_slot()
        body = json.dumps({
            'systemInstruction': {
                'parts': [{
                    'text': 'Ты профессиональный редактор русского Telegram-канала об AI. Отвечай только валидным JSON.'
                }]
            },
            'contents': [{
                'role': 'user',
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'temperature': 0.25,
                'maxOutputTokens': 900,
                'responseMimeType': 'application/json'
            }
        }).encode()

        url = publisher.GEMINI_URL + '?key=' + urllib.parse.quote(token, safe='')
        req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})

        try:
            with urllib.request.urlopen(req, timeout=GEMINI_REQUEST_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode())
            return data['candidates'][0]['content']['parts'][0]['text']
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode('utf-8', 'replace')
            last_error = RuntimeError(f'GEMINI_HTTP_{exc.code}: {raw[:500]}')
            if exc.code != 429:
                raise last_error

            lowered = raw.lower()
            quota_exhausted = (
                'quota_exceeded' in lowered
                or 'exceeded your current quota' in lowered
                or 'daily quota' in lowered
            )
            if quota_exhausted or retry_index >= len(GEMINI_RETRY_DELAYS_SECONDS):
                raise last_error

            delay = GEMINI_RETRY_DELAYS_SECONDS[retry_index]
            print('GEMINI_RETRY', int(delay), 'transient_429')
            time.sleep(delay)

    raise last_error or RuntimeError('GEMINI_UNAVAILABLE')


def _one_shot_gemini_chat(prompt, token):
    return _gemini_chat(prompt, token)


def _github_models_chat(prompt, token):
    """OpenAI-compatible GitHub Models inference using workflow models permission."""
    body = json.dumps({
        'model': GITHUB_MODELS_MODEL,
        'messages': [
            {'role': 'system', 'content': 'Ты профессиональный редактор русского Telegram-канала об AI. Отвечай только валидным JSON.'},
            {'role': 'user', 'content': _compact_gemini_prompt(prompt)},
        ],
        'temperature': 0.25,
        'max_tokens': 900,
    }).encode()

    req = urllib.request.Request(
        GITHUB_MODELS_URL,
        data=body,
        headers={
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode())
        return data['choices'][0]['message']['content']
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode('utf-8', 'replace')
        raise RuntimeError(f'GITHUB_MODELS_HTTP_{exc.code}: {raw[:300]}') from exc


def install_runtime_hardening():
    global _active_provider_state
    publisher.IMPORTANCE_THRESHOLD = CANONICAL_PRE_AI_THRESHOLD
    publisher.gemini_chat = _gemini_chat

    original_ai = publisher.ai
    original_chat = publisher.chat

    def circuit_checked_gemini(prompt, token):
        if _active_provider_state is not None and publisher.provider_blocked(_active_provider_state, 'GEMINI'):
            raise RuntimeError('GEMINI_CIRCUIT_OPEN')
        return _gemini_chat(prompt, token)

    def circuit_checked_chat(url, model, token, prompt, provider, retries=2):
        if _active_provider_state is not None and publisher.provider_blocked(_active_provider_state, provider):
            raise RuntimeError(provider + '_CIRCUIT_OPEN')
        return original_chat(url, model, token, prompt, provider, retries)

    publisher.gemini_chat = circuit_checked_gemini
    publisher.chat = circuit_checked_chat

    def ai_with_quota_circuit(prompt, state):
        global _active_provider_state
        _active_provider_state = state
        try:
            return original_ai(prompt, state)
        except RuntimeError as exc:
            message = str(exc)
            if 'GEMINI_HTTP_429' in message:
                lowered = message.lower()
                cooldown = (
                    GEMINI_QUOTA_COOLDOWN_SECONDS
                    if ('exceeded your current quota' in lowered or 'quota_exceeded' in lowered or 'daily quota' in lowered)
                    else publisher.PROVIDER_COOLDOWN.get('GEMINI', 120)
                )
                publisher.PROVIDER_COOLDOWN['GEMINI'] = cooldown
                publisher.block_provider(state, 'GEMINI', 'HTTP_429_QUOTA_OR_RATE_LIMIT')

            github_token = os.environ.get('GITHUB_TOKEN')
            if github_token and not publisher.provider_blocked(state, 'GITHUB_MODELS'):
                telemetry = state.setdefault('_cycle_provider', {
                    'attempts': [], 'used': None, 'failovers': 0, 'failures': 0,
                    'blocked': 0, 'skipped_no_key': 0, 'retries': 0
                })
                try:
                    telemetry['attempts'].append('GITHUB_MODELS')
                    print('AI_PROVIDER_ATTEMPT GITHUB_MODELS')
                    result = _github_models_chat(prompt, github_token)
                    if result and len(result.strip()) > 20:
                        telemetry['used'] = 'GITHUB_MODELS'
                        telemetry['failovers'] = max(0, len(telemetry['attempts']) - 1)
                        print('AI_PROVIDER_OK GITHUB_MODELS')
                        print('AI_PROVIDER_USAGE', json.dumps(telemetry, ensure_ascii=False, separators=(',', ':')))
                        return result
                    raise RuntimeError('EMPTY_RESPONSE')
                except Exception as fallback_error:
                    print('AI_PROVIDER_FAILED GITHUB_MODELS', str(fallback_error)[:180])
                    publisher.block_provider(state, 'GITHUB_MODELS', 'GITHUB_MODELS_UNAVAILABLE')

            raise
        finally:
            _active_provider_state = None

    publisher.ai = ai_with_quota_circuit

    legacy_collect = publisher.collect

    def canonical_collect(telemetry=None):
        candidates = legacy_collect(telemetry)
        canonical = []
        for item in candidates:
            item.pop('russia_weight_bonus', None)
            item['audience_score'] = None
            base = float(publisher.score(item))
            item['score'] = round(base, 1)
            item['importance'] = round(base, 1)
            item['base_score'] = round(base, 1)
            item['audience_bonus'] = 0.0
            item['score_stage'] = 'pre_ai'
            if base >= CANONICAL_PRE_AI_THRESHOLD:
                canonical.append(item)
        canonical.sort(key=lambda item: (float(item.get('score', 0)), float(item.get('time', 0))), reverse=True)
        print('CANONICAL_PRE_AI_FILTER', len(candidates), '->', len(canonical), 'threshold', CANONICAL_PRE_AI_THRESHOLD)
        return canonical

    publisher.collect = canonical_collect


def main():
    install_runtime_hardening()
    guard.AI_EVALUATION_DEADLINE = time.monotonic() + AI_EVALUATION_BUDGET_SECONDS
    print('AI_EVALUATION_BUDGET', int(AI_EVALUATION_BUDGET_SECONDS))
    guard.run_production()


if __name__ == '__main__':
    main()
