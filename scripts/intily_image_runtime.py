"""Production image runtime with a strict <=1,000,000-byte payload cap."""

from io import BytesIO
from PIL import Image, ImageOps
import intily_image_hardening as hardening

MAX_TELEGRAM_IMAGE_BYTES = 1_000_000
MAX_SOURCE_IMAGE_BYTES = 8 * 1024 * 1024
JPEG_QUALITIES = (88, 82, 76, 70, 64, 58, 52, 46, 40)
MAX_DIMENSION = 1800
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 150


def _encode_jpeg(image, quality):
    image = ImageOps.exif_transpose(image)
    if image.mode != 'RGB':
        background = Image.new('RGB', image.size, 'white')
        if 'A' in image.getbands():
            background.paste(image, mask=image.getchannel('A'))
        else:
            background.paste(image.convert('RGB'))
        image = background
    out = BytesIO()
    image.save(out, format='JPEG', quality=quality, optimize=True, progressive=True)
    return out.getvalue()


def _prepare(data, content_type='image/jpeg'):
    """Normalize a source to a Telegram-safe JPEG no larger than 1,000,000 B."""
    if len(data) <= MAX_TELEGRAM_IMAGE_BYTES and content_type == 'image/jpeg':
        return data, 'image/jpeg', False
    with Image.open(BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image)
        if max(image.size) > MAX_DIMENSION:
            scale = MAX_DIMENSION / max(image.size)
            image = image.resize(
                (max(MIN_IMAGE_WIDTH, int(image.width * scale)),
                 max(MIN_IMAGE_HEIGHT, int(image.height * scale))),
                Image.Resampling.LANCZOS,
            )
        for quality in JPEG_QUALITIES:
            encoded = _encode_jpeg(image, quality)
            if len(encoded) <= MAX_TELEGRAM_IMAGE_BYTES:
                return encoded, 'image/jpeg', True
        current = image
        while max(current.size) > 800:
            scale = 0.8
            current = current.resize(
                (max(MIN_IMAGE_WIDTH, int(current.width * scale)),
                 max(MIN_IMAGE_HEIGHT, int(current.height * scale))),
                Image.Resampling.LANCZOS,
            )
            for quality in JPEG_QUALITIES:
                encoded = _encode_jpeg(current, quality)
                if len(encoded) <= MAX_TELEGRAM_IMAGE_BYTES:
                    return encoded, 'image/jpeg', True
    raise ValueError('IMAGE_OPTIMIZATION_FAILED_1MB')


def fetch_image(article_url):
    image = hardening.fetch_image(article_url)
    source_bytes = len(image.get('data', b''))
    data, content_type, optimized = _prepare(image['data'], image.get('content_type', 'image/jpeg'))
    if len(data) > MAX_TELEGRAM_IMAGE_BYTES:
        raise ValueError('IMAGE_OVER_1MB_AFTER_OPTIMIZATION')
    image = dict(image)
    image['data'] = data
    image['content_type'] = content_type
    dims = hardening.pipeline._dimensions(data, content_type)
    if not dims or dims[0] < MIN_IMAGE_WIDTH or dims[1] < MIN_IMAGE_HEIGHT:
        raise ValueError('IMAGE_DIMENSIONS_INVALID_AFTER_OPTIMIZATION')
    image['width'], image['height'] = dims
    image['optimized'] = optimized
    image['source_payload_bytes'] = source_bytes
    image['payload_bytes'] = len(data)
    print('IMAGE_PAYLOAD_BYTES', len(data), 'source_bytes', source_bytes, 'optimized', optimized)
    return image
