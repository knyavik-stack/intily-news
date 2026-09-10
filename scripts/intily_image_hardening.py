"""Runtime hardening for Intily publisher-image retrieval.

Keeps the deterministic extractor/validator, adds publisher Referer retry,
forbids Google-hosted images, follows one level of HTML image indirection,
and bounds total media-fetch time so a blocked publisher cannot stall a post.
"""

import time
import urllib.parse

import intily_image_pipeline as pipeline

GOOGLE_IMAGE_HOSTS = {
    'news.google.com', 'www.news.google.com',
    'googleusercontent.com', 'www.googleusercontent.com',
}

MAX_TELEGRAM_IMAGE_BYTES = 1_000_000
MAX_IMAGE_BYTES = pipeline.MAX_SOURCE_IMAGE_BYTES
IMAGE_FETCH_TOTAL_BUDGET_SECONDS = 12.0
IMAGE_REQUEST_TIMEOUT_SECONDS = 6
MAX_NESTED_IMAGE_CANDIDATES = 8

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


def _forbidden_host(url):
    host = _host(url)
    return host in GOOGLE_IMAGE_HOSTS or host.endswith('.googleusercontent.com')


def _browser_attempts(source_url):
    return [
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


def _nested_candidates(data, content_type, base_url):
    if content_type not in {'text/html', 'application/xhtml+xml'}:
        return []
    try:
        parser_candidates, _parser = pipeline._meta_image_candidates(
            data.decode('utf-8', 'replace')
        )
    except Exception:
        return []
    priority = {
        'og_image': 0,
        'jsonld_image': 1,
        'image_src': 2,
        'twitter_image': 3,
        'html_img': 4,
        'html_source': 5,
        'css_image': 6,
    }
    ranked = []
    for method, value in parser_candidates:
        image_url = urllib.parse.urljoin(base_url, value)
        if not image_url.startswith(('http://', 'https://')) or _forbidden_host(image_url):
            continue
        ranked.append((priority.get(method, 9), 'nested_' + method, image_url))
    return sorted(ranked, key=lambda row: (row[0], row[1], row[2]))[:MAX_NESTED_IMAGE_CANDIDATES]


def fetch_image(article_url):
    ranked, source_url = pipeline.extract_image_candidates(article_url)
    pending = list(ranked)
    errors = []
    nested_seen = set()
    started_at = time.monotonic()

    while pending and time.monotonic() - started_at < IMAGE_FETCH_TOTAL_BUDGET_SECONDS:
        _rank, method, image_url = pending.pop(0)
        if _forbidden_host(image_url):
            errors.append(f'{method}:GOOGLE_IMAGE_FORBIDDEN')
            continue

        for headers in _browser_attempts(source_url):
            if time.monotonic() - started_at >= IMAGE_FETCH_TOTAL_BUDGET_SECONDS:
                break
            try:
                data, content_type, final_url = pipeline._request(
                    image_url, headers, IMAGE_REQUEST_TIMEOUT_SECONDS, MAX_IMAGE_BYTES
                )
                if _forbidden_host(final_url):
                    raise ValueError('GOOGLE_IMAGE_FORBIDDEN')
                if content_type in {'text/html', 'application/xhtml+xml'}:
                    for nested in _nested_candidates(data, content_type, final_url):
                        nested_url = nested[2]
                        if nested_url not in nested_seen:
                            nested_seen.add(nested_url)
                            pending.append(nested)
                    errors.append(f'{method}:HTML_IMAGE_INDIRECTION')
                    break
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

    elapsed = round(time.monotonic() - started_at, 2)
    raise ValueError(
        'IMAGE_CANDIDATES_FAILED: ' + ' | '.join(errors[:10])
        + f' | elapsed={elapsed}s'
    )
