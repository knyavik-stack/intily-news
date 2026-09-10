import unittest
from unittest.mock import patch

import intily_image_hardening as hardening


class ImageHardeningTests(unittest.TestCase):
    def test_nested_html_image_candidate_is_followed(self):
        html = b'<html><head><meta property="og:image" content="https://cdn.example/photo.jpg"></head></html>'
        image = b'fake-jpeg'
        responses = [
            (html, 'text/html', 'https://cdn.example/wrapper'),
            (image, 'image/jpeg', 'https://cdn.example/photo.jpg'),
        ]
        with patch.object(hardening.pipeline, 'extract_image_candidates', return_value=[(1, 'html_img', 'https://cdn.example/wrapper')],), \
             patch.object(hardening.pipeline, '_request', side_effect=responses), \
             patch.object(hardening.pipeline, '_dimensions', return_value=(1200, 800)):
            result = hardening.fetch_image('https://publisher.example/story')
        self.assertEqual(result['url'], 'https://cdn.example/photo.jpg')
        self.assertEqual(result['method'], 'nested_og_image')

    def test_google_nested_image_is_rejected(self):
        html = b'<meta property="og:image" content="https://googleusercontent.com/x.jpg">'
        with patch.object(hardening.pipeline, 'extract_image_candidates', return_value=[(1, 'html_img', 'https://cdn.example/wrapper')]), \
             patch.object(hardening.pipeline, '_request', return_value=(html, 'text/html', 'https://cdn.example/wrapper')):
            with self.assertRaisesRegex(ValueError, 'GOOGLE_IMAGE_FORBIDDEN'):
                hardening.fetch_image('https://publisher.example/story')


if __name__ == '__main__':
    unittest.main()
