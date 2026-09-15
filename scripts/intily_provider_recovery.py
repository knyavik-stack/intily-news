"""Recovery helper for persisted AI-provider circuit breakers.

Normal production cycles use the bounded automatic recovery mode below. It only
clears provider cooldowns when every configured AI provider is blocked; this
prevents a persisted all-provider outage from becoming a permanent deadlock
while preserving circuit-breaker protection when at least one provider works.
"""

import json
import os
import sys
import time


PROVIDERS = ('GEMINI', 'GROQ', 'OPENAI', 'GITHUB_MODELS')
PROVIDER_ENV = {
    'GEMINI': 'GEMINI_API_KEY',
    'GROQ': 'GROQ_API_KEY',
    'OPENAI': 'OPENAI_API_KEY',
    'GITHUB_MODELS': 'GITHUB_TOKEN',
}
STATE_FILE = os.environ.get('STATE_FILE', 'data/intily-ai-news-state.json')


def _configured_providers(state):
    configured = []
    for name in PROVIDERS:
        env_name = PROVIDER_ENV[name]
        if os.environ.get(env_name):
            configured.append(name)
    if configured:
        return configured
    # Keep the utility deterministic for tests/operator use when provider
    # secrets are intentionally not injected into the environment.
    return [name for name in PROVIDERS if name in state.get('providers', {})]


def _is_blocked(provider):
    disabled_until = float(provider.get('disabled_until', 0) or 0)
    return disabled_until > time.time() or bool(provider.get('reason'))


def recover_state(path=STATE_FILE, providers_to_reset=None):
    with open(path, encoding='utf-8') as handle:
        state = json.load(handle)

    providers = state.setdefault('providers', {})
    names = tuple(providers_to_reset or PROVIDERS)
    recovered = []
    now = time.time()

    for name in names:
        provider = providers.get(name) or {}
        disabled_until = float(provider.get('disabled_until', 0) or 0)
        if disabled_until > now or provider.get('reason'):
            recovered.append({
                'provider': name,
                'remaining_seconds': max(0, int(disabled_until - now)),
                'reason': str(provider.get('reason', ''))[:120],
            })
        providers[name] = {
            'disabled_until': 0,
            'reason': '',
            'updated_at': now,
        }

    tmp = path + '.recovery.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return recovered


def recover_if_all_blocked(path=STATE_FILE):
    with open(path, encoding='utf-8') as handle:
        state = json.load(handle)

    configured = _configured_providers(state)
    providers = state.setdefault('providers', {})
    if not configured:
        print('AI_PROVIDER_RECOVERY_SKIP no_configured_providers')
        return []

    blocked = [name for name in configured if _is_blocked(providers.get(name) or {})]
    if len(blocked) != len(configured):
        print('AI_PROVIDER_RECOVERY_SKIP provider_available')
        return []

    recovered = recover_state(path, configured)
    print('AI_PROVIDER_RECOVERY_ALL_BLOCKED', json.dumps(recovered, ensure_ascii=False, separators=(',', ':')))
    return recovered


if __name__ == '__main__':
    if '--all-blocked' in sys.argv:
        recovered = recover_if_all_blocked()
    else:
        # Operator-triggered emergency reset remains available explicitly.
        recovered = recover_state()
        print('AI_PROVIDER_RECOVERY_RESET', json.dumps(recovered, ensure_ascii=False, separators=(',', ':')))
