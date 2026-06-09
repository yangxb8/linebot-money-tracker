"""Prepare receipt photos for Gemini vision: rotate, optional crop, grayscale, resize, JPEG."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

from services.log_utils import describe_bytes

logger = logging.getLogger(__name__)

MAX_LONG_EDGE = 2048
JPEG_QUALITY = 85
CONTRAST_FACTOR = 1.5
_CROP_DETECT_MAX_EDGE = 1200
_MIN_CROP_AREA_RATIO = 0.25
_MAX_CROP_AREA_RATIO = 0.92
_MIN_CROP_SHORT_SIDE = 80
_MIN_ASPECT = 0.15
_MAX_ASPECT = 1.2
_CROP_PADDING_RATIO = 0.02


def _guess_mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    return 'image/jpeg'


def _add_padding(
    bbox: Tuple[int, int, int, int],
    width: int,
    height: int,
    *,
    pad_ratio: float,
) -> Tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    pad_x = int(width * pad_ratio)
    pad_y = int(height * pad_ratio)
    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(width, right + pad_x),
        min(height, bottom + pad_y),
    )


def _bbox_is_clear_receipt(
    bbox: Tuple[int, int, int, int],
    width: int,
    height: int,
) -> bool:
    left, top, right, bottom = bbox
    box_w = right - left
    box_h = bottom - top
    if box_w < _MIN_CROP_SHORT_SIDE or box_h < _MIN_CROP_SHORT_SIDE:
        return False

    area_ratio = (box_w * box_h) / (width * height)
    if area_ratio < _MIN_CROP_AREA_RATIO or area_ratio > _MAX_CROP_AREA_RATIO:
        return False

    aspect = box_w / box_h
    if aspect < _MIN_ASPECT or aspect > _MAX_ASPECT:
        return False

    margin_w = width * 0.02
    margin_h = height * 0.02
    touches_all_edges = (
        left <= margin_w
        and top <= margin_h
        and right >= width - margin_w
        and bottom >= height - margin_h
    )
    if touches_all_edges and area_ratio > 0.88:
        return False

    return True


def _scale_bbox(
    bbox: Tuple[int, int, int, int],
    from_size: Tuple[int, int],
    to_size: Tuple[int, int],
) -> Tuple[int, int, int, int]:
    from_w, from_h = from_size
    to_w, to_h = to_size
    if from_w == 0 or from_h == 0:
        return bbox
    sx = to_w / from_w
    sy = to_h / from_h
    left, top, right, bottom = bbox
    return (
        int(left * sx),
        int(top * sy),
        int(right * sx),
        int(bottom * sy),
    )


def _detect_receipt_bbox(img: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    """Return a crop box when a receipt-like region is clearly separable from the background."""
    width, height = img.size
    if width < 120 or height < 120:
        return None

    detect = img
    scale_back = (width, height)
    long_edge = max(width, height)
    if long_edge > _CROP_DETECT_MAX_EDGE:
        ratio = _CROP_DETECT_MAX_EDGE / long_edge
        detect = img.resize(
            (max(1, int(width * ratio)), max(1, int(height * ratio))),
            Image.Resampling.LANCZOS,
        )

    gray = ImageOps.exif_transpose(detect).convert('L')
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.filter(ImageFilter.GaussianBlur(radius=2))

    mean = ImageStat.Stat(gray).mean[0]
    bright_threshold = max(int(mean - 8), 150)
    bright_mask = gray.point(lambda p: 255 if p >= bright_threshold else 0, mode='1')
    content_mask = gray.point(lambda p: 255 if p < 235 else 0, mode='1')

    candidates = [bbox for bbox in (bright_mask.getbbox(), content_mask.getbbox()) if bbox]
    if not candidates:
        return None

    detect_w, detect_h = gray.size
    for bbox in sorted(
        candidates,
        key=lambda box: (box[2] - box[0]) * (box[3] - box[1]),
        reverse=True,
    ):
        padded = _add_padding(bbox, detect_w, detect_h, pad_ratio=_CROP_PADDING_RATIO)
        if not _bbox_is_clear_receipt(padded, detect_w, detect_h):
            continue
        if detect.size != (width, height):
            padded = _scale_bbox(padded, detect.size, scale_back)
        padded = _add_padding(padded, width, height, pad_ratio=0)
        left, top, right, bottom = padded
        if right - left < _MIN_CROP_SHORT_SIDE or bottom - top < _MIN_CROP_SHORT_SIDE:
            continue
        logger.info(
            'Receipt preprocess: detected crop bbox=%s on %dx%d image',
            padded,
            width,
            height,
        )
        return padded

    return None


def _maybe_crop(img: Image.Image) -> Image.Image:
    bbox = _detect_receipt_bbox(img)
    if bbox is None:
        return img
    return img.crop(bbox)


def _resize_long_edge(img: Image.Image, max_edge: int) -> Image.Image:
    width, height = img.size
    long_edge = max(width, height)
    if long_edge <= max_edge:
        return img
    ratio = max_edge / long_edge
    new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def _to_grayscale_contrast(img: Image.Image) -> Image.Image:
    gray = img.convert('L')
    return ImageEnhance.Contrast(gray).enhance(CONTRAST_FACTOR)


def _encode_jpeg(img: Image.Image) -> bytes:
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue()


def preprocess_receipt_image(image_bytes: bytes) -> Tuple[bytes, str]:
    """Always-on pipeline: EXIF rotate → optional crop → grayscale/contrast → resize → JPEG."""
    if not image_bytes:
        return image_bytes, 'image/jpeg'

    original_len = len(image_bytes)
    try:
        with Image.open(BytesIO(image_bytes)) as opened:
            img = ImageOps.exif_transpose(opened)
            img = img.convert('RGB')

            cropped = _maybe_crop(img)
            if cropped is not img:
                logger.info(
                    'Receipt preprocess: cropped %dx%d -> %dx%d',
                    img.width,
                    img.height,
                    cropped.width,
                    cropped.height,
                )

            gray = _to_grayscale_contrast(cropped)
            resized = _resize_long_edge(gray, MAX_LONG_EDGE)
            output = _encode_jpeg(resized)

        logger.info(
            'Receipt preprocess: %s -> %s (%dx%d grayscale JPEG q=%d)',
            describe_bytes(image_bytes),
            describe_bytes(output),
            resized.width,
            resized.height,
            JPEG_QUALITY,
        )
        if len(output) >= original_len:
            logger.debug(
                'Receipt preprocess: output not smaller than input (%d vs %d bytes)',
                len(output),
                original_len,
            )
        return output, 'image/jpeg'
    except Exception:
        logger.warning(
            'Receipt preprocess failed for %s; using original bytes',
            describe_bytes(image_bytes),
            exc_info=True,
        )
        return image_bytes, _guess_mime_type(image_bytes)
