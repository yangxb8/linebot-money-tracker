import unittest
from unittest.mock import MagicMock, patch

from services.ocr import extract_text_from_image_bytes, _guess_mime_type, _tesseract_lang


class TestOcr(unittest.TestCase):
    def test_guess_mime_type_detects_jpeg_and_png(self):
        self.assertEqual(_guess_mime_type(b'\xff\xd8\xff\x00'), 'image/jpeg')
        self.assertEqual(_guess_mime_type(b'\x89PNG\r\n\x1a\n'), 'image/png')

    @patch('services.ocr._ocr_with_pytesseract')
    def test_auto_prefers_pytesseract_first(self, pytesseract_mock):
        pytesseract_mock.return_value = ['Lunch 120 THB']
        lines = extract_text_from_image_bytes(b'fake-image', prefer='auto')
        self.assertEqual(lines, ['Lunch 120 THB'])
        pytesseract_mock.assert_called_once()

    @patch('services.ocr._ocr_with_document_ai')
    @patch('services.ocr._ocr_with_pytesseract', side_effect=RuntimeError('no local OCR'))
    def test_auto_falls_back_to_document_ai(self, _pytesseract_mock, document_ai_mock):
        document_ai_mock.return_value = ['TOTAL 45.00 USD']
        lines = extract_text_from_image_bytes(b'fake-image', prefer='auto')
        self.assertEqual(lines, ['TOTAL 45.00 USD'])

    @patch('services.ocr._ocr_with_document_ai', side_effect=RuntimeError('Document AI requires DOCUMENT_AI_PROJECT_ID'))
    @patch('services.ocr._ocr_with_pytesseract', side_effect=RuntimeError('no local OCR'))
    def test_auto_returns_empty_when_all_backends_fail(self, _pytesseract_mock, _document_ai_mock):
        lines = extract_text_from_image_bytes(b'fake-image', prefer='auto')
        self.assertEqual(lines, [])

    @patch.dict('os.environ', {'TESSERACT_LANG': 'jpn+eng'})
    @patch('services.ocr.pytesseract')
    @patch('services.ocr.Image')
    def test_pytesseract_uses_japanese_language_pack(self, image_module, pytesseract_module):
        image_module.open.return_value.convert.return_value = MagicMock()
        pytesseract_module.image_to_string.return_value = '合計 600円'

        from services.ocr import _ocr_with_pytesseract

        lines = _ocr_with_pytesseract(b'fake-image')
        self.assertEqual(lines, ['合計 600円'])
        pytesseract_module.image_to_string.assert_called_once()
        _, kwargs = pytesseract_module.image_to_string.call_args
        self.assertEqual(kwargs.get('lang'), 'jpn+eng')
        self.assertEqual(_tesseract_lang(), 'jpn+eng')


if __name__ == '__main__':
    unittest.main()
