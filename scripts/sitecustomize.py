"""INTILY production runtime compatibility overrides.

Keep this module limited to technical compatibility migrations. User-authored
editorial behavior in ``intily_ai_news.py`` is canonical and must not be
replaced here.
"""

import intily_ai_news as _publisher

# Technical compatibility only: Groq retired llama-3.1-8b-instant on 2026-08-16.
_publisher.GROQ_MODEL = 'openai/gpt-oss-20b'
print('GROQ_MODEL_RUNTIME_OVERRIDE', _publisher.GROQ_MODEL)
