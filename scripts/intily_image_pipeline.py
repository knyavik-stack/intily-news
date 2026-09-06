"""Best-effort article image extraction and Telegram photo delivery for Intily."""

import html
import json
import re
import struct
import urllib.parse
import urllib.request

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_HTML_BYTES = 2 * 1024 * 1024
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 150
IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
GOOGLE_NEWS_HOSTS = {'news.google.com', 'www.news.google.com'}


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


def _meta_image_candidates(text):
    patterns = [
        ('og_image', r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\'][^>]*>'),
        ('og_image', r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\'][^>]*>'),
        ('twitter_image', r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\'][^>]*>'),
        ('twitter_image', r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\'][^>]*>'),
        ('image_src', r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\'][^>]*>'),
        ('image_src', r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']image_src["\'][^>]*>'),
    ]
    out = []
    for method, pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            value = html.unescape(match.group(1).strip())
            if value and (method, value) not in out:
                out.append((method, value))

    # JSON-LD is a useful fallback for publishers whose meta tags are incomplete.
    for match in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.I | re.S):
        try:
            payload = json.loads(html.unescape(match.group(1).strip()))
        except Exception:
            continue

        def collect(value):
            if isinstance(value, str) and value.startswith(('http://', 'https://')):
                out.append(('jsonld_image', value.strip()))
            elif isinstance(value, list):
                for item in value:
                    collect(item)
            elif isinstance(value, dict):
                if 'url' in value:
                    collect(value['url'])
                if 'image' in value:
                    collect(value['image'])

        collect(payload.get('image') if isinstance(payload, dict) else payload)

    deduped = []
    for method, value in out:
        if (method, value) not in deduped:
            deduped.append((method, value))
    return deduped


def resolve_article_url(article_url):
    """Follow Google News RSS redirects to the publisher's real article URL."""
    if not article_url.startswith(('http://', 'https://')):
        raise ValueError('ARTICLE_URL_INVALID')

    data, content_type, final_url = _request(article_url, {
        'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
        'Accept': 'text/html,application/xhtml+xml'
    }, 12, MAX_HTML_BYTES)

    final_host = _host(final_url)
    if final_host not in GOOGLE_NEWS_HOSTS:
        return final_url, data, content_type

    # A Google News wrapper should normally redirect to the publisher. If it does
    # not, do not scrape Google News' generic preview image: that is exactly the
    # class of wrong-image failure this resolver is designed to prevent.
    raise ValueError('ARTICLE_SOURCE_UNRESOLVED')


def extract_image_url(article_url):
    final_url, data, _ = resolve_article_url(article_url)
    text = data.decode('utf-8', 'replace')
    candidates = _meta_image_candidates(text)
    if not candidates:
        raise ValueError('IMAGE_NOT_FOUND')

    # Prefer the publisher's OG image. JSON-LD / twitter / image_src are fallbacks.
    source_host = _host(final_url)
    ranked = []
    priority = {'og_image': 0, 'jsonld_image': 1, 'image_src': 2, 'twitter_image': 3}
    for method, value in candidates:
        image_url = urllib.parse.urljoin(final_url, value)
        image_host = _host(image_url)
        generic_google_penalty = 20 if source_host not in GOOGLE_NEWS_HOSTS and image_host in GOOGLE_NEWS_HOSTS else 0
        ranked.append((priority.get(method, 9) + generic_google_penalty, method, image_url))
    ranked.sort(key=lambda row: row[0])
    _, method, image_url = ranked[0]
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
    image_url, method, source_url = extract_image_url(article_url)
    data, content_type, final_url = _request(image_url, {
        'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
    }, 15, MAX_IMAGE_BYTES)
    if content_type not in IMAGE_TYPES:
        raise ValueError('IMAGE_CONTENT_TYPE_INVALID')
    dims = _dimensions(data, content_type)
    if not dims or dims[0] < MIN_IMAGE_WIDTH or dims[1] < MIN_IMAGE_HEIGHT:
        raise ValueError('IMAGE_DIMENSIONS_INVALID')
    return {'data': data, 'content_type': content_type, 'url': final_url, 'method': method, 'source_url': source_url, 'width': dims[0], 'height': dims[1]}


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
    telemetry = {'status': 'not_attempted', 'method': None, 'url': None, 'source_url': None, 'width': None, 'height': None, 'error': None}
    try:
        image = fetch_image(article_url)
        if len(text) > 1024:
            raise ValueError('CAPTION_TOO_LONG')
        result = send_photo(token, chat_id, text, image)
        telemetry.update(status='sent', method=image['method'], url=image['url'], source_url=image['source_url'], width=image['width'], height=image['height'])
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
