import os
import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image

import intily_image_runtime as runtime


class ImageRuntimeTests(unittest.TestCase):
    def _large_png(self):
        image = Image.frombytes('RGB', (1800, 1200), os.urandom(1800 * 1200 * 3))
        out = BytesIO()
        image.save(out, format='PNG')
        return out.getvalue()

    def test_prepare_rejects_oversized_image_without_optimization(self):
        source = self._large_png()
        self.assertGreater(len(source), runtime.MAX_TELEGRAM_IMAGE_BYTES)
        with self.assertRaisesRegex(ValueError, '^IMAGE_TOO_LARGE$'):
            runtime._prepare(source, 'image/png')

    def test_small_jpeg_is_accepted_unchanged(self):
        image = Image.new('RGB', (800, 600), 'white')
        out = BytesIO()
        image.save(out, format='JPEG', quality=80)
        source = out.getvalue()
        data, content_type, optimized = runtime._prepare(source)
        self.assertEqual(data, source)
        self.assertEqual(content_type, 'image/jpeg')
        self.assertFalse(optimized)

    def test_fetch_rejects_oversized_source(self):
        source = self._large_png()
        fake = {
            'data': source,
            'content_type': 'image/png',
            'url': 'https://publisher.example/image.png',
            'method': 'og_image',
            'source_url': 'https://publisher.example/story',
            'width': 1800,
            'height': 1200,
        }
        with patch.object(runtime.hardening, 'fetch_image', return_value=fake):
            with self.assertRaisesRegex(ValueError, '^IMAGE_TOO_LARGE$'):
                runtime.fetch_image('https://publisher.example/story')


if __name__ == '__main__':
    unittest.main()
