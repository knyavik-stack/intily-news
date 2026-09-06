"""Best-effort article image extraction and Telegram photo delivery for Intily.

The resolver is deliberately publisher-first: Google News is only a discovery
transport. It must never become the image source. Candidate extraction is
multi-strategy and validation happens per candidate so one broken/placeholder
image does not force a text-only fallback when a later publisher image works.
"""

import html
import json
import re
import struct
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_HTML_BYTES = 2 * 1024 * 1024
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 150
IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
GOOGLE_NEWS_HOSTS = {'news.google.com', 'www.news.google.com'}
MAX_IMAGE_CANDIDATES = 8


class _ArticleParser(HTMLParser):
    """Extract image/canonical metadata without depending on third-party HTML libs."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = []
        self.links = []
        self.images = []
        self.canonical = []
        self._jsonld = []
        self._jsonld_depth = 0
        self._jsonld_buffer = []

    @staticmethod
    def _attrs(attrs):
        return {str(k).lower(): str(v or '').strip() for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = self._attrs(attrs)
        if tag == 'meta':
            key = (a.get('property') or a.get('name') or '').lower()
            content = html.unescape(a.get('content', '')).strip()
            if key and content:
                self.meta.append((key, content))
        elif tag == 'link':
            rel = a.get('rel', '').lower().split()
            href = html.unescape(a.get('href', '')).strip()
            if href:
                self.links.append((rel, href))
                if 'canonical' in rel:
                    self.canonical.append(href)
        elif tag == 'img':
            for key in ('src', 'data-src', 'data-lazy-src', 'data-original', 'data-image'):
                value = html.unescape(a.get(key, '')).strip()
                if value:
                    self.images.append((key, value, a.get('srcset', ''), a.get('alt', ''), a.get('class', '')))
                    break
            else:
                if a.get('srcset'):
                    self.images.append(('srcset', '', a.get('srcset', ''), a.get('alt', ''), a.get('class', '')))
        elif tag == 'script':
            typ = a.get('type', '').lower()
            if typ == 'application/ld+json':
                self._jsonld_depth = 1
                self._jsonld_buffer = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() == 'script' and self._jsonld_depth:
            self._finish_jsonld()

    def handle_data(self, data):
        if self._jsonld_depth:
            self._jsonld_buffer.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self._jsonld_depth:
            self._finish_jsonld()

    def _finish_jsonld(self):
        raw = ''.join(self._jsonld_buffer).strip()
        self._jsonld_depth = 0
        self._jsonld_buffer = []
        if raw:
            self._jsonld.append(raw)


def _request(url, headers=None, timeout=12, max_bytes=None):
    req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        content_type = (response.headers.get('Content-Type') or '').split(';', 1)[0].lower()
        length = response.headers.get('Content-Length')
        if length and max_bytes and int(length) > max_bytes:
            raise ValueError('IMAGE_TOO_LARGE')
        data = response.read((max_bytes or MAX_HTML_BYTES) + 1)
        if max_bytes and len(data) > max_bytes:
            raise ValueError('IMAGE_TOO_LARGE')
        return data, content_type, response.geturl()


def _host(url):
    try:
        return urllib.parse.urlsplit(url).netloc.lower().split('@')[-1].split(':', 1)[0]
    except Exception:
        return ''


def _is_absolute(value):
    return value.startswith(('http://', 'https://'))


def _srcset_candidates(value):
    out = []
    for part in value.split(','):
        token = part.strip().split()
        if not token:
            continue
        url = token[0]
        descriptor = token[1] if len(token) > 1 else ''
        score = 0
        match = re.match(r'(\d+)(w|x)?$', descriptor, re.I)
        if match:
            score = int(match.group(1))
            if match.group(2) == 'x':
                score *= 1000
        out.append((score, url))
    return [url for _score, url in sorted(out, reverse=True)]


def _looks_placeholder(value):
    low = urllib.parse.unquote(str(value or '')).lower()
    return any(term in low for term in (
        'favicon', 'placeholder', 'default-image', 'default_image',
        '/logo', 'logo.', 'avatar', 'icon.', 'spacer.', 'pixel.',
        'google-news', 'googleusercontent'
    ))


def _parse_jsonld_image(value, out):
    if isinstance(value, str):
        value = value.strip()
        if _is_absolute(value):
            out.append(('jsonld_image', value))
        return
    if isinstance(value, list):
        for item in value:
            _parse_jsonld_image(item, out)
        return
    if isinstance(value, dict):
        for key in ('url', 'contentUrl'):
            if key in value:
                _parse_jsonld_image(value[key], out)
        if 'image' in value:
            _parse_jsonld_image(value['image'], out)
        if '@graph' in value:
            _parse_jsonld_image(value['@graph'], out)


def _meta_image_candidates(text):
    parser = _ArticleParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        # Metadata extraction should be best effort even for malformed publisher HTML.
        pass

    out = []
    meta_map = {}
    for key, value in parser.meta:
        meta_map.setdefault(key, []).append(value)

    for key in ('og:image', 'og:image:url'):
        for value in meta_map.get(key, []):
            out.append(('og_image', value))
    for key in ('twitter:image', 'twitter:image:src'):
        for value in meta_map.get(key, []):
            out.append(('twitter_image', value))

    for rels, href in parser.links:
        if 'image_src' in rels:
            out.append(('image_src', href))

    for raw in parser._jsonld:
        try:
            payload = json.loads(html.unescape(raw))
        except Exception:
            continue
        _parse_jsonld_image(payload, out)

    # Last-resort publisher HTML images. Prefer lazy/source-set URLs before plain src.
    for kind, value, srcset, alt, css_class in parser.images:
        candidates = _srcset_candidates(srcset) if srcset else []
        if value:
            candidates.insert(0, value)
        for candidate in candidates[:3]:
            out.append(('html_img', candidate))

    deduped = []
    seen = set()
    for method, value in out:
        value = html.unescape(str(value or '').strip())
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append((method, value))
    return deduped, parser


def resolve_article_url(article_url):
    """Resolve a Google News item to the real publisher article URL."""
    if not article_url.startswith(('http://', 'https://')):
        raise ValueError('ARTICLE_URL_INVALID')

    data, content_type, final_url = _request(article_url, {
        'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
        'Accept': 'text/html,application/xhtml+xml'
    }, 12, MAX_HTML_BYTES)

    final_host = _host(final_url)
    if final_host not in GOOGLE_NEWS_HOSTS:
        return final_url, data, content_type

    # Some wrappers do not redirect but expose the publisher URL as canonical/og:url.
    text = data.decode('utf-8', 'replace')
    candidates, parser = _meta_image_candidates(text)
    source_urls = list(parser.canonical)
    for key, value in parser.meta:
        if key == 'og:url':
            source_urls.append(value)
    for source_url in source_urls:
        resolved = urllib.parse.urljoin(final_url, source_url)
        if _host(resolved) in GOOGLE_NEWS_HOSTS or not _is_absolute(resolved):
            continue
        source_data, source_type, source_final = _request(resolved, {
            'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
            'Accept': 'text/html,application/xhtml+xml'
        }, 12, MAX_HTML_BYTES)
        if _host(source_final) not in GOOGLE_NEWS_HOSTS:
            return source_final, source_data, source_type

    raise ValueError('ARTICLE_SOURCE_UNRESOLVED')


def extract_image_candidates(article_url):
    final_url, data, _ = resolve_article_url(article_url)
    text = data.decode('utf-8', 'replace')
    candidates, _parser = _meta_image_candidates(text)
    if not candidates:
        raise ValueError('IMAGE_NOT_FOUND')

    source_host = _host(final_url)
    priority = {'og_image': 0, 'jsonld_image': 1, 'image_src': 2, 'twitter_image': 3, 'html_img': 4}
    ranked = []
    for method, value in candidates:
        image_url = urllib.parse.urljoin(final_url, value)
        image_host = _host(image_url)
        penalty = 20 if source_host not in GOOGLE_NEWS_HOSTS and image_host in GOOGLE_NEWS_HOSTS else 0
        placeholder_penalty = 50 if _looks_placeholder(image_url) else 0
        same_host_bonus = -0.5 if image_host == source_host else 0
        ranked.append((priority.get(method, 9) + penalty + placeholder_penalty + same_host_bonus, method, image_url))
    ranked.sort(key=lambda row: (row[0], row[1], row[2]))
    return ranked[:MAX_IMAGE_CANDIDATES], final_url


def extract_image_url(article_url):
    ranked, final_url = extract_image_candidates(article_url)
    if not ranked:
        raise ValueError('IMAGE_NOT_FOUND')
    _rank, method, image_url = ranked[0]
    return image_url, method, final_url


def _dimensions(data, content_type):
    try:
        if content_type == 'image/png' and data[:8] == b'\x89PNG\r\n\x1a\n':
            return struct.unpack('>II', data[16:24])
        if content_type == 'image/gif' and data[:6] in (b'GIF87a', b'GIF89a'):
            return struct.unpack('<HH', data[6:10])
        if content_type == 'image/webp' and len(data) >= 30 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            if data[12:16] == b'VP8X':
                return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
        if content_type == 'image/jpeg' and data[:2] == b'\xff\xd8':
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                i += 2
                if marker in (0xD8, 0xD9):
                    continue
                if i + 2 > len(data):
                    break
                n = int.from_bytes(data[i:i + 2], 'big')
                if marker in list(range(0xC0, 0xC4)) + list(range(0xC5, 0xC8)) + list(range(0xC9, 0xCC)) + list(range(0xCD, 0xD0)):
                    if i + 7 <= len(data):
                        return int.from_bytes(data[i + 5:i + 7], 'big'), int.from_bytes(data[i + 3:i + 5], 'big')
                i += max(n, 2)
    except Exception:
        return None
    return None


def fetch_image(article_url):
    ranked, source_url = extract_image_candidates(article_url)
    errors = []
    for _rank, method, image_url in ranked:
        try:
            data, content_type, final_url = _request(image_url, {
                'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
                'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
            }, 15, MAX_IMAGE_BYTES)
            if content_type not in IMAGE_TYPES:
                raise ValueError('IMAGE_CONTENT_TYPE_INVALID')
            dims = _dimensions(data, content_type)
            if not dims or dims[0] < MIN_IMAGE_WIDTH or dims[1] < MIN_IMAGE_HEIGHT:
                raise ValueError('IMAGE_DIMENSIONS_INVALID')
            return {
                'data': data, 'content_type': content_type, 'url': final_url,
                'method': method, 'source_url': source_url,
                'width': dims[0], 'height': dims[1]
            }
        except Exception as exc:
            errors.append(f'{method}:{str(exc)[:100]}')
    raise ValueError('IMAGE_CANDIDATES_FAILED: ' + ' | '.join(errors[:4]))


def _field(name, value, boundary):
    return ('--' + boundary + '\r\nContent-Disposition: form-data; name="' + name + '"\r\n\r\n').encode() + str(value).encode() + b'\r\n'


def _file(field, filename, data, content_type, boundary):
    return (('--' + boundary + '\r\nContent-Disposition: form-data; name="' + field + '"; filename="' + filename + '"\r\nContent-Type: ' + content_type + '\r\n\r\n').encode() + data + b'\r\n')


def send_photo(token, chat_id, caption, image):
    boundary = '----IntilyBoundary7MA4YWxkTrZu0gW'
    ext = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif'}[image['content_type']]
    body = b''.join([
        _field('chat_id', chat_id, boundary),
        _field('parse_mode', 'HTML', boundary),
        _field('disable_notification', 'false', boundary),
        _field('caption', caption, boundary),
        _file('photo', 'intily.' + ext, image['data'], image['content_type'], boundary),
        ('--' + boundary + '--\r\n').encode(),
    ])
    req = urllib.request.Request(
        'https://api.telegram.org/bot' + token + '/sendPhoto',
        data=body,
        headers={'Content-Type': 'multipart/form-data; boundary=' + boundary},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read().decode('utf-8', 'replace'))
    if not result.get('ok'):
        raise RuntimeError('TELEGRAM_SEND_PHOTO_FAILED: ' + str(result)[:300])
    return result


def publish_with_optional_image(text, article_url, token, chat_id, fallback_send):
    telemetry = {
        'status': 'not_attempted', 'method': None, 'url': None, 'source_url': None,
        'width': None, 'height': None, 'error': None, 'attempts': 0,
    }
    try:
        telemetry['attempts'] = 1
        image = fetch_image(article_url)
        if len(text) > 1024:
            raise ValueError('CAPTION_TOO_LONG')
        result = send_photo(token, chat_id, text, image)
        telemetry.update(
            status='sent', method=image['method'], url=image['url'], source_url=image['source_url'],
            width=image['width'], height=image['height']
        )
        print('IMAGE_SOURCE_RESOLVED', image['source_url'])
        print('IMAGE_FOUND', image['method'], image['width'], image['height'])
        print('IMAGE_VALIDATED', image['content_type'], len(image['data']))
        print('TELEGRAM_PHOTO_SENT', result.get('result', {}).get('message_id'))
        return telemetry
    except Exception as exc:
        telemetry.update(status='fallback_text', error=str(exc)[:240])
        print('IMAGE_FALLBACK_TEXT', telemetry['error'])
        fallback_send(text)
        return telemetry
