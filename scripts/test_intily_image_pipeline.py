import unittest
from unittest.mock import patch

import intily_image_pipeline as media


class ImagePipelineTests(unittest.TestCase):
    def test_meta_attribute_order_is_supported(self):
        html = '''
        <html><head>
          <meta content="https://cdn.example/image.jpg" property="og:image">
          <meta name="twitter:image" content="https://cdn.example/twitter.jpg">
        </head></html>
        '''
        candidates, _ = media._meta_image_candidates(html)
        self.assertIn(('og_image', 'https://cdn.example/image.jpg'), candidates)
        self.assertIn(('twitter_image', 'https://cdn.example/twitter.jpg'), candidates)

    def test_jsonld_and_lazy_html_images_are_candidates(self):
        html = '''
        <script type="application/ld+json">
        {"@type":"NewsArticle","image":{"url":"https://cdn.example/jsonld.jpg"}}
        </script>
        <img data-src="/assets/article.jpg" srcset="/assets/small.jpg 400w, /assets/large.jpg 1600w">
        '''
        candidates, _ = media._meta_image_candidates(html)
        methods = [method for method, _ in candidates]
        values = [value for _, value in candidates]
        self.assertIn(('jsonld_image', 'https://cdn.example/jsonld.jpg'), candidates)
        self.assertIn('html_img', methods)
        self.assertIn('/assets/large.jpg', values)

    def test_google_news_canonical_fallback_resolves_publisher(self):
        wrapper = '''
        <html><head>
          <link rel="canonical" href="https://publisher.example/story/1">
        </head></html>
        '''
        publisher = '<html><head><meta property="og:image" content="/img.jpg"></head></html>'
        responses = [
            (wrapper.encode(), 'text/html', 'https://news.google.com/rss/articles/abc'),
            (publisher.encode(), 'text/html', 'https://publisher.example/story/1'),
        ]
        with patch.object(media, '_request', side_effect=responses):
            final_url, data, _ = media.resolve_article_url('https://news.google.com/rss/articles/abc')
        self.assertEqual(final_url, 'https://publisher.example/story/1')
        self.assertIn(b'og:image', data)

    def test_invalid_first_candidate_does_not_force_text_fallback(self):
        html = '<meta property="og:image" content="/broken.jpg"><meta property="twitter:image" content="/good.jpg">'
        responses = [
            (html.encode(), 'text/html', 'https://publisher.example/story'),
            (b'not-an-image', 'text/html', 'https://publisher.example/broken.jpg'),
            (self._jpeg(640, 480), 'image/jpeg', 'https://publisher.example/good.jpg'),
        ]
        with patch.object(media, '_request', side_effect=responses):
            image = media.fetch_image('https://publisher.example/story')
        self.assertEqual(image['url'], 'https://publisher.example/good.jpg')
        self.assertEqual(image['method'], 'twitter_image')
        self.assertEqual((image['width'], image['height']), (640, 480))

    @staticmethod
    def _jpeg(width, height):
        # Minimal JPEG containing a SOF marker sufficient for _dimensions().
        return (b'\xff\xd8\xff\xc0\x00\x11\x08' + height.to_bytes(2, 'big') +
                width.to_bytes(2, 'big') + b'\x01\x01\x11\x00' + b'\xff\xd9')


if __name__ == '__main__':
    unittest.main()
