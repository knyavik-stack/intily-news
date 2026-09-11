import unittest
from unittest.mock import patch

# Production loads audience policy before media delivery; importing it first
# activates the no-truncation caption guard used in production.
import intily_audience_policy  # noqa: F401
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
        wrapper = '<html><head><link rel="canonical" href="https://publisher.example/story/1"></head></html>'
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
        html = '<meta property="og:image" content="/broken.jpg"><meta name="twitter:image" content="/good.jpg">'
        responses = [
            (html.encode(), 'text/html', 'https://publisher.example/story'),
            (b'not-an-image', 'text/html', 'https://publisher.example/broken.jpg'),
            (self._jpeg(640, 480), 'image/jpeg', 'https://publisher.example/good.jpg'),
        ]
        with patch.object(media, '_request', side_effect=responses):
            image = media.fetch_image('https://publisher.example/story')
        self.assertEqual(image['url'], 'https://publisher.example/good.jpg')
        self.assertEqual((image['width'], image['height']), (640, 480))

    def test_oversized_first_candidate_is_skipped_for_next_candidate(self):
        html = '<meta property="og:image" content="/large.jpg"><meta name="twitter:image" content="/good.jpg">'
        oversized = b'x' * (media.MAX_SOURCE_IMAGE_BYTES + 1)
        responses = [
            (html.encode(), 'text/html', 'https://publisher.example/story'),
            (oversized, 'image/jpeg', 'https://publisher.example/large.jpg'),
            (self._jpeg(640, 480), 'image/jpeg', 'https://publisher.example/good.jpg'),
        ]
        with patch.object(media, '_request', side_effect=responses):
            image = media.fetch_image('https://publisher.example/story')
        self.assertEqual(image['url'], 'https://publisher.example/good.jpg')

    def test_blockchain_news_expected_image_is_a_first_class_candidate(self):
        expected = 'https://blockchainstock.blob.core.windows.net/features/2242046FCF14090589D5A49FFC590D13A9AF6032D71ECDBD82C9F012CD661799.jpg'
        html = f'<meta property="og:image" content="{expected}">'
        candidates, _ = media._meta_image_candidates(html)
        self.assertEqual(candidates[0], ('og_image', expected))

    def test_photo_caption_preserves_supported_formatting(self):
        text = '<b>Заголовок &amp; тест</b> — <i>важно</i> <a href="https://example.com">источник</a>'
        caption = media._photo_caption(text)
        self.assertLessEqual(len(caption), 1024)
        self.assertIn('<b>Заголовок &amp; тест</b>', caption)
        self.assertIn('<i>важно</i>', caption)
        self.assertIn('<a href="https://example.com">источник</a>', caption)
        self.assertNotIn('<script', caption.lower())

    def test_long_photo_caption_is_rejected_instead_of_truncated(self):
        text = '<b>Заголовок</b> ' + ('длинный & текст ' * 200)
        with self.assertRaisesRegex(ValueError, 'PHOTO_CAPTION_LIMIT_TEXT_SPLIT'):
            media._photo_caption(text)

    def test_long_post_sends_photo_and_full_text_separately(self):
        text = '<b>Заголовок</b> ' + ('длинный текст ' * 200)
        image = {
            'data': self._jpeg(640, 480),
            'content_type': 'image/jpeg',
            'url': 'https://publisher.example/good.jpg',
            'method': 'og_image',
            'source_url': 'https://publisher.example/story',
            'width': 640,
            'height': 480,
        }
        with patch.object(media, 'fetch_image', return_value=image), \
             patch.object(media, 'send_photo', return_value={'ok': True, 'result': {'message_id': 123}}) as send_photo, \
             patch.object(media, 'MAX_TELEGRAM_CAPTION_BYTES', 1024), \
             patch.object(media, '_photo_caption', side_effect=ValueError('PHOTO_CAPTION_LIMIT_TEXT_SPLIT')):
            full_text = []
            telemetry = media.publish_with_optional_image(
                text, image['source_url'], 'token', '@intily', full_text.append
            )
        self.assertEqual(telemetry['status'], 'sent')
        self.assertEqual(telemetry['caption_mode'], 'photo_plus_full_text')
        self.assertEqual(full_text, [text])
        self.assertEqual(send_photo.call_count, 1)
        self.assertEqual(send_photo.call_args.args[2], '')

    def test_photo_caption_rejects_unsafe_href(self):
        caption = media._photo_caption('<a href="javascript:alert(1)">опасная ссылка</a>')
        self.assertNotIn('javascript:', caption.lower())
        self.assertIn('опасная ссылка', caption)

    @staticmethod
    def _jpeg(width, height):
        return (b'\xff\xd8\xff\xc0\x00\x11\x08' + height.to_bytes(2, 'big') +
                width.to_bytes(2, 'big') + b'\x01\x01\x11\x00' + b'\xff\xd9')


if __name__ == '__main__':
    unittest.main()
