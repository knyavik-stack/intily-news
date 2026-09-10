"""One-shot recovery for persisted AI-provider circuit breakers.

This utility is intentionally operator-triggered through the workflow. It does
not touch queue/publication/story memory; it only clears persisted provider
cooldowns so the next production cycle can make a real vendor request.
"""

import json
import os
import time


PROVIDERS = ('GEMINI', 'GROQ', 'OPENAI', 'GITHUB_MODELS')
STATE_FILE = os.environ.get('STATE_FILE', 'data/intily-ai-news-state.json')


def recover_state(path=STATE_FILE):
    with open(path, encoding='utf-8') as handle:
        state = json.load(handle)

    providers = state.setdefault('providers', {})
    recovered = []
    now = time.time()

    for name in PROVIDERS:
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


if __name__ == '__main__':
    # Recovery is intentionally observable and one-shot; normal runs do not call this utility.
    recovered = recover_state()
    print('AI_PROVIDER_RECOVERY_RESET', json.dumps(recovered, ensure_ascii=False, separators=(',', ':')))
