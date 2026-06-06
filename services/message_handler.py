import logging
from typing import List, Dict, Any, Optional

from services.ai_assist import assist_parse_image, assist_parse_ocr
from services.categorize import classify_expense
from services.category_taxonomy import format_category_path, resolve_code
from services.expense_repository import build_insert_row, insert_expenses
from services.gemini_client import GeminiClient
from services.intent import is_expense_intent_image, is_expense_intent_text
from services.log_utils import describe_bytes
from services.message_context import MessageContext
from services.ocr import extract_text_from_image_bytes, _guess_mime_type
from services.receipt_parser import parse_text_for_expenses

logger = logging.getLogger(__name__)

CANNED_UNSUPPORTED_REPLY = (
    "Sorry—I only accept expense submissions right now. Please send a receipt image "
    "or a text message like: 'Lunch 120 THB at Cafe'"
)
ERROR_REPLY_TEXT = (
    "Sorry, I couldn't generate a response right now. "
    "Please try again in a moment."
)
CATEGORY_CONFIRMATION_FOOTER = (
    "Reply with 1–3 if you'd like a different category (saved in a future update)."
)


def format_expense_items(items: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    if not items:
        return None

    lines = []
    for it in items:
        description = str(it.get('description', 'Expense')).strip()
        amount = it.get('amount', '')
        currency = it.get('currency', '')
        amount_text = str(amount)
        currency_text = f" {currency}" if currency else ''
        lines.append(f"- {description}: {amount_text}{currency_text}")

        guess_path = it.get('category_guess_path')
        if guess_path:
            lines.append(f"  Category (guess): {guess_path}")

        alt_paths = it.get('category_alternative_paths') or []
        if alt_paths:
            lines.append("  Please confirm or pick another:")
            for index, alt_path in enumerate(alt_paths[:3], start=1):
                lines.append(f"  {index}) {alt_path}")
            lines.append(f"  {CATEGORY_CONFIRMATION_FOOTER}")

    return "Detected expense(s):\n" + "\n".join(lines)


async def _enrich_and_persist_items(
    items: List[Dict[str, Any]],
    gemini: GeminiClient,
    context: Optional[MessageContext],
) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    insert_rows = []

    for index, item in enumerate(items):
        cat_result = await classify_expense(item, gemini)
        guess_node = resolve_code(cat_result.guessed)
        alt_paths = [format_category_path(resolve_code(code)) for code in cat_result.alternatives]

        enriched_item = dict(item)
        enriched_item['category_guess_path'] = format_category_path(guess_node)
        enriched_item['category_alternative_paths'] = alt_paths
        enriched.append(enriched_item)

        if context is not None:
            insert_rows.append(
                build_insert_row(
                    context=context,
                    item=item,
                    line_item_index=index,
                    category_code=guess_node.code,
                )
            )

    if context is not None and insert_rows:
        result = insert_expenses(insert_rows)
        if result.error:
            logger.warning('Expense persistence failed but reply will continue: %s', result.error)
        else:
            logger.info(
                'Expense persistence complete: inserted=%d skipped=%d',
                result.inserted,
                result.skipped,
            )

    return enriched


async def process_text_message(
    text: str,
    gemini: GeminiClient,
    context: Optional[MessageContext] = None,
) -> str:
    logger.info('Processing text message len=%d', len(text or ''))
    try:
        if await is_expense_intent_text(text, gemini):
            items = parse_text_for_expenses(text)
            if items:
                logger.info('Text pipeline: deterministic parser returned %d item(s)', len(items))
                items = await _enrich_and_persist_items(items, gemini, context)
                reply_text = format_expense_items(items)
            else:
                logger.info('Text pipeline: no parsed items; calling Gemini for free-form reply')
                reply_text = await gemini.generate_reply(text)
                logger.info('Text pipeline: Gemini reply generated (len=%d)', len(reply_text or ''))
            if not reply_text:
                logger.warning('Text pipeline: empty reply after processing')
                return ERROR_REPLY_TEXT
            return reply_text
        logger.info('Text pipeline: message rejected as non-expense intent')
        return CANNED_UNSUPPORTED_REPLY
    except Exception:
        logger.exception('Text message processing failed')
        return ERROR_REPLY_TEXT


async def _extract_expense_items_from_image(
    image_bytes: bytes,
    gemini: GeminiClient,
    mime_type: str,
) -> List[Dict[str, Any]]:
    ocr_text = ''
    ocr_line_count = 0
    try:
        ocr_lines = extract_text_from_image_bytes(image_bytes)
        ocr_line_count = len(ocr_lines)
        ocr_text = '\n'.join(ocr_lines)
        logger.info('Image pipeline: OCR returned %d line(s), text_len=%d', ocr_line_count, len(ocr_text))
    except Exception:
        logger.warning('Image pipeline: OCR raised unexpectedly; continuing to LLM fallbacks', exc_info=True)

    items = parse_text_for_expenses(ocr_text)
    if items:
        logger.info('Image pipeline: deterministic parser returned %d item(s)', len(items))
        return items

    if ocr_text:
        logger.info('Image pipeline: OCR text present but no parser matches; trying assist_parse_ocr')
        items = await assist_parse_ocr(ocr_text, gemini)
        if items:
            logger.info('Image pipeline: assist_parse_ocr returned %d item(s)', len(items))
            return items
        logger.warning('Image pipeline: assist_parse_ocr returned no items')

    logger.info('Image pipeline: falling back to assist_parse_image (LLM vision)')
    items = await assist_parse_image(image_bytes, gemini, mime_type)
    if items:
        logger.info('Image pipeline: assist_parse_image returned %d item(s)', len(items))
    else:
        logger.warning(
            'Image pipeline: all extraction stages failed (ocr_lines=%d ocr_text_len=%d)',
            ocr_line_count,
            len(ocr_text),
        )
    return items


async def process_image_message(
    image_bytes: bytes,
    gemini: GeminiClient,
    mime_type: Optional[str] = None,
    context: Optional[MessageContext] = None,
) -> str:
    resolved_mime = mime_type or _guess_mime_type(image_bytes)
    logger.info(
        'Processing image message: image=%s mime=%s (provided=%s)',
        describe_bytes(image_bytes),
        resolved_mime,
        mime_type or 'auto-detected',
    )
    try:
        if not await is_expense_intent_image(image_bytes, gemini, resolved_mime):
            logger.info('Image pipeline: rejected as non-expense intent')
            return CANNED_UNSUPPORTED_REPLY

        items = await _extract_expense_items_from_image(image_bytes, gemini, resolved_mime)
        if not items:
            logger.warning(
                'Image pipeline: no expense items extracted; returning error reply '
                '(image=%s mime=%s)',
                describe_bytes(image_bytes),
                resolved_mime,
            )
            return ERROR_REPLY_TEXT

        items = await _enrich_and_persist_items(items, gemini, context)
        reply_text = format_expense_items(items)
        if not reply_text:
            logger.warning('Image pipeline: format_expense_items returned empty for %d item(s)', len(items))
            return ERROR_REPLY_TEXT

        logger.info('Image pipeline: success with %d item(s)', len(items))
        return reply_text
    except Exception:
        logger.exception(
            'Image processing failed: image=%s mime=%s',
            describe_bytes(image_bytes),
            resolved_mime,
        )
        return ERROR_REPLY_TEXT
