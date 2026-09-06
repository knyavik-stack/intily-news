"""Best-effort article image extraction and Telegram photo delivery for Intily.

The image layer is presentation-only: failure to find/download/upload an image
must never block publication of an otherwise valid editorial post.
"""

import html
import json
import re
import struct
import urllib.error
import urllib.parse
import urllib.request

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_HTML_BYTES = 2 * 1024 * 1024
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 150

IMAGE_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif'
}


def _request(url, headers=None, timeout=12, max_bytes=None):
    req = urllib.request.Request(
        url,
        headers=headers or {
            'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)'
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        content_type = (response.headers.get('Content-Type') or '').split(';', 1)[0].lower()
        length = response.headers.get('Content-Length')
        if length and max_bytes and int(length) > max_bytes:
            raise ValueError('IMAGE_TOO_LARGE')
        data = response.read((max_bytes or MAX_HTML_BYTES) + 1)
        if max_bytes and len(data) > max_bytes:
            raise ValueError('IMAGE_TOO_LARGE')
        return data, content_type, response.geturl()


def _meta_image(html_text):
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\'][^>]*>',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\'][^>]*>',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\'][^>]*>',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\'][^>]*>',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, re.I)
        if match:
            return html.unescape(match.group(1).strip())
    return ''


def extract_image_url(article_url):
    if not article_url.startswith(('http://', 'https://')):
        raise ValueError('ARTICLE_URL_INVALID')
    data, _, final_url = _request(
        article_url,
        headers={
            'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
            'Accept': 'text/html,application/xhtml+xml'
        },
        timeout=12,
        max_bytes=MAX_HTML_BYTES,
    )
    text = data.decode('utf-8', 'replace')
    image = _meta_image(text)
    if not image:
        raise ValueError('IMAGE_NOT_FOUND')
    return urllib.parse.urljoin(final_url, image), 'og_image'


def _dimensions(data, content_type):
    try:
        if content_type == 'image/png' and data[:8] == b'\x89PNG\r\n\x1a\n':
            return struct.unpack('>II', data[16:24])
        if content_type == 'image/gif' and data[:6] in (b'GIF87a', b'GIF89a'):
            return struct.unpack('<HH', data[6:10])
        if content_type == 'image/webp' and data[:12] == b'RIFF' + data[4:8] + b'WEBP':
            if data[12:16] == b'VP8X' and len(data) >= 30:
                w = 1 + int.from_bytes(data[24:27], 'little')
                h = 1 + int.from_bytes(data[27:30], 'little')
                return w, h
            if data[12:16] == b'VP8 ' and len(data) >= 30 and data[23:27] == b'\x9d\x01\x2a':
                return struct.unpack('<HH', data[26:30])
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
                segment_len = int.from_bytes(data[i:i + 2], 'big')
                if marker in range(0xC0, 0xC4) or marker in range(0xC5, 0xC8) or marker in range(0xC9, 0xCC) or marker in range(0xCD, 0xD0):
                    if i + 7 <= len(data):
                        h = int.from_bytes(data[i + 3:i + 5], 'big')
                        w = int.from_bytes(data[i + 5:i + 7], 'big')
                        return w, h
                i += max(segment_len, 2)
    except Exception:
        return None
    return None


def fetch_image(article_url):
    image_url, method = extract_image_url(article_url)
    data, content_type, final_url = _request(
        image_url,
        headers={
            'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
        },
        timeout=15,
        max_bytes=MAX_IMAGE_BYTES,
    )
    if content_type not in IMAGE_TYPES:
        raise ValueError('IMAGE_CONTENT_TYPE_INVALID')
    dims = _dimensions(data, content_type)
    if not dims or dims[0] < MIN_IMAGE_WIDTH or dims[1] < MIN_IMAGE_HEIGHT:
        raise ValueError('IMAGE_DIMENSIONS_INVALID')
    return {
        'data': data,
        'content_type': content_type,
        'url': final_url,
        'method': method,
        'width': dims[0],
        'height': dims[1],
    }


def _multipart(field, filename, data, content_type, boundary):
    return (
        ('--' + boundary + '\r\n').encode()
        + ('Content-Disposition: form-data; name="' + field + '"; filename="' + filename + '"\r\n').encode()
        + ('Content-Type: ' + content_type + '\r\n\r\n').encode()
        + data
        + b'\r\n'
    )


def send_photo(token, chat_id, caption, image):
    boundary = '----IntilyBoundary7MA4YWxkTrZu0gW'
    body = b''.join([
        _multipart('chat_id', 'chat.txt', str(chat_id).encode(), 'text/plain', boundary),
        _multipart('photo', 'intily.jpg' if image['content_type'] == 'image/jpeg' else 'intily.png', image['data'], image['content_type'], boundary),
        _multipart('caption', 'caption.txt', caption.encode('utf-8'), 'text/plain; charset=utf-8', boundary),
        ('--' + boundary + '--\r\n').encode(),
    ])
    url = 'https://api.telegram.org/bot' + token + '/sendPhoto'
    req = urllib.request.Request(
        url,
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
        'status': 'not_attempted',
        'method': None,
        'url': None,
        'width': None,
        'height': None,
        'error': None,
    }
    try:
        image = fetch_image(article_url)
        if len(text) > 1024:
            raise ValueError('CAPTION_TOO_LONG')
        result = send_photo(token, chat_id, text, image)
        telemetry.update({
            'status': 'sent',
            'method': image['method'],
            'url': image['url'],
            'width': image['width'],
            'height': image['height'],
        })
        print('IMAGE_FOUND', image['method'], image['width'], image['height'])
        print('IMAGE_VALIDATED', image['content_type'], len(image['data']))
        print('TELEGRAM_PHOTO_SENT', result.get('result', {}).get('message_id'))
        return telemetry
    except Exception as exc:
        telemetry['status'] = 'fallback_text'
        telemetry['error'] = str(exc)[:240]
        print('IMAGE_FALLBACK_TEXT', telemetry['error'])
        fallback_send(text)
        return telemetry
