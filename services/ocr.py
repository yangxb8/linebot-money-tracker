from typing import List, Optional
from io import BytesIO
import logging
import os

logger = logging.getLogger(__name__)

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None


def _guess_mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if image_bytes.startswith(b'GIF87a') or image_bytes.startswith(b'GIF89a'):
        return 'image/gif'
    if image_bytes.startswith(b'RIFF') and image_bytes[8:12] == b'WEBP':
        return 'image/webp'
    return 'image/jpeg'


def _tesseract_lang() -> str:
    # jpn+eng handles mixed Japanese/English labels common on receipts.
    return os.getenv('TESSERACT_LANG', 'jpn+eng')


def _ocr_with_pytesseract(image_bytes: bytes) -> List[str]:
    if Image is None or pytesseract is None:
        raise RuntimeError('pytesseract/Pillow not installed')

    img = Image.open(BytesIO(image_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')

    text = pytesseract.image_to_string(img, lang=_tesseract_lang())
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines


def _ocr_with_document_ai(image_bytes: bytes) -> List[str]:
    try:
        from google.cloud import documentai_v1 as documentai
    except Exception as e:
        raise RuntimeError('google-cloud-documentai not installed') from e

    project_id = os.getenv('DOCUMENT_AI_PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT')
    location = os.getenv('DOCUMENT_AI_LOCATION', 'asia-southeast1')
    processor_id = os.getenv('DOCUMENT_AI_PROCESSOR_ID')

    if not project_id or not processor_id:
        raise RuntimeError(
            'Document AI requires DOCUMENT_AI_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) '
            'and DOCUMENT_AI_PROCESSOR_ID'
        )

    client = documentai.DocumentProcessorServiceClient()
    name = client.processor_path(project_id, location, processor_id)
    raw_document = documentai.RawDocument(
        content=image_bytes,
        mime_type=_guess_mime_type(image_bytes),
    )
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)
    text = result.document.text or ''
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines


def extract_text_from_image_bytes(image_bytes: bytes, prefer: Optional[str] = 'auto') -> List[str]:
    """Extract text lines from image bytes.

    Parameters:
      - image_bytes: raw image bytes
      - prefer: 'pytesseract', 'documentai', or 'auto' (try pytesseract then Document AI)

    Returns list of text lines (may be empty).
    Raises RuntimeError if no OCR backend is available.
    """
    backends = []
    if prefer == 'pytesseract':
        backends = ['pytesseract']
    elif prefer in ('documentai', 'vision'):
        backends = ['documentai']
    else:
        backends = ['pytesseract', 'documentai']

    last_exc = None
    for b in backends:
        try:
            if b == 'pytesseract':
                return _ocr_with_pytesseract(image_bytes)
            if b == 'documentai':
                return _ocr_with_document_ai(image_bytes)
        except Exception as e:
            logger.debug('OCR backend %s failed: %s', b, e)
            last_exc = e

    raise RuntimeError('No OCR backend available or all backends failed') from last_exc
