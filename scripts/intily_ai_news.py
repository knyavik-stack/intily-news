import os
import re
import json
import time
import hashlib
from difflib import SequenceMatcher
import html
import urllib.parse
import urllib.request
import urllib.error
import random
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET


# ============================================================
# INTILY AI NEWS PUBLISHER
# Production queue / failover / watchdog / editorial QA
# ============================================================

# Discovery freshness is intentionally short. Old items should not occupy
# queue capacity when the channel publishes one story every three minutes.
# ============================================================
# НАСТРОЙКИ ПУБЛИКАЦИИ — единая точка управления Intily
# ============================================================

LOOKBACK = timedelta(hours=12)  # Максимальный возраст новости для discovery/queue.
SEARCH_INTERVAL_SECONDS = 30 * 60  # Плановый интервал поиска новостей: 30 минут.
PUBLISH_INTERVAL_SECONDS = 2 * 60  # Минимальный интервал между публикациями в Telegram.
IMPORTANCE_THRESHOLD = 60.0  # Минимальный математический score (0–100).
MAX_QUEUE = 20  # Максимальное количество подходящих историй в памяти.
RUSSIA_MIN_SHARE = 0.60  # Минимальная доля российских новостей в очереди при наличии качественных RU-кандидатов.
RUSSIA_MIN_QUEUE_SLOTS = 12  # Зарезервированное количество RU-слотов в полной очереди.
JOKE_RATE = 0.90  # Целевая вероятность шутки для подходящих несерьёзных публикаций.
URGENT_SEARCH_QUEUE_THRESHOLD = 1  # Искать немедленно, когда в durable queue не больше 1 материала.

# Переключатель редакционного стиля.
# 1 — авторский промпт Boss: жёсткий, матерный, саркастичный стиль.
# 2 — приличный промпт: естественный русский без мата и грубых формулировок.
# Меняйте только это число. Остальная логика публикации от него не зависит.
style_prompt = 1

MAX_PUBLISH = 1
TARGET_QUEUE_SIZE = MAX_QUEUE
WORLD_TARGET_SHARE = 1 - RUSSIA_MIN_SHARE
RUSSIA_TARGET_SHARE = RUSSIA_MIN_SHARE
RUSSIA_WEIGHT_BONUS_MIN = 5.0
RUSSIA_WEIGHT_BONUS_MAX = 10.0
RECENCY_RUSSIA_UNDER_3H = 23.5
RECENCY_WORLD_UNDER_3H = 21.5
RECENCY_OVER_3H = -2.0
REGION_HISTORY_SIZE = 20
QUEUE_RETENTION = timedelta(days=7)
QUEUE_RETRY_BASE_SECONDS = 300
QUEUE_RETRY_MAX_SECONDS = 6 * 3600

# Временный диагностический footer публикации. Выключен по решению Boss.
SHOW_QUEUE_DIAGNOSTICS = False
POLICY_VERSION = '2026-09-04'  # Версия policy, используемая в runtime diagnostics и state migrations.

HEARTBEAT_MAX_SECONDS = 900
FAILURE_ALERT_THRESHOLD = 3
MAX_ATTEMPTS_PER_RUN = 10
MAX_EDIT_ATTEMPTS = 2


STATE_FILE = os.environ.get(
    'STATE_FILE',
    'data/intily-ai-news-state.json'
)

# Exact RSS-item memory — только защита ingestion. Она не является архивом
# публикаций и не должна превращаться в долгосрочный blacklist.
KNOWN_LOOKBACK_SECONDS = 90 * 60


# ------------------------------------------------------------
# Provider models
# ------------------------------------------------------------

GROQ_MODEL = 'llama-3.1-8b-instant'
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'

OPENAI_MODEL = 'gpt-4o-mini'
OPENAI_URL = 'https://api.openai.com/v1/chat/completions'

GEMINI_MODEL = 'gemini-3.1-flash-lite'
GEMINI_URL = (
    'https://generativelanguage.googleapis.com/v1beta/models/'
    + GEMINI_MODEL
    + ':generateContent'
)

TG_URL = 'https://api.telegram.org/bot{}/sendMessage'


# ------------------------------------------------------------
# Sources
# ------------------------------------------------------------

# First-party / publisher RSS sources. Google News остаётся широким discovery index,
# а прямые RSS повышают устойчивость к проблемам одного агрегатора.
DIRECT_RSS_FEEDS = [
    ('WORLD', 'TechCrunch AI', 'https://techcrunch.com/category/artificial-intelligence/feed/'),
    ('WORLD', 'VentureBeat AI', 'https://venturebeat.com/category/ai/feed/'),
    ('WORLD', 'The Verge AI', 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml'),
    ('WORLD', 'OpenAI News', 'https://openai.com/news/rss.xml'),
    ('WORLD', 'Google DeepMind', 'https://deepmind.google/blog/rss.xml'),
    ('WORLD', 'Hugging Face', 'https://huggingface.co/blog/feed.xml'),
    ('WORLD', 'Ars Technica', 'https://feeds.arstechnica.com/arstechnica/index'),
    ('RUSSIA', 'Habr AI/News', 'https://habr.com/ru/rss/news'),
]

QUERIES = [
    ('WORLD', 'AI artificial intelligence major technology news'),
    ('WORLD', 'OpenAI model launch agent product'),
    ('WORLD', 'Anthropic Claude model enterprise'),
    ('WORLD', 'Google DeepMind Gemini AI technology'),
    ('WORLD', 'Microsoft Meta Apple AI product technology'),
    ('WORLD', 'Nvidia AI chips GPU semiconductor'),
    ('WORLD', 'AI agents robotics autonomous systems'),
    ('WORLD', 'artificial intelligence research breakthrough science'),
    ('WORLD', 'AI implementation business enterprise adoption automation'),
    ('WORLD', 'AI practical application workflow productivity operations'),
    ('WORLD', 'AI customer service sales marketing finance implementation'),
    ('WORLD', 'AI healthcare education manufacturing logistics application'),
    ('WORLD', 'AI software tool platform feature review developer coding'),
    ('WORLD', 'AI deployment architecture inference cost reliability'),
    ('WORLD', 'AI security vulnerability breach agent safety failure problem'),
    ('WORLD', 'AI startup funding acquisition investment enterprise technology'),
    ('WORLD', 'How to build an AI agent'),
    ('WORLD', 'AI safety standards and international regulations'),
    ('WORLD', 'OpenAI Google Anthropic latest LLM models release'),
    ('WORLD', 'Generative AI tools for software development productivity'),
    ('WORLD', 'AGI breakthrough timeline predictions computer science'),
    ('WORLD', 'Breakthroughs in robotics powered by multimodal AI'),
    ('RUSSIA', 'Развитие ИИ в России национальная стратегия'),
    ('RUSSIA', 'Яндекс Сбер новые нейросети GigaChat YandexGPT'),
    ('RUSSIA', 'Искусственный интеллект в российском бизнесе кейсы'),
    ('RUSSIA', 'ИИ технологии в российском образовании и медицине'),
    ('RUSSIA', 'Регулирование и законы об ИИ в РФ'),
    ('RUSSIA', 'ИИ искусственный интеллект нейросети Россия технологии'),
    ('RUSSIA', 'Яндекс Сбер VK ИИ продукт технология'),
    ('RUSSIA', 'российские компании внедрение ИИ бизнес автоматизация'),
    ('RUSSIA', 'ИИ применение практика бизнес кейс Россия'),
    ('RUSSIA', 'ИИ финансы промышленность медицина образование логистика Россия'),
    ('RUSSIA', 'ИИ разработка инфраструктура модели агенты Россия'),
    ('RUSSIA', 'ИИ безопасность уязвимость утечка проблемы Россия'),
    ('RUSSIA', 'ИИ робототехника чипы исследования Россия'),
    ('RUSSIA', 'ИИ регулирование закон инвестиции технологии Россия'),
    ('RUSSIA', 'российский ИИ стартап продукт платформа обзор'),
    ('RUSSIA', 'ИИ в образовании'),
    ('RUSSIA', 'ИИ в медицине'),
    ('RUSSIA', 'Как создать ИИ агента'),
    ('RUSSIA', 'site:yandex.ru/company/news ИИ искусственный интеллект'),
    ('RUSSIA', 'site:sber.ru ИИ искусственный интеллект технологии'),
    ('RUSSIA', 'site:rbc.ru ИИ внедрение бизнес технологии'),
    ('RUSSIA', 'site:kommersant.ru ИИ технологии бизнес Россия'),
    ('RUSSIA', 'site:vc.ru ИИ бизнес внедрение автоматизация')
]


QUALITY_TRUSTED = {
    'reuters', 'bloomberg', 'financial times', 'the verge',
    'techcrunch', 'wired', 'mit technology review', 'arstechnica',
    'venturebeat', 'tass', 'interfax', 'рбк', 'коммерсантъ',
    'ведомости', 'forbes'
}

TRUSTED = QUALITY_TRUSTED | {'science.mail.ru', 'securitylab.ru', 'vc.ru', 'ria.ru'}

HIGH_IMPACT_TERMS = {
    'launch', 'released', 'release', 'introduces', 'introduced', 'model',
    'agent', 'robot', 'robotics', 'breakthrough', 'acquisition', 'funding',
    'investment', 'billion', 'chip', 'gpu', 'security', 'breach', 'regulation',
    'law', 'запуст', 'выпуст', 'представ', 'модел', 'агент', 'робот', 'прорыв',
    'инвести', 'миллиард', 'поглощ', 'чип', 'утеч', 'регулир', 'закон',
    'сделк', 'финансир', 'разработ', 'внедрен'
}

APPLICATION_TERMS = {
    'application', 'applied', 'implementation', 'implement', 'deployment',
    'deploy', 'workflow', 'productivity', 'automation', 'business', 'enterprise',
    'customer', 'sales', 'marketing', 'finance', 'healthcare', 'education',
    'manufacturing', 'logistics', 'application', 'интеграц', 'внедр', 'автоматиза',
    'бизнес', 'производств', 'медицин', 'образован', 'логист', 'финанс', 'продаж'
}


# ...


def build_edit_prompt(x, retry=False, previous_error=''):
    # Выбор стиля происходит только здесь. Сам пользовательский prompt можно менять
    # в соответствующем блоке ниже, а переключатель style_prompt находится в начале файла.
    if style_prompt == 1:
        # Авторский prompt Boss. Не менять без его прямого указания.
        prompt_template = (
            'Подготовь готовый Telegram-пост, описание ЦЕЛИКОМ на естественном русском языке как журналиста-тюремного алкаша в жестком конкретно правдивом тоне, чётко по факту, объективно, честно с максимальным сарказмом и жёстким цитированием мата через каждое слово. '
            'Не делай дословный перевод: перескажи человеческим быдло языком с матом в стиле: ёбаный пупок, прикинь, охуеть, нейрохуйня, пиздец, блядь, ебануться, ёмана рот, сраньё, мудак, хуй, пизда, ебать, ракета, токен тебе в рот, пиздатокен, в APIёбан, обучен на хуях, галлюциноебля, нейронка-хуёнка и производные от них '
            'Обязательно раскрой: что произошло, кто участники, почему это важно и практический ценный контекстный профессиональный вывод. Можно разбивать на абзацы. Постарайся уместиться в 700 символов. '
            'Не выдумывай факты. Названия компаний, продуктов и моделей можно оставлять в оригинальном написании.\n'
            'Юмор: целевая доля жёсткой человеческой шутки — 100%%. В этой публикации шутка %s. '
            # 'Если тема про безопасность, закон, аварию, вред или серьёзный инцидент — шутка запрещена. '
            'Не используй речевые штампы ИИ и канцелярит.  Супер этичный и приличный заголовок. Верни строгий JSON с полями title, body, meaning, joke. joke может быть пустой строкой.\n%s\n\n'
            'Источник: %s\nЗаголовок: %s\nОписание: %s'
        )
    elif style_prompt == 2:
        # Альтернативный приличный стиль. Он сохраняет фактические требования,
        # но убирает мат, грубые формулировки и образ «тюремного журналиста».
        prompt_template = (
            'Подготовь готовый Telegram-пост, описание ЦЕЛИКОМ на естественном русском языке в живом, уверенном и профессиональном стиле. '
            'Пиши конкретно, честно и по фактам, без канцелярита, шаблонов и искусственной «нейросетевой» манеры. '
            'Не делай дословный перевод: перескажи событие понятно для русскоязычного читателя. '
            'Обязательно раскрой: что произошло, кто участники, почему это важно и какой практический ценный контекстный вывод стоит из этого сделать. '
            'Можно разбивать на абзацы. Постарайся уместиться в 700 символов. '
            'Не выдумывай факты. Названия компаний, продуктов и моделей можно оставлять в оригинальном написании.\n'
            'Юмор: целевая доля живой человеческой шутки — 100%%. В этой публикации шутка %s. '
            'Не используй речевые штампы ИИ и канцелярит. Заголовок должен быть этичным, понятным и информативным. '
            'Верни строгий JSON с полями title, body, meaning, joke. joke может быть пустой строкой.\n%s\n\n'
            'Источник: %s\nЗаголовок: %s\nОписание: %s'
        )
    else:
        # Защита от случайного неверного значения: не запускаем непредусмотренный стиль.
        raise ValueError('Недопустимое значение style_prompt: используйте 1 или 2')

    want_joke = random.random() < JOKE_RATE
    joke_instruction = 'нужна' if want_joke else 'не нужна'
    retry_instruction = ''
    if retry:
        retry_instruction = (
            '\nПредыдущая версия не прошла редакторскую проверку. Сделай текст проще, естественнее и полностью на русском языке. Не повторяй проблемную конструкцию.'
        )
        if previous_error:
            retry_instruction += '\nПричина предыдущего отказа: ' + previous_error[:180]

    return prompt_template % (
        joke_instruction,
        retry_instruction,
        x['source'],
        x['title'],
        x['desc']
    )


def hashtags_for(x):
    # Telegram topic tags: always include core AI tags, then add only relevant topics.
    blob = (x.get('title', '') + ' ' + x.get('desc', '')).lower()
    tags = ['#ИИ', '#AI']
    mapping = [
        ('agent', '#AIагенты'), ('агент', '#AIагенты'),
        ('model', '#AIмодели'), ('модель', '#AIмодели'),
        ('robot', '#Робототехника'), ('робот', '#Робототехника'),
        ('security', '#БезопасностьИИ'), ('безопас', '#БезопасностьИИ'),
        ('regulation', '#РегулированиеИИ'), ('регулир', '#РегулированиеИИ'),
        ('investment', '#AIинвестиции'), ('инвести', '#AIинвестиции'),
        ('business', '#AIбизнес'), ('бизнес', '#AIбизнес'),
        ('automation', '#Автоматизация'), ('автоматиза', '#Автоматизация'),
        ('inference', '#Inference'), ('инфраструктур', '#AIинфраструктура')
    ]
    for term, tag in mapping:
        if term in blob and tag not in tags:
            tags.append(tag)
        if len(tags) >= 5:
            break
    return ' '.join(tags[:5])



def edit(x, s):
    last_error = ''

    for attempt in range(
        MAX_EDIT_ATTEMPTS
    ):