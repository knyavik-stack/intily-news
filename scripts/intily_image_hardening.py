"""Runtime hardening for Intily publisher-image retrieval.

Keeps the existing deterministic extractor/validator but adds a publisher
Referer retry and an explicit ban on Google-hosted image URLs. This is kept in
a separate module so the core image pipeline remains easy to regression-test.
"""

import urllib.parse

import intily_image_pipeline as pipeline

GOOGLE_IMAGE_HOSTS = {
    'news.google.com', 'www.news.google.com',
    'googleusercontent.com', 'www.googleusercontent.com',
}

# Backward-compatible alias for the production runtime. This is a source-fetch
# limit only; the final Telegram payload is enforced separately at 1,000,000 B.
MAX_IMAGE_BYTES = pipeline.MAX_SOURCE_IMAGE_BYTES


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
