const MODEL = '@cf/meta/llama-3.3-70b-instruct-fp8-fast';
const CRON = '* * * * *';

const STATE_KEY = 'publisher:v3';
const LOCK_KEY = 'publisher:lock:v3';

const LOOKBACK_MS = 12 * 60 * 60 * 1000;
const LOCK_TTL = 240;
const PUBLISHED_TTL = 7 * 24 * 60 * 60;
const MAX_PUBLISH_PER_RUN = 30;
const MAX_QUEUE = 100;

const MIN_SCORE = 3;

// Collect at most once per hour; scheduled runs can still drain the queue.
const COLLECT_INTERVAL_MS = 20 * 60 * 1000;
const REQUEST_DELAY_MS = 2500;

export default {
  async fetch(request, env) {
    const u = new URL(request.url);

    if (u.pathname === '/health' && request.method === 'GET') {
      return Response.json({
        ok: true,
        service: 'intily-ai-news',
        version: '5.0',
        cron: CRON,
        time: new Date().toISOString()
      });
    }

    // /run deliberately disabled.
    // Production publishing must happen only through Cloudflare Cron.
    return new Response('Not found', { status: 404 });
  },

  async scheduled(event, env, ctx) {
    if (event.cron !== CRON) return;

    // Run every minute, but dispatch to GitHub only on ~1/3 of ticks.
    // The gate is intentionally first so non-selected ticks finish immediately.
    const gate = Math.floor(Math.random() * 3) + 1;
    if (gate !== 1) return;

    ctx.waitUntil(dispatchGitHub(env));
  }
};

async function dispatchGitHub(env) {
  const response = await fetch('https://api.github.com/repos/knyavik-stack/intily-news/actions/workflows/intily-ai-news.yml/dispatches', {
    method: 'POST',
    headers: {
      'authorization': `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
      'accept': 'application/vnd.github+json',
      'content-type': 'application/json',
      'user-agent': 'intily-cloudflare-scheduler'
    },
    body: JSON.stringify({ ref: 'main' })
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`GITHUB_DISPATCH_FAILED ${response.status}: ${detail.slice(0,300)}`);
  }
  console.log('GITHUB_DISPATCH', response.status);
}

async function publish(env) {
  const lock = await acquireLock(env);
  if (!lock) {
    console.log('SKIP_LOCKED');
    return;
  }

  try {
    let state = await loadState(env);

    let candidates = [];
    const shouldCollect = !state.lastCollect ||
      Date.now() - state.lastCollect >= COLLECT_INTERVAL_MS;

    if (shouldCollect) {
      candidates = await collect();
      state.lastCollect = Date.now();
    } else {
      console.log('COLLECT_SKIPPED_INTERVAL');
    }

    // Add only new candidates to the persistent queue.
    state = enqueueCandidates(state, candidates);

    // Highest priority first.
    state.queue.sort((a, b) =>
      b.score - a.score ||
      b.time - a.time
    );

    let published = 0;
    const remaining = [];

    for (const item of state.queue) {
      if (published >= MAX_PUBLISH_PER_RUN) {
        remaining.push(item);
        continue;
      }

      if (Date.now() - item.time > LOOKBACK_MS) {
        continue;
      }

      if (state.published[item.key]) {
        continue;
      }

      if (item.score < MIN_SCORE) {
        // Keep candidates temporarily. A later run may still process them
        // if they remain within the lookback window.
        remaining.push(item);
        continue;
      }

      try {
        const post = await edit(env, item);

        if (!post) {
          console.log('EDITOR_REJECTED', item.key);
          remaining.push(item);
          continue;
        }

        await sendTelegram(env, post);

        state.published[item.key] = Date.now();
        published++;

        console.log('PUBLISHED', {
          key: item.key,
          title: item.title,
          score: item.score
        });

      } catch (err) {
        console.error('ITEM_FAILED', {
          key: item.key,
          error: err?.message || String(err)
        });

        // Keep failed items in queue for a later retry.
        remaining.push(item);
      }
    }

    state.queue = remaining.slice(0, MAX_QUEUE);

    // Remove old published markers.
    const publishedCutoff = Date.now() - PUBLISHED_TTL;
    for (const [key, ts] of Object.entries(state.published)) {
      if (ts < publishedCutoff) {
        delete state.published[key];
      }
    }

    state.lastRun = Date.now();
    state.lastCandidates = candidates.length;
    state.lastPublished = published;

    await saveState(env, state);

    console.log('RUN_COMPLETE', {
      candidates: candidates.length,
      published,
      queue: state.queue.length
    });

  } finally {
    await releaseLock(env);
  }
}

/* =========================================================
   STATE
========================================================= */

async function loadState(env) {
  const raw = await env.STATE.get(STATE_KEY);

  if (!raw) {
    return {
      queue: [],
      published: {},
      known: {},
      lastRun: 0,
      lastCandidates: 0,
      lastPublished: 0
    };
  }

  try {
    const parsed = JSON.parse(raw);

    return {
      queue: Array.isArray(parsed.queue) ? parsed.queue : [],
      published: parsed.published || {},
      known: parsed.known || {},
      lastRun: parsed.lastRun || 0,
      lastCandidates: parsed.lastCandidates || 0,
      lastPublished: parsed.lastPublished || 0
    };
  } catch {
    return {
      queue: [],
      published: {},
      known: {},
      lastRun: 0,
      lastCandidates: 0,
      lastPublished: 0
    };
  }
}

async function saveState(env, state) {
  await env.STATE.put(
    STATE_KEY,
    JSON.stringify(state)
  );
}

function enqueueCandidates(state, candidates) {
  const existingQueue = new Set(
    state.queue.map(x => x.key)
  );

  for (const c of candidates) {
    if (state.published[c.key]) continue;
    if (state.known[c.key]) continue;
    if (existingQueue.has(c.key)) continue;

    state.known[c.key] = Date.now();
    state.queue.push(c);
    existingQueue.add(c.key);
  }

  // Keep state bounded.
  const cutoff = Date.now() - LOOKBACK_MS;

  state.queue = state.queue
    .filter(x => x.time >= cutoff)
    .sort((a, b) =>
      b.score - a.score ||
      b.time - a.time
    )
    .slice(0, MAX_QUEUE);

  // Keep only recent known IDs.
  const knownCutoff = Date.now() - PUBLISHED_TTL;

  for (const [key, ts] of Object.entries(state.known)) {
    if (ts < knownCutoff) {
      delete state.known[key];
    }
  }

  return state;
}

/* =========================================================
   LOCK
========================================================= */

async function acquireLock(env) {
  const existing = await env.STATE.get(LOCK_KEY);

  if (existing) {
    const ts = Number(existing);

    if (
      Number.isFinite(ts) &&
      Date.now() - ts < LOCK_TTL * 1000
    ) {
      return false;
    }
  }

  await env.STATE.put(
    LOCK_KEY,
    String(Date.now()),
    { expirationTtl: LOCK_TTL }
  );

  return true;
}

async function releaseLock(env) {
  await env.STATE.delete(LOCK_KEY);
}

/* =========================================================
   NEWS COLLECTION
========================================================= */

async function collect() {
  // Two aggregated Google queries instead of six burst requests.
  const queries = [
    { region: 'WORLD', q: '(AI OR "artificial intelligence" OR OpenAI OR Anthropic OR DeepMind OR Nvidia OR "AI agents") when:1d' },
    { region: 'RUSSIA', q: '(ИИ OR "искусственный интеллект" OR нейросети OR Яндекс OR Сбер OR VK) when:1d' }
  ];
  const all = [];
  const cutoff = Date.now() - LOOKBACK_MS;
  const headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    'accept': 'application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5',
    'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
  };

  for (let i = 0; i < queries.length; i++) {
    const item = queries[i];
    const url = 'https://news.google.com/rss/search?' +
      new URLSearchParams({
        q: item.q,
        hl: item.region === 'RUSSIA' ? 'ru-RU' : 'en-US',
        gl: item.region === 'RUSSIA' ? 'RU' : 'US',
        ceid: item.region === 'RUSSIA' ? 'RU:ru' : 'US:en'
      });

    try {
      const response = await fetch(url, { headers });
      if (!response.ok) {
        console.error('NEWS_FEED_ERROR', response.status, item.region);
      } else {
        const xml = await response.text();
        for (const x of parseRSS(xml)) {
          if (x.time < cutoff) continue;
          const score = scoreNews(x);
          if (score < 3) continue;
          all.push({ ...x, region: item.region, score, key: await storyKey(x) });
        }
      }
    } catch (err) {
      console.error('NEWS_FEED_EXCEPTION', item.region, err?.message || String(err));
    }

    if (i < queries.length - 1) {
      await new Promise(resolve => setTimeout(resolve, REQUEST_DELAY_MS));
    }
  }

  // If Google is unavailable, use publisher RSS feeds as a resilience fallback.
  if (!all.length) {
    const feeds = [
      { region: 'WORLD', url: 'https://techcrunch.com/feed/' },
      { region: 'WORLD', url: 'https://venturebeat.com/feed/' },
      { region: 'WORLD', url: 'https://www.theverge.com/rss/index.xml' },
      { region: 'RUSSIA', url: 'https://habr.com/ru/rss/hubs/artificial_intelligence/all/?fl=ru' }
    ];
    for (const feed of feeds) {
      try {
        const response = await fetch(feed.url, { headers });
        if (!response.ok) {
          console.error('FALLBACK_FEED_ERROR', response.status, feed.url);
          continue;
        }
        const xml = await response.text();
        for (const x of parseRSS(xml)) {
          if (x.time < cutoff) continue;
          const score = scoreNews(x);
          if (score < 3) continue;
          all.push({ ...x, region: feed.region, score, key: await storyKey(x) });
        }
      } catch (err) {
        console.error('FALLBACK_FEED_EXCEPTION', feed.url, err?.message || String(err));
      }
    }
  }

  return clusterStories(all);
}

/* =========================================================
   SCORING
========================================================= */

function scoreNews(x) {
  const blob = (
    x.title +
    ' ' +
    x.desc +
    ' ' +
    x.source
  ).toLowerCase();

  let score = 0;

  const weights = [
    ['launch', 5],
    ['release', 5],
    ['model', 4],
    ['agent', 5],
    ['breakthrough', 7],
    ['research', 3],
    ['security', 5],
    ['safety', 5],
    ['regulation', 5],
    ['law', 5],
    ['investment', 4],
    ['billion', 5],
    ['acquisition', 5],
    ['chip', 4],
    ['gpu', 4],

    ['openai', 4],
    ['anthropic', 4],
    ['google', 3],
    ['deepmind', 4],
    ['nvidia', 4],
    ['microsoft', 3],

    ['yandex', 4],
    ['sber', 4],

    ['закон', 6],
    ['регулир', 5],
    ['миллиард', 5],
    ['запуст', 5],
    ['выпуст', 5],
    ['агент', 5],
    ['модель', 4],
    ['нейросет', 4],
    ['исследован', 3],
    ['инвести', 4],
    ['покуп', 5],
    ['сделк', 4],
    ['безопасност', 5]
  ];

  for (const [word, weight] of weights) {
    if (blob.includes(word)) {
      score += weight;
    }
  }

  const trusted = [
    'reuters',
    'bloomberg',
    'financial times',
    'the verge',
    'techcrunch',
    'tass',
    'interfax',
    'рбк',
    'коммерсантъ',
    'ведомости'
  ];

  if (
    trusted.includes(
      x.source.toLowerCase().trim()
    )
  ) {
    score += 3;
  }

  const age = Date.now() - x.time;

  if (age < 3 * 60 * 60 * 1000) {
    score += 5;
  } else if (age > 12 * 60 * 60 * 1000) {
    score -= 1;
  }

  return Math.max(0, Math.min(score, 30));
}

/* =========================================================
   RSS
========================================================= */

function parseRSS(xml) {
  const out = [];

  for (
    const m of xml.matchAll(
      /<item>([\s\S]*?)<\/item>/gi
    )
  ) {
    const s = m[1];

    const title = dec(tag(s, 'title'));
    const link = dec(tag(s, 'link'));
    const desc = dec(
      tag(s, 'description')
    )
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    const source = dec(tag(s, 'source'));
    const date = Date.parse(
      tag(s, 'pubDate')
    );

    if (
      title &&
      link &&
      Number.isFinite(date)
    ) {
      out.push({
        title,
        link: cleanUrl(link),
        desc,
        source,
        time: date
      });
    }
  }

  return out;
}

function tag(s, name) {
  const m = s.match(
    new RegExp(
      '<' +
      name +
      '[^>]*>([\\s\\S]*?)</' +
      name +
      '>',
      'i'
    )
  );

  return m ? m[1] : '';
}

function dec(s) {
  return String(s)
    .replace(/<!\[CDATA\[|\]\]>/g, '')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .trim();
}

function cleanUrl(url) {
  try {
    const u = new URL(url);

    [
      'utm_source',
      'utm_medium',
      'utm_campaign',
      'utm_term',
      'utm_content',
      'gclid',
      'fbclid'
    ].forEach(x => u.searchParams.delete(x));

    return u.toString();
  } catch {
    return url;
  }
}

/* =========================================================
   STORY DEDUPLICATION
========================================================= */

async function storyKey(x) {
  const normalized =
    normalizeTitle(x.title) +
    '|' +
    normalizeSource(x.source);

  return sha(normalized);
}

function normalizeTitle(title) {
  return String(title)
    .toLowerCase()
    .replace(/ё/g, 'е')
    .replace(/[^a-zа-я0-9\s]/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .filter(Boolean)
    .sort()
    .join(' ');
}

function normalizeSource(source) {
  return String(source)
    .toLowerCase()
    .replace(/[^a-zа-я0-9]/gi, '');
}

function clusterStories(items) {
  const result = [];

  for (const item of items) {
    const duplicate = result.find(
      existing =>
        similarity(
          item.title,
          existing.title
        ) >= 0.72
    );

    if (!duplicate) {
      result.push(item);
      continue;
    }

    // Keep the better source / fresher / higher scored version.
    if (
      item.score > duplicate.score ||
      (
        item.score === duplicate.score &&
        item.time > duplicate.time
      )
    ) {
      Object.assign(duplicate, item);
    }
  }

  return result.sort(
    (a, b) =>
      b.score - a.score ||
      b.time - a.time
  );
}

function similarity(a, b) {
  const A = new Set(
    normalizeTitle(a)
      .split(' ')
      .filter(x => x.length > 2)
  );

  const B = new Set(
    normalizeTitle(b)
      .split(' ')
      .filter(x => x.length > 2)
  );

  if (!A.size || !B.size) return 0;

  let intersection = 0;

  for (const word of A) {
    if (B.has(word)) intersection++;
  }

  const union = new Set([...A, ...B]).size;

  return intersection / union;
}

/* =========================================================
   AI EDITOR
========================================================= */

async function edit(env, c) {
  const prompt = `
Ты — главный редактор Telegram-канала intilyshop о современных технологиях и искусственном интеллекте.

Твоя задача — на основе исходного материала подготовить ГОТОВЫЙ пост для публикации.

КРИТИЧЕСКИЕ ПРАВИЛА:

1. Весь результат должен быть написан НА ЕСТЕСТВЕННОМ РУССКОМ ЯЗЫКЕ.
2. Не делай дословный перевод.
3. Перескажи новость так, как написал бы грамотный русский журналист.
4. Не используй типичные ИИ-штампы:
   - "таким образом"
   - "в свою очередь"
   - "данное событие"
   - "важный шаг"
   - "на сегодняшний день"
   - "это подчеркивает"
   - "следует отметить"
5. Не выдумывай факты.
6. Не добавляй сведения, которых нет в исходном материале или которые нельзя логически вывести из него.
7. Тема должна быть раскрыта в пределах не более 60 слов.
8. Обязательно объясни:
   - что произошло;
   - кто участвует;
   - почему это важно;
   - что это может изменить.
9. Обязательно сделай понятный вывод не более 20 слов.
10. Используй 1–3 уместных эмодзи.
11. Юмор разрешён ТОЛЬКО если он действительно естественен для конкретной новости.
12. Для происшествий, законов, войн и серьёзных конфликтов юмор ЗАПРЕЩЁН.
13. Не используй голые URL.
14. Не пиши название источника латиницей внутри основного текста.
15. Не оставляй английский текст в заголовке или содержании.
16. Не оставляй "..." как незаполненный текст.
17. Не пиши комментарии о том, что ты ИИ.
18. Не пиши "перевод", "оригинал", "источник сообщил" без необходимости.

Верни ТОЛЬКО JSON:

{
  "title": "русский заголовок",
  "body": "полностью русский основной текст",
  "meaning": "полностью русский блок о том, что это значит",
  "joke": "пустая строка, если юмор неуместен"
}

Исходный источник: ${c.source}
Дата публикации: ${new Date(c.time).toISOString()}

Заголовок:
${c.title}

Описание:
${c.desc}
`;

  try {
    const r = await env.AI.run(
      MODEL,
      {
        prompt,
        max_tokens: 900,
        temperature: 0.35,
        response_format: {
          type: 'json_object'
        }
      }
    );

    const raw = r?.response;

    if (!raw) {
      console.error('AI_EMPTY');
      return null;
    }

    const j = JSON.parse(raw);

    if (
      typeof j.title !== 'string' ||
      typeof j.body !== 'string' ||
      typeof j.meaning !== 'string'
    ) {
      console.error('AI_INVALID_FIELDS');
      return null;
    }

    const title = cleanAI(j.title);
    const body = cleanAI(j.body);
    const meaning = cleanAI(j.meaning);
    const joke = cleanAI(j.joke || '');

    if (
      !title ||
      !body ||
      !meaning
    ) {
      return null;
    }

    // Entire editorial content must pass Russian-language QA.
    if (
      !isRussianEnough(
        `${title}\n${body}\n${meaning}\n${joke}`
      )
    ) {
      console.error('RU_QA_FAILED', c.key);
      return null;
    }

    const flag =
      c.region === 'RUSSIA'
        ? '🇷🇺'
        : '🌍';

    const jokeBlock =
      joke && isRussianEnough(joke)
        ? `\n\n😏 ${escapeHtml(joke)}`
        : '';

    const sourceName =
      sourceToRussian(c.source);

    return (
      `${flag} <b>${escapeHtml(title)}</b>` +
      `\n\n${escapeHtml(body)}` +
      `\n\n<b>Что это значит:</b> ${escapeHtml(meaning)}` +
      jokeBlock +
      `\n\n📰 Источник: ${escapeHtml(sourceName)}` +
      ` · ${formatMoscow(c.time)}` +
      `\n🔗 <a href="${escapeHtmlAttr(c.link)}">Подробнее</a>`
    );

  } catch (err) {
    console.error(
      'AI_EDITOR_ERROR',
      err?.message || String(err)
    );
    return null;
  }
}

/* =========================================================
   RUSSIAN QA
========================================================= */

function isRussianEnough(text) {
  const clean = String(text)
    .replace(
      /https?:\/\/\S+/gi,
      ''
    )
    .replace(
      /<[^>]*>/g,
      ''
    );

  const cyr =
    (clean.match(/[А-Яа-яЁё]/g) || [])
      .length;

  const lat =
    (clean.match(/[A-Za-z]/g) || [])
      .length;

  const words =
    clean
      .split(/\s+/)
      .filter(Boolean)
      .length;

  if (words < 8) return false;
  if (cyr < 30) return false;

  // English may not dominate the final text.
  if (lat > 8 && lat > cyr * 0.12) {
    return false;
  }

  // Detect obvious unfinished/template output.
  if (
    /\.\.\./.test(clean) ||
    /\{\{|\}\}/.test(clean) ||
    /\bTODO\b/i.test(clean) ||
    /\bPLACEHOLDER\b/i.test(clean)
  ) {
    return false;
  }

  return true;
}

/* =========================================================
   TELEGRAM
========================================================= */

async function sendTelegram(env, text) {
  let lastError = null;

  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      const response = await fetch(
        `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
        {
          method: 'POST',
          headers: {
            'content-type': 'application/json'
          },
          body: JSON.stringify({
            chat_id: '@intilyshop',
            text,
            parse_mode: 'HTML',
            disable_web_page_preview: true
          })
        }
      );

      const data =
        await response.json().catch(
          () => ({})
        );

      if (
        response.ok &&
        data.ok
      ) {
        return data;
      }

      const retry =
        data?.parameters?.retry_after;

      lastError = new Error(
        `Telegram ${response.status}: ${
          data?.description || 'unknown error'
        }`
      );

      // Respect Telegram rate limits.
      const wait =
        Number.isFinite(retry)
          ? Math.min(retry, 60)
          : Math.min(
              2 ** attempt,
              30
            );

      await sleep(wait * 1000);

    } catch (err) {
      lastError = err;

      await sleep(
        Math.min(
          2 ** attempt,
          30
        ) * 1000
      );
    }
  }

  throw lastError || new Error(
    'Telegram publishing failed'
  );
}

/* =========================================================
   HELPERS
========================================================= */

function cleanAI(value) {
  return String(value)
    .replace(/\r/g, '')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeHtmlAttr(value) {
  return escapeHtml(value)
    .replace(/'/g, '&#39;');
}

function sourceToRussian(source) {
  const s =
    String(source)
      .toLowerCase()
      .trim();

  const map = {
    'reuters': 'Reuters',
    'bloomberg': 'Bloomberg',
    'financial times': 'Financial Times',
    'the verge': 'The Verge',
    'techcrunch': 'TechCrunch',
    'tass': 'ТАСС',
    'interfax': 'Интерфакс',
    'рбк': 'РБК',
    'коммерсантъ': 'Коммерсантъ',
    'ведомости': 'Ведомости'
  };

  return map[s] || source;
}

function formatMoscow(timestamp) {
  return new Date(timestamp)
    .toLocaleString(
      'ru-RU',
      {
        timeZone: 'Europe/Moscow',
        dateStyle: 'short',
        timeStyle: 'short'
      }
    ) + ' МСК';
}

async function sha(s) {
  const buffer =
    await crypto.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(s)
    );

  return [...new Uint8Array(buffer)]
    .map(
      x =>
        x.toString(16)
          .padStart(2, '0')
    )
    .join('');
}

function sleep(ms) {
  return new Promise(
    resolve => setTimeout(resolve, ms)
  );
}
