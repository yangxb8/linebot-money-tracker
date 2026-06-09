import unittest
from io import BytesIO

from PIL import Image

from services.receipt_image_preprocess import (
    JPEG_QUALITY,
    MAX_LONG_EDGE,
    _detect_receipt_bbox,
    preprocess_receipt_image,
)


def _encode_png(img: Image.Image) -> bytes:
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def _make_receipt_on_dark_table() -> Image.Image:
    img = Image.new('RGB', (600, 800), (50, 50, 50))
    for x in range(160, 440):
        for y in range(120, 720):
            img.putpixel((x, y), (235, 235, 235))
    for x in range(180, 420):
        img.putpixel((x, 200), (20, 20, 20))
    return img


class TestReceiptImagePreprocess(unittest.TestCase):
    def test_detects_clear_receipt_bbox(self):
        img = _make_receipt_on_dark_table()
        bbox = _detect_receipt_bbox(img)
        self.assertIsNotNone(bbox)
        left, top, right, bottom = bbox
        self.assertLess(left, 200)
        self.assertGreater(right, 400)
        self.assertLess(top, 200)
        self.assertGreater(bottom, 600)

    def test_skips_crop_when_no_clear_document(self):
        img = Image.new('RGB', (400, 400), (128, 128, 128))
        self.assertIsNone(_detect_receipt_bbox(img))

    def test_preprocess_outputs_jpeg_grayscale(self):
        img = _make_receipt_on_dark_table()
        output, mime = preprocess_receipt_image(_encode_png(img))
        self.assertEqual(mime, 'image/jpeg')
        self.assertTrue(output.startswith(b'\xff\xd8'))
        with Image.open(BytesIO(output)) as processed:
            self.assertEqual(processed.mode, 'L')
            self.assertLessEqual(max(processed.size), MAX_LONG_EDGE)

    def test_preprocess_resizes_large_images(self):
        img = Image.new('RGB', (4000, 3000), (220, 220, 220))
        output, _ = preprocess_receipt_image(_encode_png(img))
        with Image.open(BytesIO(output)) as processed:
            self.assertEqual(max(processed.size), MAX_LONG_EDGE)

    def test_preprocess_empty_bytes_passthrough(self):
        output, mime = preprocess_receipt_image(b'')
        self.assertEqual(output, b'')
        self.assertEqual(mime, 'image/jpeg')


if __name__ == '__main__':
    unittest.main()
