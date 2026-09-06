#!/usr/bin/env python3
"""Одноразовая миграция production-кода Intily.

Скрипт нужен только для безопасного применения уже проверенных замен к main
из production workflow. После успешного применения файл можно удалить.
"""
from pathlib import Path

TARGET = Path("scripts/intily_ai_news.py")

OLD = """    admission['candidate_count'] = len(candidates)\n    admission['admission_rate'] = round(admission['added'] / max(1, len(candidates)) * 100, 2)\n    admission['dominant_block'] = max(\n        (k for k in admission if k not in ('added', 'admission_rate')),\n        key=lambda k: admission[k],\n        default='none'\n    )\n"""

NEW = """    admission['candidate_count'] = len(candidates)\n    admission['admission_rate'] = round(admission['added'] / max(1, len(candidates)) * 100, 2)\n    # candidate_count — это размер входа, а не причина отказа.\n    # Иначе он почти всегда становится dominant_block и скрывает реальную\n    # причину: уже опубликовано, недавно известно, уже в очереди или story dedup.\n    block_keys = (\n        'published_key', 'known_recent', 'already_queued',\n        'story_queue', 'story_history'\n    )\n    admission['dominant_block'] = max(\n        block_keys,\n        key=lambda k: admission.get(k, 0),\n        default='none'\n    )\n"""

old_text = TARGET.read_text(encoding="utf-8")
if NEW in old_text:
    print("ADMISSION_HOTFIX already applied")
    raise SystemExit(0)
if OLD not in old_text:
    raise SystemExit("ADMISSION_HOTFIX source pattern not found; refusing unsafe edit")

text = old_text.replace(OLD, NEW, 1)
TARGET.write_text(text, encoding="utf-8")
print("ADMISSION_HOTFIX applied")
