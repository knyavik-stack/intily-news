"""Resolve current Google News RSS article wrappers to publisher URLs.

Google News RSS article links are no longer reliably resolved by a normal HTTP
redirect. Current wrappers expose decoding parameters on the article page and
require a small internal ``batchexecute`` request. This module is deliberately
stdlib-only and returns the original URL on failure so discovery/publishing is
never blocked by media resolution.
"""

import base64
import json
import re
import urllib.parse
import urllib.request

GOOGLE_HOSTS = {'news.google.com', 'www.news.google.com'}
USER_AGENT = 'Mozilla/5.0 (compatible; IntilyNews/1.0)'


def _is_google_news(url):
    try:
        parsed = urllib.parse.urlsplit(url)
        return parsed.hostname in GOOGLE_HOSTS and '/articles/' in (parsed.path or '') or parsed.hostname in GOOGLE_HOSTS and '/rss/articles/' in (parsed.path or '')
    except Exception:
        return False


def _get(url, headers=None, timeout=12):
    req = urllib.request.Request(url, headers=headers or {'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), dict(response.headers), response.geturl()


def _article_id(url):
    path = urllib.parse.urlsplit(url).path
    match = re.search(r'/(?:rss/)?articles/([^/?]+)', path)
    return match.group(1) if match else None


def _legacy_decode(article_id):
    """Support old CBMi-style IDs when they still contain the URL directly."""
    try:
        padded = article_id + '=' * (-len(article_id) % 4)
        raw = base64.urlsafe_b64decode(padded.encode())
        match = re.search(rb'https?://[^\x00\"\\\s]+', raw)
        if match:
            return match.group(0).decode('utf-8', 'ignore')
    except Exception:
        pass
    return None


def _params(html_text):
    signature = re.search(r'data-n-a-sg="([^"]+)"', html_text)
    timestamp = re.search(r'data-n-a-ts="([^"]+)"', html_text)
    if not signature or not timestamp:
        return None, None
    return signature.group(1), timestamp.group(1)


def _batchexecute(article_id, signature, timestamp, cookies=''):
    inner = json.dumps([
        'garturlreq',
        [["X", "X", ["X", "X"], None, None, 1, 1, 'US:en', None, 1, None, None, None, None, None, 0, 1],
         'X', 'X', 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
        article_id,
        int(timestamp),
        signature,
    ], separators=(',', ':'))
    payload = json.dumps([[['Fbv4je', inner]]], separators=(',', ':'))
    body = ('f.req=' + urllib.parse.quote(payload, safe='')).encode()
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Origin': 'https://news.google.com',
        'Referer': 'https://news.google.com/',
        'X-Same-Domain': '1',
    }
    if cookies:
        headers['Cookie'] = cookies
    req = urllib.request.Request(
        'https://news.google.com/_/DotsSplashUi/data/batchexecute',
        data=body,
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        raw = response.read().decode('utf-8', 'replace')

    parts = raw.split('\n\n', 1)
    if len(parts) != 2:
        return None
    try:
        outer = json.loads(parts[1].strip())
        inner_json = outer[0][2]
        decoded = json.loads(inner_json)
        value = decoded[1]
        return value if isinstance(value, str) and value.startswith(('http://', 'https://')) else None
    except Exception:
        return None


def resolve(url):
    """Return the publisher URL, or the original URL if resolution fails."""
    if not url or not _is_google_news(url):
        return url

    article_id = _article_id(url)
    if not article_id:
        return url

    legacy = _legacy_decode(article_id)
    if legacy and not _is_google_news(legacy):
        return legacy

    cookies = 'CONSENT=PENDING+987'
    try:
        data, headers, _final = _get(
            'https://news.google.com/articles/' + urllib.parse.quote(article_id, safe=''),
            {
                'User-Agent': USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cookie': cookies,
            },
        )
        set_cookie = headers.get('Set-Cookie', '')
        if set_cookie:
            cookies = set_cookie.split(';', 1)[0]
        signature, timestamp = _params(data.decode('utf-8', 'replace'))
        if signature and timestamp:
            decoded = _batchexecute(article_id, signature, timestamp, cookies)
            if decoded and not _is_google_news(decoded):
                return decoded
    except Exception:
        pass
    return url
