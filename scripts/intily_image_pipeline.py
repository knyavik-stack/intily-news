import html
import json
import re
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from intily_image_hardening import (
    IMAGE_TYPES,
    MAX_IMAGE_CANDIDATES,
    MAX_SOURCE_IMAGE_BYTES,
    MIN_IMAGE_HEIGHT,
    MIN_IMAGE_WIDTH,
    extract_image_candidates,
    request as _request,
)

MAX_TELEGRAM_IMAGE_BYTES = 1_000_000
MAX_TELEGRAM_CAPTION_BYTES = 1024

ALLOWED_HTML_TAGS = {'b', 'strong', 'i', 'em', 'u', 's', 'code', 'pre', 'a'}


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
            if (parsed.scheme.lower() in {'http', 'https'} and parsed.netloc) or parsed.scheme.lower() == 'tg':
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
    """Return safe Telegram HTML only when the complete text fits the caption limit."""
    sanitized = _sanitize_telegram_html(text)
    if len(sanitized) <= limit:
        return sanitized
    raise ValueError('PHOTO_CAPTION_LIMIT_TEXT_SPLIT')


def _field(name, value, boundary):
    return ('--' + boundary + '\r\nContent-Disposition: form-data; name="' + name + '"\r\n\r\n').encode() + str(value).encode() + b'\r\n'


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
                 'width': None, 'height': None, 'error': None, 'attempts': 0, 'caption_mode': None}
    try:
        telemetry['attempts'] = 1
        image = fetch_image(article_url)
        try:
            caption = _photo_caption(text)
            result = send_photo(token, chat_id, caption, image)
            telemetry['caption_mode'] = 'full'
        except ValueError as exc:
            if str(exc) != 'PHOTO_CAPTION_LIMIT_TEXT_SPLIT':
                raise
            # Preserve the complete editorial text instead of truncating it:
            # publish the validated photo without a caption, then the full text.
            result = send_photo(token, chat_id, '', image)
            fallback_send(text)
            telemetry['caption_mode'] = 'photo_plus_full_text'
            telemetry['text_message_sent'] = True
        telemetry.update(status='sent', method=image['method'], url=image['url'], source_url=image['source_url'],
                         width=image['width'], height=image['height'])
        print('IMAGE_SOURCE_RESOLVED', image['source_url'])
        print('IMAGE_FOUND', image['method'], image['width'], image['height'])
        print('IMAGE_VALIDATED', image['content_type'], len(image['data']))
        print('TELEGRAM_PHOTO_SENT', result.get('result', {}).get('message_id'))
        if telemetry['caption_mode'] == 'photo_plus_full_text':
            print('TELEGRAM_FULL_TEXT_SENT_AFTER_PHOTO')
        return telemetry
    except Exception as exc:
        telemetry.update(status='fallback_text', error=str(exc)[:240])
        print('IMAGE_FALLBACK_TEXT', telemetry['error'])
        fallback_send(text)
        return telemetry
