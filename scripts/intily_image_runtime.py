"""Production image runtime with a strict <=1,000,000-byte acceptance cap."""

import intily_image_hardening as hardening

MAX_TELEGRAM_IMAGE_BYTES = 1_000_000
MAX_SOURCE_IMAGE_BYTES = 8 * 1024 * 1024
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 150


def _prepare(data, content_type='image/jpeg'):
    """Accept an image only when the already-downloaded payload is <= 1 MB.

    Oversized images are intentionally rejected. Intily does not resize or
    recompress source media to make an oversized image fit the product cap.
    """
    if len(data) > MAX_TELEGRAM_IMAGE_BYTES:
        raise ValueError('IMAGE_TOO_LARGE')
    return data, content_type, False


def fetch_image(article_url):
    image = hardening.fetch_image(article_url)
    source_bytes = len(image.get('data', b''))
    if source_bytes > MAX_TELEGRAM_IMAGE_BYTES:
        raise ValueError('IMAGE_TOO_LARGE')
    data, content_type, optimized = _prepare(
        image['data'], image.get('content_type', 'image/jpeg')
    )
    image = dict(image)
    image['data'] = data
    image['content_type'] = content_type
    dims = hardening.pipeline._dimensions(data, content_type)
    if not dims or dims[0] < MIN_IMAGE_WIDTH or dims[1] < MIN_IMAGE_HEIGHT:
        raise ValueError('IMAGE_DIMENSIONS_INVALID')
    image['width'], image['height'] = dims
    image['optimized'] = optimized
    image['source_payload_bytes'] = source_bytes
    image['payload_bytes'] = len(data)
    print('IMAGE_PAYLOAD_BYTES', len(data), 'source_bytes', source_bytes, 'optimized', optimized)
    return image
