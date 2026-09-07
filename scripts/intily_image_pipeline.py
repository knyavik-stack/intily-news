"""Best-effort article image extraction and Telegram photo delivery for Intily.

The resolver is publisher-first: Google News is only a discovery transport.
Candidate extraction is multi-strategy and validation happens per candidate.
"""

import html
import json
import re
import struct
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MAX_SOURCE_IMAGE_BYTES = 8 * 1024 * 1024
MAX_HTML_BYTES = 2 * 1024 * 1024
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 150
IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif'}
GOOGLE_NEWS_HOSTS = {'news.google.com', 'www.news.google.com'}
MAX_IMAGE_CANDIDATES = 12
MAX_TELEGRAM_CAPTION_BYTES = 1024
ALLOWED_HTML_TAGS = {'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del', 'code', 'pre', 'a', 'blockquote', 'tg-spoiler'}


class _ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = []
        self.links = []
        self.images = []
        self.sources = []
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
            values = []
            for key in ('src', 'data-src', 'data-lazy-src', 'data-original', 'data-image', 'data-filename', 'data-url'):
                value = html.unescape(a.get(key, '')).strip()
                if value:
                    values.append((key, value))
            srcset = a.get('srcset') or a.get('data-srcset') or ''
            if values or srcset:
                self.images.append((values, srcset, a.get('alt', ''), a.get('class', '')))
        elif tag == 'source':
            srcset = a.get('srcset') or a.get('data-srcset') or a.get('src') or ''
            if srcset:
                self.sources.append(srcset)
        elif tag == 'script' and a.get('type', '').lower() == 'application/ld+json':
            self._jsonld_depth = 1
            self._jsonld_buffer = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() == 'script' and self._jsonld_depth:
            self._jsonld.append(''.join(self._jsonld_buffer))
            self._jsonld_depth = 0
            self._jsonld_buffer = []

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self._jsonld_depth:
            self._jsonld.append(''.join(self._jsonld_buffer))
            self._jsonld_depth = 0
            self._jsonld_buffer = []

    def handle_data(self, data):
        if self._jsonld_depth:
            self._jsonld_buffer.append(data)


def _host(url):
    try:
        return urllib.parse.urlsplit(url).netloc.lower().split('@')[-1].split(':', 1)[0]
    except Exception:
        return ''


def _is_absolute(url):
    try:
        return urllib.parse.urlsplit(url).scheme in ('http', 'https')
    except Exception:
        return False


def _request(url, headers, timeout, max_bytes):
    if not _is_absolute(url):
        raise ValueError('IMAGE_URL_SCHEME_INVALID')
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        content_type = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
        final_url = response.geturl()
        if not _is_absolute(final_url):
            raise ValueError('IMAGE_FINAL_URL_SCHEME_INVALID')
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError('IMAGE_SOURCE_TOO_LARGE')
        return data, content_type, final_url


def _looks_placeholder(url):
    lower = url.lower()
    return any(token in lower for token in ('placeholder', 'default-image', 'no-image', 'no_image', 'spacer.gif'))


def _srcset_candidates(value):
    result = []
    for item in str(value or '').split(','):
        token = item.strip().split()[0] if item.strip() else ''
        if token:
            result.append(token)
    return result


def _parse_jsonld_image(payload, out):
    if isinstance(payload, dict):
        for key in ('image', 'thumbnailUrl'):
            value = payload.get(key)
            if isinstance(value, str):
                out.append(('jsonld_image', value))
            elif isinstance(value, dict):
                for subkey in ('url', 'contentUrl'):
                    if isinstance(value.get(subkey), str):
                        out.append(('jsonld_image', value[subkey]))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        out.append(('jsonld_image', item))
                    elif isinstance(item, dict):
                        for subkey in ('url', 'contentUrl'):
                            if isinstance(item.get(subkey), str):
                                out.append(('jsonld_image', item[subkey]))
        for value in payload.values():
            if isinstance(value, (dict, list)):
                _parse_jsonld_image(value, out)
    elif isinstance(payload, list):
        for value in payload:
            _parse_jsonld_image(value, out)


def _meta_image_candidates(text):
    parser = _ArticleParser()
    parser.feed(text)
    out = []
    meta_map = {}
    for key, value in parser.meta:
        meta_map.setdefault(key, []).append(value)
    for key in ('og:image', 'og:image:url', 'og:image:secure_url', 'article:image'):
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
            _parse_jsonld_image(json.loads(html.unescape(raw)), out)
        except Exception:
            continue
    for values, srcset, _alt, _css_class in parser.images:
        candidates = _srcset_candidates(srcset) if srcset else []
        for _key, value in values:
            if value:
                candidates.insert(0, value)
        for candidate in candidates[:4]:
            out.append(('html_img', candidate))
    for srcset in parser.sources:
        for candidate in _srcset_candidates(srcset)[:4]:
            out.append(('html_source', candidate))
    for match in re.findall(r'url\s*\(\s*[\'"]?([^\'")\s]+)[\'"]?\s*\)', text, flags=re.I):
        clean_url = html.unescape(match).strip()
        if re.match(r'^https?://|^//|^/', clean_url):
            out.append(('css_image', clean_url))
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
    if not _is_absolute(article_url):
        raise ValueError('ARTICLE_URL_INVALID')
    data, content_type, final_url = _request(article_url, {
        'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
        'Accept': 'text/html,application/xhtml+xml'
    }, 12, MAX_HTML_BYTES)
    if _host(final_url) not in GOOGLE_NEWS_HOSTS:
        return final_url, data, content_type
    parser_candidates, parser = _meta_image_candidates(data.decode('utf-8', 'replace'))
    _ = parser_candidates
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
    candidates, _parser = _meta_image_candidates(data.decode('utf-8', 'replace'))
    if not candidates:
        raise ValueError('IMAGE_NOT_FOUND')
    source_host = _host(final_url)
    priority = {'og_image': 0, 'jsonld_image': 1, 'image_src': 2, 'twitter_image': 3,
                'html_img': 4, 'html_source': 5, 'css_image': 6}
    ranked = []
    for method, value in candidates:
        image_url = urllib.parse.urljoin(final_url, value)
        if not _is_absolute(image_url):
            continue
        image_host = _host(image_url)
        penalty = 20 if image_host in {'news.google.com', 'www.news.google.com'} else 0
        placeholder_penalty = 50 if _looks_placeholder(image_url) else 0
        same_host_bonus = -0.5 if image_host == source_host else 0
        ranked.append((priority.get(method, 9) + penalty + placeholder_penalty + same_host_bonus, method, image_url))
    return sorted(ranked, key=lambda row: (row[0], row[1], row[2]))[:MAX_IMAGE_CANDIDATES], final_url


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
        if content_type == 'image/webp' and len(data) >= 30 and data[:4] == b'RIFF' and data[8:12] == b'WEBP' and data[12:16] == b'VP8X':
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
    try:
        from io import BytesIO
        from PIL import Image
        with Image.open(BytesIO(data)) as image:
            return image.size
    except Exception:
        return None


def fetch_image(article_url):
    ranked, source_url = extract_image_candidates(article_url)
    errors = []
    for _rank, method, image_url in ranked:
        try:
            data, content_type, final_url = _request(image_url, {
                'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
                'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': source_url,
            }, 15, MAX_SOURCE_IMAGE_BYTES)
            if content_type not in IMAGE_TYPES:
                raise ValueError('IMAGE_CONTENT_TYPE_INVALID')
            dims = _dimensions(data, content_type)
            if not dims or dims[0] < MIN_IMAGE_WIDTH or dims[1] < MIN_IMAGE_HEIGHT:
                raise ValueError('IMAGE_DIMENSIONS_INVALID')
            return {'data': data, 'content_type': content_type, 'url': final_url,
                    'method': method, 'source_url': source_url,
                    'width': dims[0], 'height': dims[1]}
        except Exception as exc:
            errors.append(f'{method}:{str(exc)[:100]}')
    raise ValueError('IMAGE_CANDIDATES_FAILED: ' + ' | '.join(errors[:6]))


def _sanitize_telegram_html(text):
    """Preserve supported Telegram HTML formatting while removing unsafe markup."""
    source = str(text or '')
    token_re = re.compile(r'<[^>]*>')
    out = []
    pos = 0
    for match in token_re.finditer(source):
        if match.start() > pos:
            chunk = source[pos:match.start()]
            # Existing entities are kept; raw ampersands are escaped without
            # double-escaping valid entities produced by the editorial formatter.
            chunk = re.sub(r'&(?!#\d+;|#x[0-9A-Fa-f]+;|(?:amp|lt|gt|quot);)', '&amp;', chunk)
            chunk = chunk.replace('<', '&lt;').replace('>', '&gt;')
            out.append(chunk)
        raw = match.group(0)
        tag_match = re.fullmatch(r'</?\s*([A-Za-z0-9-]+)([^>]*)>', raw)
        if not tag_match:
            out.append(html.escape(raw, quote=False))
            pos = match.end()
            continue
        tag = tag_match.group(1).lower()
        attrs = tag_match.group(2) or ''
        closing = raw.lstrip().startswith('</')
        if tag not in ALLOWED_HTML_TAGS:
            pos = match.end()
            continue
        if closing:
            out.append(f'</{tag}>')
        elif tag == 'a':
            href_match = re.search(r'href\s*=\s*["\']([^"\']+)["\']', attrs, flags=re.I)
            href = html.unescape(href_match.group(1)).strip() if href_match else ''
            parsed = urllib.parse.urlsplit(href)
            if parsed.scheme.lower() in {'http', 'https', 'tg'} and parsed.netloc or parsed.scheme.lower() == 'tg':
                out.append(f'<a href="{html.escape(href, quote=True)}">')
            else:
                out.append('<a>')
        else:
            out.append(f'<{tag}>')
        pos = match.end()
    if pos < len(source):
        chunk = source[pos:]
        chunk = re.sub(r'&(?!#\d+;|#x[0-9A-Fa-f]+;|(?:amp|lt|gt|quot);)', '&amp;', chunk)
        chunk = chunk.replace('<', '&lt;').replace('>', '&gt;')
        out.append(chunk)
    return ''.join(out)


def _photo_caption(text, limit=MAX_TELEGRAM_CAPTION_BYTES):
    """Return safe Telegram HTML, preserving formatting, bounded after escaping."""
    sanitized = _sanitize_telegram_html(text)
    if len(sanitized) <= limit:
        return sanitized
    parts = re.findall(r'</?[^>]+>|[^<]+', sanitized)
    result = []
    open_tags = []
    used = 0
    for part in parts:
        if part.startswith('<'):
            tag_match = re.fullmatch(r'<(/?)([A-Za-z0-9-]+)(?: [^>]*)?>', part)
            if not tag_match:
                continue
            closing, tag = tag_match.groups()
            if closing:
                if tag in open_tags:
                    while open_tags:
                        current = open_tags.pop()
                        if current == tag:
                            break
                        result.append(f'</{current}>')
                    result.append(part)
            else:
                result.append(part)
                open_tags.append(tag)
            continue
        remaining = limit - used - 1
        if remaining <= 0:
            break
        if len(part) <= remaining:
            result.append(part)
            used += len(part)
        else:
            result.append(part[:remaining].rstrip() + '…')
            used += remaining + 1
            break
    while open_tags:
        result.append(f'</{open_tags.pop()}>')
    return ''.join(result)[:limit]


def _field(name, value, boundary):
    return ('--' + boundary + '\r\nContent-Disposition: form-data; name="' + name + '\r\n\r\n').encode() + str(value).encode() + b'\r\n'


def _file(field, filename, data, content_type, boundary):
    return (('--' + boundary + '\r\nContent-Disposition: form-data; name="' + field + '"; filename="' + filename + '"\r\nContent-Type: ' + content_type + '\r\n\r\n').encode() + data + b'\r\n')


def send_photo(token, chat_id, caption, image):
    boundary = '----IntilyBoundary7MA4YWxkTrZu0gW'
    ext = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif', 'image/avif': 'jpg'}[image['content_type']]
    body = b''.join([_field('chat_id', chat_id, boundary), _field('parse_mode', 'HTML', boundary),
                     _field('disable_notification', 'false', boundary), _field('caption', caption, boundary),
                     _file('photo', 'intily.' + ext, image['data'], image['content_type'], boundary),
                     ('--' + boundary + '--\r\n').encode()])
    req = urllib.request.Request('https://api.telegram.org/bot' + token + '/sendPhoto', data=body,
                                 headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read().decode('utf-8', 'replace'))
    if not result.get('ok'):
        raise RuntimeError('TELEGRAM_SEND_PHOTO_FAILED: ' + str(result)[:300])
    return result


def publish_with_optional_image(text, article_url, token, chat_id, fallback_send):
    telemetry = {'status': 'not_attempted', 'method': None, 'url': None, 'source_url': None,
                 'width': None, 'height': None, 'error': None, 'attempts': 0}
    try:
        telemetry['attempts'] = 1
        image = fetch_image(article_url)
        caption = _photo_caption(text)
        result = send_photo(token, chat_id, caption, image)
        telemetry.update(status='sent', method=image['method'], url=image['url'], source_url=image['source_url'],
                         width=image['width'], height=image['height'])
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
