import hashlib
import struct
import unittest
import zlib
from unittest.mock import patch

import intily_image_runtime as runtime


def _png(width, height, pixel=b'\xff\xff\xff'):
    """Build a deterministic RGB PNG fixture without an external imaging library."""
    row = pixel * width
    raw = b''.join(b'\x00' + row for _ in range(height))
    compressed = zlib.compress(raw, 9)

    def chunk(kind, data):
        return (
            struct.pack('>I', len(data))
            + kind
            + data
            + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', header)
        + chunk(b'IDAT', compressed)
        + chunk(b'IEND', b'')
    )


class ImageRuntimeTests(unittest.TestCase):
    def _large_png(self):
        # Deterministic high-entropy RGB rows keep the fixture above 1 MB.
        rows = []
        state = b'intily-media-fixture'
        for _y in range(1200):
            row = bytearray()
            while len(row) < 1800 * 3:
                state = hashlib.sha256(state).digest()
                row.extend(state)
            rows.append(b'\x00' + bytes(row[:1800 * 3]))
        raw = b''.join(rows)
        compressed = zlib.compress(raw, 9)

        def chunk(kind, data):
            return (
                struct.pack('>I', len(data))
                + kind
                + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
            )

        header = struct.pack('>IIBBBBB', 1800, 1200, 8, 2, 0, 0, 0)
        return (
            b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', header)
            + chunk(b'IDAT', compressed)
            + chunk(b'IEND', b'')
        )

    def test_prepare_rejects_oversized_image_without_optimization(self):
        source = self._large_png()
        self.assertGreater(len(source), runtime.MAX_TELEGRAM_IMAGE_BYTES)
        with self.assertRaisesRegex(ValueError, '^IMAGE_TOO_LARGE$'):
            runtime._prepare(source, 'image/png')

    def test_small_png_is_accepted_unchanged(self):
        source = _png(800, 600)
        self.assertLess(len(source), runtime.MAX_TELEGRAM_IMAGE_BYTES)
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
