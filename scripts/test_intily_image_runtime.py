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

    def test_prepare_enforces_strict_one_megabyte_cap(self):
        source = self._large_png()
        self.assertGreater(len(source), runtime.MAX_TELEGRAM_IMAGE_BYTES)
        data, content_type, optimized = runtime._prepare(source)
        self.assertTrue(optimized)
        self.assertEqual(content_type, 'image/jpeg')
        self.assertLessEqual(len(data), runtime.MAX_TELEGRAM_IMAGE_BYTES)
        with Image.open(BytesIO(data)) as image:
            self.assertGreaterEqual(image.width, runtime.MIN_IMAGE_WIDTH)
            self.assertGreaterEqual(image.height, runtime.MIN_IMAGE_HEIGHT)

    def test_small_jpeg_is_not_reencoded(self):
        image = Image.new('RGB', (800, 600), 'white')
        out = BytesIO()
        image.save(out, format='JPEG', quality=80)
        source = out.getvalue()
        data, content_type, optimized = runtime._prepare(source)
        self.assertEqual(data, source)
        self.assertEqual(content_type, 'image/jpeg')
        self.assertFalse(optimized)

    def test_fetch_uses_bounded_source_and_returns_one_megabyte_payload(self):
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
            result = runtime.fetch_image('https://publisher.example/story')
        self.assertLessEqual(result['payload_bytes'], runtime.MAX_TELEGRAM_IMAGE_BYTES)
        self.assertEqual(result['content_type'], 'image/jpeg')
        self.assertTrue(result['optimized'])
        self.assertEqual(result['source_payload_bytes'], len(source))


if __name__ == '__main__':
    unittest.main()
