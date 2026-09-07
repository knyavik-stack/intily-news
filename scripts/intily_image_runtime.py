"""Production image runtime: publisher-first fetch plus <=1 MiB Telegram payload.

The source image may be larger than the Telegram payload budget. We fetch only
up to a bounded source size, then normalize/compress it to a strict 1 MiB cap
before sendPhoto. Google-hosted images remain forbidden by the hardening layer.
"""

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
    if image.mode not in ('RGB', 'L'):
        background = Image.new('RGB', image.size, 'white')
        if 'A' in image.getbands():
            background.paste(image, mask=image.getchannel('A'))
        else:
            background.paste(image.convert('RGB'))
        image = background
    else:
        image = image.convert('RGB')
    out = BytesIO()
    image.save(out, format='JPEG', quality=quality, optimize=True, progressive=True)
    return out.getvalue()


def _prepare(data):
    if len(data) <= MAX_TELEGRAM_IMAGE_BYTES:
        return data, 'image/jpeg' if data[:2] == b'\xff\xd8' else None

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
                return encoded, 'image/jpeg'

        # Quality alone can be insufficient for very detailed images. Reduce
        # dimensions progressively, then retry the same bounded quality ladder.
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
                    return encoded, 'image/jpeg'

    raise ValueError('IMAGE_OPTIMIZATION_FAILED_1MB')


def fetch_image(article_url):
    """Fetch a publisher image and guarantee the returned payload is <=1 MiB."""
    original_limit = hardening.pipeline.MAX_IMAGE_BYTES
    hardening.pipeline.MAX_IMAGE_BYTES = MAX_SOURCE_IMAGE_BYTES
    try:
        image = hardening.fetch_image(article_url)
    finally:
        hardening.pipeline.MAX_IMAGE_BYTES = original_limit

    data, content_type = _prepare(image['data'])
    if len(data) > MAX_TELEGRAM_IMAGE_BYTES:
        raise ValueError('IMAGE_OVER_1MB_AFTER_OPTIMIZATION')

    image = dict(image)
    image['data'] = data
    image['content_type'] = content_type or image['content_type']
    dims = hardening.pipeline._dimensions(data, image['content_type'])
    if not dims or dims[0] < MIN_IMAGE_WIDTH or dims[1] < MIN_IMAGE_HEIGHT:
        raise ValueError('IMAGE_DIMENSIONS_INVALID_AFTER_OPTIMIZATION')
    image['width'], image['height'] = dims
    image['optimized'] = len(image.get('data', b'')) < len(image.get('_source_data', image['data']))
    image['payload_bytes'] = len(data)
    return image
