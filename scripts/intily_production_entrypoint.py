"""Canonical production entrypoint hardening the legacy publisher at runtime."""

import hashlib
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
AI_EVALUATION_BUDGET_SECONDS = 180.0
GEMINI_REQUEST_TIMEOUT_SECONDS = 20

_gemini_last_request_at = 0.0
_active_provider_state = None


def _wait_for_gemini_slot():
    global _gemini_last_request_at
    now = time.monotonic()
    wait = GEMINI_MIN_REQUEST_INTERVAL_SECONDS - (now - _gemini_last_request_at)
    if wait > 0:
        time.sleep(wait)
    _gemini_last_request_at = time.monotonic()


def _compact_gemini_prompt(prompt):
    if not isinstance(prompt, str) or len(prompt) <= GEMINI_MAX_PROMPT_CHARS:
        return prompt
    truncation_marker = "\n[CONTEXT_TRUNCATED]\n"
    available_chars = GEMINI_MAX_PROMPT_CHARS - len(truncation_marker)
    head = available_chars * 2 // 3
    tail = available_chars - head
    return prompt[:head] + truncation_marker + prompt[-tail:]


def _gemini_chat(prompt, token):
    prompt = _compact_gemini_prompt(prompt)
    last_error = None
    for retry_index in range(len(GEMINI_RETRY_DELAYS_SECONDS) + 1):
        _wait_for_gemini_slot()
        body = json.dumps({
            'systemInstruction': {'parts': [{'text': 'Ты профессиональный редактор русского Telegram-канала об AI. Отвечай только валидным JSON.'}]},
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': 0.25, 'maxOutputTokens': 900, 'responseMimeType': 'application/json'}
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
            quota_exhausted = 'quota_exceeded' in lowered or 'exceeded your current quota' in lowered or 'daily quota' in lowered
            if quota_exhausted or retry_index >= len(GEMINI_RETRY_DELAYS_SECONDS):
                raise last_error
            delay = GEMINI_RETRY_DELAYS_SECONDS[retry_index]
            print('GEMINI_RETRY', int(delay), 'transient_429')
            time.sleep(delay)
    raise last_error or RuntimeError('GEMINI_UNAVAILABLE')


def _provider_key_fingerprint(token):
    """Store only a one-way credential fingerprint so rotated keys can reopen circuits."""
    if not token:
        return None
    return hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]


def _sync_provider_credentials(state):
    """Automatically reopen a provider when its configured secret has changed."""
    fingerprints = state.setdefault('_provider_key_fingerprints', {})
    changed = []
    for name, env_name in (
        ('GEMINI', 'GEMINI_API_KEY'),
        ('GROQ', 'GROQ_API_KEY'),
        ('OPENAI', 'OPENAI_API_KEY'),
    ):
        token = os.environ.get(env_name)
        if not token:
            continue
        current = _provider_key_fingerprint(token)
        previous = fingerprints.get(name)
        if previous and previous != current:
            publisher.clear_provider(state, name)
            print('AI_PROVIDER_CREDENTIAL_ROTATED', name)
            changed.append(name)
        fingerprints[name] = current
    return changed


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
            _sync_provider_credentials(state)
            return original_ai(prompt, state)
        except RuntimeError as exc:
            message = str(exc)
            if 'GEMINI_HTTP_429' in message:
                lowered = message.lower()
                cooldown = GEMINI_QUOTA_COOLDOWN_SECONDS if ('exceeded your current quota' in lowered or 'quota_exceeded' in lowered or 'daily quota' in lowered) else publisher.PROVIDER_COOLDOWN.get('GEMINI', 120)
                publisher.PROVIDER_COOLDOWN['GEMINI'] = cooldown
                publisher.block_provider(state, 'GEMINI', 'HTTP_429_QUOTA_OR_RATE_LIMIT')
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
