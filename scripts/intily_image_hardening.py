"""Runtime hardening for Intily publisher-image retrieval.

Keeps the deterministic extractor/validator, adds publisher Referer retry,
forbids Google-hosted images, and skips source images over the product's strict
1,000,000-byte delivery cap so another valid publisher candidate can be tried.
"""

import urllib.parse

import intily_image_pipeline as pipeline

GOOGLE_IMAGE_HOSTS = {
    'news.google.com', 'www.news.google.com',
    'googleusercontent.com', 'www.googleusercontent.com',
}

MAX_TELEGRAM_IMAGE_BYTES = 1_000_000
MAX_IMAGE_BYTES = pipeline.MAX_SOURCE_IMAGE_BYTES

BROWSER_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/151.0.0.0 Safari/537.36'
)


def _host(url):
    try:
        return urllib.parse.urlsplit(url).netloc.lower().split('@')[-1].split(':', 1)[0]
    except Exception:
        return ''


def fetch_image(article_url):
    ranked, source_url = pipeline.extract_image_candidates(article_url)
    errors = []
    for _rank, method, image_url in ranked:
        if _host(image_url) in GOOGLE_IMAGE_HOSTS or _host(image_url).endswith('.googleusercontent.com'):
            errors.append(f'{method}:GOOGLE_IMAGE_FORBIDDEN')
            continue

        attempts = [
            {
                'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
                'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': source_url,
            },
            {
                'User-Agent': 'Mozilla/5.0 (compatible; IntilyNews/1.0)',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            },
            {
                'User-Agent': BROWSER_USER_AGENT,
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': source_url,
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
            },
        ]
        for headers in attempts:
            try:
                data, content_type, final_url = pipeline._request(
                    image_url, headers, 15, MAX_IMAGE_BYTES
                )
                if _host(final_url) in GOOGLE_IMAGE_HOSTS or _host(final_url).endswith('.googleusercontent.com'):
                    raise ValueError('GOOGLE_IMAGE_FORBIDDEN')
                if content_type not in pipeline.IMAGE_TYPES:
                    raise ValueError('IMAGE_CONTENT_TYPE_INVALID')
                if len(data) > MAX_TELEGRAM_IMAGE_BYTES:
                    errors.append(f'{method}:IMAGE_TOO_LARGE:{len(data)}')
                    break
                dims = pipeline._dimensions(data, content_type)
                if not dims or dims[0] < pipeline.MIN_IMAGE_WIDTH or dims[1] < pipeline.MIN_IMAGE_HEIGHT:
                    raise ValueError('IMAGE_DIMENSIONS_INVALID')
                return {
                    'data': data,
                    'content_type': content_type,
                    'url': final_url,
                    'method': method,
                    'source_url': source_url,
                    'width': dims[0],
                    'height': dims[1],
                }
            except Exception as exc:
                errors.append(f'{method}:{str(exc)[:100]}')

    raise ValueError('IMAGE_CANDIDATES_FAILED: ' + ' | '.join(errors[:8]))