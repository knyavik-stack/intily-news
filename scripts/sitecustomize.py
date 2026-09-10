"""INTILY production runtime compatibility overrides.

Python auto-loads this module when `scripts/` is on PYTHONPATH. Keep small
runtime migrations here only when the legacy publisher cannot be changed safely
in-place in the same release.
"""

import random
import intily_ai_news as _publisher

# Groq retired llama-3.1-8b-instant on 2026-08-16. GPT-OSS 20B is the
# documented replacement and is available under Groq's Free Plan limits.
_publisher.GROQ_MODEL = 'openai/gpt-oss-20b'
print('GROQ_MODEL_RUNTIME_OVERRIDE', _publisher.GROQ_MODEL)


def _clean_build_edit_prompt(x, retry=False, previous_error=''):
    """Replace the legacy contaminated editor prompt with the current product voice.

    The legacy prompt contained excessive profanity and an unsuitable character
    instruction. Runtime override keeps this correction isolated and reversible
    until the publisher is fully refactored.
    """
    want_joke = random.random() < _publisher.JOKE_RATE
    joke_instruction = 'Добавь одну короткую живую шутку, если тема это позволяет.' if want_joke else 'Шутка не обязательна для этой публикации.'
    retry_instruction = ''
    if retry:
        retry_instruction = '\nПредыдущая версия не прошла редакторскую проверку. Сделай текст естественнее, конкретнее и полностью на русском языке.'
        if previous_error:
            retry_instruction += '\nПричина предыдущего отказа: ' + str(previous_error)[:180]

    return (
        'Подготовь готовый пост для русскоязычного Telegram-канала об AI. '
        'Пиши естественным человеческим русским языком: живо, конкретно, без канцелярита, шаблонов и искусственной «нейросетевой» манеры. '
        'Не выдумывай факты и не усиливай формулировки без подтверждения источником. '
        'Обязательно раскрой: что произошло, кто участники, почему это важно и какой практический вывод полезен читателю. '
        'Названия компаний, продуктов и моделей можно оставлять в оригинальном написании. '
        'Лёгкий юмор допустим только там, где он уместен; для безопасности, закона, аварий, вреда и серьёзных инцидентов юмор не использовать. '
        + joke_instruction + ' '
        + retry_instruction + '\n'
        'Верни строгий JSON с полями title, body, meaning, joke. Поле joke может быть пустой строкой. '
        'Заголовок должен быть информативным и аккуратным. Постарайся уместиться в 700 символов.\n\n'
        f'Источник: {x.get("source", "")}\n'
        f'Заголовок: {x.get("title", "")}\n'
        f'Описание: {x.get("desc", "")} '
    )


_publisher.build_edit_prompt = _clean_build_edit_prompt
print('EDITOR_PROMPT_RUNTIME_OVERRIDE clean_ru_voice')
