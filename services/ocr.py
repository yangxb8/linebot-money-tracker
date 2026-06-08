from typing import List, Optional
from io import BytesIO
import base64
import json
import logging
import os
import urllib.error
import urllib.request

from services.log_utils import describe_bytes, truncate

logger = logging.getLogger(__name__)

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

_VISION_ANNOTATE_URL = 'https://vision.googleapis.com/v1/images:annotate'


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
    return os.getenv('TESSERACT_LANG', 'jpn+eng')


def _ocr_with_pytesseract(image_bytes: bytes) -> List[str]:
    if Image is None or pytesseract is None:
        raise RuntimeError('pytesseract/Pillow not installed')

    lang = _tesseract_lang()
    logger.info('OCR pytesseract: starting lang=%s image=%s', lang, describe_bytes(image_bytes))

    img = Image.open(BytesIO(image_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')

    text = pytesseract.image_to_string(img, lang=lang)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    logger.info('OCR pytesseract: extracted %d line(s)', len(lines))
    if lines:
        logger.debug('OCR pytesseract sample: %s', truncate('\n'.join(lines[:5]), 500))
    else:
        logger.warning('OCR pytesseract: no text lines extracted')
    return lines


def _ocr_with_cloud_vision(image_bytes: bytes) -> List[str]:
    api_key = os.getenv('GOOGLE_VISION_API_KEY')
    if not api_key:
        raise RuntimeError('GOOGLE_VISION_API_KEY environment variable is not set')

    logger.info(
        'OCR Cloud Vision: DOCUMENT_TEXT_DETECTION image=%s',
        describe_bytes(image_bytes),
    )

    payload = {
        'requests': [
            {
                'image': {'content': base64.b64encode(image_bytes).decode('ascii')},
                'features': [{'type': 'DOCUMENT_TEXT_DETECTION'}],
            }
        ]
    }
    url = f'{_VISION_ANNOTATE_URL}?key={api_key}'
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Cloud Vision API HTTP {exc.code}: {error_body[:500]}') from exc

    responses = body.get('responses') or []
    if not responses:
        logger.warning('OCR Cloud Vision: empty responses')
        return []

    first = responses[0]
    if first.get('error'):
        message = first['error'].get('message', 'unknown error')
        raise RuntimeError(f'Cloud Vision API error: {message}')

    full_text = ''
    full_annotation = first.get('fullTextAnnotation') or {}
    if isinstance(full_annotation, dict):
        full_text = full_text or (full_annotation.get('text') or '')

    if not full_text:
        annotations = first.get('textAnnotations') or []
        if annotations and isinstance(annotations[0], dict):
            full_text = annotations[0].get('description') or ''

    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    logger.info('OCR Cloud Vision: extracted %d line(s)', len(lines))
    if lines:
        logger.debug('OCR Cloud Vision sample: %s', truncate('\n'.join(lines[:5]), 500))
    else:
        logger.warning('OCR Cloud Vision: no text lines extracted')
    return lines


def extract_text_from_image_bytes(image_bytes: bytes, prefer: Optional[str] = 'auto') -> List[str]:
    """Extract text lines from image bytes.

    Backends (auto order): pytesseract → Cloud Vision DOCUMENT_TEXT_DETECTION.

    Cloud Vision requires GOOGLE_VISION_API_KEY.
    """
    backends: List[str] = []
    if prefer == 'pytesseract':
        backends = ['pytesseract']
    elif prefer in ('vision', 'cloud_vision', 'documentai'):
        backends = ['vision']
    else:
        backends = ['pytesseract', 'vision']

    logger.info(
        'OCR extract: image=%s prefer=%s backends=%s',
        describe_bytes(image_bytes),
        prefer,
        backends,
    )

    last_exc = None
    for backend in backends:
        try:
            if backend == 'pytesseract':
                return _ocr_with_pytesseract(image_bytes)
            if backend == 'vision':
                return _ocr_with_cloud_vision(image_bytes)
        except Exception as exc:
            logger.warning('OCR backend %s failed: %s', backend, exc)
            last_exc = exc

    logger.warning(
        'OCR extract: all backends failed (%s); returning empty text. last_error=%s',
        ', '.join(backends),
        last_exc,
    )
    return []
