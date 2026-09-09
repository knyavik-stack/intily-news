"""Canonical production entrypoint hardening the legacy publisher at runtime.

This adapter is intentionally small and sits before the scoring runtime guard.
It fixes two legacy behaviors that cannot be allowed into production:
- collection must use the canonical 40-point pre-AI gate, not the legacy 60;
- a Gemini 429 quota response must fail fast and open a circuit, rather than
  sleeping 5+10+20 seconds for every queued item until the workflow times out.
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


def _one_shot_gemini_chat(prompt, token):
    """One request only; quota errors must not consume the whole CI budget."""
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
    req = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': 'application/json'},
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode())
        return data['candidates'][0]['content']['parts'][0]['text']
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode('utf-8', 'replace')
        raise RuntimeError(f'GEMINI_HTTP_{exc.code}: {raw[:300]}') from exc


def install_runtime_hardening():
    publisher.IMPORTANCE_THRESHOLD = CANONICAL_PRE_AI_THRESHOLD
    publisher.gemini_chat = _one_shot_gemini_chat

    original_ai = publisher.ai

    def ai_with_quota_circuit(prompt, state):
        try:
            return original_ai(prompt, state)
        except RuntimeError as exc:
            message = str(exc)
            if 'GEMINI_HTTP_429' in message:
                lowered = message.lower()
                cooldown = (
                    GEMINI_QUOTA_COOLDOWN_SECONDS
                    if 'exceeded your current quota' in lowered
                    else publisher.PROVIDER_COOLDOWN.get('GEMINI', 120)
                )
                publisher.PROVIDER_COOLDOWN['GEMINI'] = cooldown
                publisher.block_provider(state, 'GEMINI', 'HTTP_429_QUOTA_OR_RATE_LIMIT')
            raise

    publisher.ai = ai_with_quota_circuit

    # The legacy collector still applies a regional random bonus before its
    # filtering stage. Recalculate with the canonical scoring function and keep
    # only genuine pre-AI >=40 candidates before the guard runs AI evaluation.
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
    guard.run_production()


if __name__ == '__main__':
    main()
