"""INTILY production runtime compatibility overrides.

Python auto-loads this module when `scripts/` is on PYTHONPATH. Keep vendor
model selection here temporarily while the legacy publisher is being migrated.
"""

import intily_ai_news as _publisher

# Groq retired llama-3.1-8b-instant on 2026-08-16. GPT-OSS 20B is the
# documented replacement and is available under Groq's Free Plan limits.
_publisher.GROQ_MODEL = 'openai/gpt-oss-20b'
print('GROQ_MODEL_RUNTIME_OVERRIDE', _publisher.GROQ_MODEL)
