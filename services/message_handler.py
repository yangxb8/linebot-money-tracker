import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from services.ai_assist import assist_parse_ocr
from services.categorize import classify_expense
from services.category_taxonomy import format_category_path, resolve_code
from services.confirmation_repository import (
    get_confirmation_by_bot_message_id,
    try_mark_reply_processed,
    write_audit,
)
from services.expense_repository import (
    build_insert_row,
    fetch_expense_ids_for_message,
    insert_expenses,
)
from services.gemini_client import GeminiClient
from services.intent import is_expense_intent_image, is_expense_intent_text
from services.log_utils import describe_bytes
from services.message_context import (
    BotReply,
    ConfirmationItemSnapshot,
    ConfirmationSavePayload,
    MessageContext,
    ReplyContext,
    ReplyEditResult,
)
from services.ocr import extract_text_from_image_bytes, _guess_mime_type
from services.receipt_parser import parse_text_for_expenses
from services.receipt_normalize import normalize_receipt_items
from services.receipt_validate import validate_receipt_items
from services.reply_edit import apply_edit_intent, parse_edit_intent
from services.reply_summary import detect_reply_language, format_duplicate_reply, format_unknown_confirmation

logger = logging.getLogger(__name__)

CANNED_UNSUPPORTED_REPLY = (
    "Sorry—I only accept expense submissions right now. Please send a receipt image "
    "or a text message like: 'Lunch 120 THB at Cafe'"
)
ERROR_REPLY_TEXT = (
    "Sorry, I couldn't generate a response right now. "
    "Please try again in a moment."
)
RECEIPT_PARSE_ERROR_REPLY = (
    "I couldn't read this receipt clearly enough to log expenses. "
    "Please try a clearer photo, or send the total as text (e.g. まいばすけっと 321円)."
)


def _prepare_receipt_items(items: List[Dict[str, Any]], ocr_text: str) -> List[Dict[str, Any]]:
    if not items:
        return []
    normalized = normalize_receipt_items(items, ocr_text)
    validated = validate_receipt_items(normalized, ocr_text)
    return validated or []
CATEGORY_CONFIRMATION_FOOTER = (
    "Reply to this message to change category (1–3), edit fields, delete, or restore."
)


def format_expense_items(
    items: Optional[List[Dict[str, Any]]],
    *,
    logged_by_line_user_id: Optional[str] = None,
    is_shared_tenant: bool = False,
) -> Optional[str]:
    if not items:
        return None

    lines = []
    if is_shared_tenant and logged_by_line_user_id:
        lines.append(f'Logged by: {logged_by_line_user_id}')
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


def _build_confirmation_payload(
    items: List[Dict[str, Any]],
    confirmation_text: str,
    context: MessageContext,
) -> Optional[ConfirmationSavePayload]:
    id_rows = fetch_expense_ids_for_message(context.tenant, context.source_message_id)
    if not id_rows:
        return None

    id_by_index = {int(row['line_item_index']): str(row['id']) for row in id_rows}
    snapshots: List[ConfirmationItemSnapshot] = []

    for index, item in enumerate(items):
        expense_id = id_by_index.get(index)
        if not expense_id:
            continue
        guess_code = item.get('category_guess_code') or 'unknown'
        alt_codes = tuple(item.get('category_alternative_codes') or ())
        amount_raw = item.get('amount', 0)
        snapshots.append(
            ConfirmationItemSnapshot(
                line_item_index=index,
                expense_id=expense_id,
                description=str(item.get('description', 'Expense')),
                amount=Decimal(str(amount_raw)).quantize(Decimal('0.01')),
                currency=str(item.get('currency', 'JPY')).strip().upper()[:3],
                category_guess_code=guess_code,
                category_alternatives=alt_codes,
            )
        )

    if not snapshots:
        return None

    return ConfirmationSavePayload(
        tenant=context.tenant,
        confirmation_text=confirmation_text,
        items=tuple(snapshots),
    )


async def _enrich_and_persist_items(
    items: List[Dict[str, Any]],
    gemini: GeminiClient,
    context: Optional[MessageContext],
) -> tuple[List[Dict[str, Any]], Optional[ConfirmationSavePayload]]:
    enriched: List[Dict[str, Any]] = []
    insert_rows = []

    for index, item in enumerate(items):
        cat_result = await classify_expense(item, gemini)
        guess_node = resolve_code(cat_result.guessed)
        alt_paths = [format_category_path(resolve_code(code)) for code in cat_result.alternatives]

        enriched_item = dict(item)
        enriched_item['category_guess_path'] = format_category_path(guess_node)
        enriched_item['category_guess_code'] = guess_node.code
        enriched_item['category_alternative_paths'] = alt_paths
        enriched_item['category_alternative_codes'] = list(cat_result.alternatives)
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

    confirmation_payload: Optional[ConfirmationSavePayload] = None
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
            reply_text_preview = format_expense_items(
                enriched,
                logged_by_line_user_id=context.tenant.logged_by_line_user_id,
                is_shared_tenant=context.tenant.is_shared,
            )
            if reply_text_preview:
                confirmation_payload = _build_confirmation_payload(
                    enriched,
                    reply_text_preview,
                    context,
                )

    return enriched, confirmation_payload


def _text_reply(text: str, confirmation: Optional[ConfirmationSavePayload] = None) -> BotReply:
    return BotReply(text=text, confirmation=confirmation)


async def process_reply_edit(
    text: str,
    reply_context: ReplyContext,
    gemini: GeminiClient,
) -> ReplyEditResult:
    language = detect_reply_language(text)

    if not try_mark_reply_processed(reply_context.tenant, reply_context.user_reply_message_id):
        return ReplyEditResult(text=format_duplicate_reply(language))

    confirmation = get_confirmation_by_bot_message_id(
        reply_context.quoted_bot_message_id,
        reply_context.tenant,
    )
    if confirmation is None:
        return ReplyEditResult(text=format_unknown_confirmation(language))

    try:
        intent = await parse_edit_intent(
            text,
            list(confirmation.items_snapshot),
            confirmation.pending_action,
            gemini,
        )
        result = await apply_edit_intent(intent, confirmation, text, gemini)
        write_audit(
            confirmation.id,
            reply_context.line_user_id,
            reply_context.user_reply_message_id,
            text,
            result.intent_json,
            result.status,
            result.summary,
        )
        return ReplyEditResult(
            text=result.summary,
            confirmation_id=confirmation.id,
            anchor_reply_to_sent_message=result.anchor_reply_to_sent_message,
        )
    except Exception:
        logger.exception('process_reply_edit failed')
        from services.reply_summary import EditSummaryInput, format_edit_result

        return ReplyEditResult(
            text=format_edit_result(
                language,
                EditSummaryInput(status='error', action='update', error_message=None),
            ),
            confirmation_id=confirmation.id,
        )


async def process_text_message(
    text: str,
    gemini: GeminiClient,
    context: Optional[MessageContext] = None,
) -> BotReply:
    logger.info('Processing text message len=%d', len(text or ''))
    try:
        if await is_expense_intent_text(text, gemini):
            items = parse_text_for_expenses(text)
            confirmation_payload = None
            if items:
                logger.info('Text pipeline: deterministic parser returned %d item(s)', len(items))
                items, confirmation_payload = await _enrich_and_persist_items(items, gemini, context)
                reply_text = format_expense_items(
                    items,
                    logged_by_line_user_id=context.tenant.logged_by_line_user_id if context else None,
                    is_shared_tenant=context.tenant.is_shared if context else False,
                )
            else:
                logger.info('Text pipeline: no parsed items; calling Gemini for free-form reply')
                reply_text = await gemini.generate_reply(text)
                logger.info('Text pipeline: Gemini reply generated (len=%d)', len(reply_text or ''))
            if not reply_text:
                logger.warning('Text pipeline: empty reply after processing')
                return _text_reply(ERROR_REPLY_TEXT)
            return _text_reply(reply_text, confirmation_payload)
        logger.info('Text pipeline: message rejected as non-expense intent')
        return _text_reply(CANNED_UNSUPPORTED_REPLY)
    except Exception:
        logger.exception('Text message processing failed')
        return _text_reply(ERROR_REPLY_TEXT)


async def _extract_expense_items_from_ocr(
    image_bytes: bytes,
    gemini: GeminiClient,
) -> tuple[List[Dict[str, Any]], int, int, str]:
    """Run OCR and text-based extraction (parser + OCR assist). Returns (items, line_count, text_len, ocr_text)."""
    ocr_text = ''
    ocr_line_count = 0
    try:
        ocr_lines = extract_text_from_image_bytes(image_bytes)
        ocr_line_count = len(ocr_lines)
        ocr_text = '\n'.join(ocr_lines)
        logger.info('Image pipeline: OCR returned %d line(s), text_len=%d', ocr_line_count, len(ocr_text))
    except Exception:
        logger.warning('Image pipeline: OCR raised unexpectedly; continuing to LLM fallbacks', exc_info=True)

    items = _prepare_receipt_items(parse_text_for_expenses(ocr_text), ocr_text)
    if items:
        logger.info('Image pipeline: deterministic parser returned %d item(s)', len(items))
        return items, ocr_line_count, len(ocr_text), ocr_text

    if ocr_text:
        logger.info('Image pipeline: OCR text present but no parser matches; trying assist_parse_ocr')
        items = _prepare_receipt_items(await assist_parse_ocr(ocr_text, gemini), ocr_text)
        if items:
            logger.info('Image pipeline: assist_parse_ocr returned %d item(s)', len(items))
            return items, ocr_line_count, len(ocr_text), ocr_text
        logger.warning('Image pipeline: assist_parse_ocr returned no valid items')

    return [], ocr_line_count, len(ocr_text), ocr_text


async def process_image_message(
    image_bytes: bytes,
    gemini: GeminiClient,
    mime_type: Optional[str] = None,
    context: Optional[MessageContext] = None,
) -> BotReply:
    resolved_mime = mime_type or _guess_mime_type(image_bytes)
    logger.info(
        'Processing image message: image=%s mime=%s (provided=%s)',
        describe_bytes(image_bytes),
        resolved_mime,
        mime_type or 'auto-detected',
    )
    try:
        items, ocr_line_count, ocr_text_len, ocr_text = await _extract_expense_items_from_ocr(
            image_bytes,
            gemini,
        )
        if not items and not ocr_text.strip():
            logger.info('Image pipeline: OCR empty; checking receipt intent before giving up')
            if not await is_expense_intent_image(image_bytes, gemini, resolved_mime):
                logger.info('Image pipeline: rejected as non-expense intent')
                return _text_reply(CANNED_UNSUPPORTED_REPLY)

        if not items:
            logger.warning(
                'Image pipeline: no expense items extracted after all stages '
                '(image=%s mime=%s ocr_lines=%d ocr_text_len=%d)',
                describe_bytes(image_bytes),
                resolved_mime,
                ocr_line_count,
                ocr_text_len,
            )
            return _text_reply(RECEIPT_PARSE_ERROR_REPLY)

        items, confirmation_payload = await _enrich_and_persist_items(items, gemini, context)
        reply_text = format_expense_items(
            items,
            logged_by_line_user_id=context.tenant.logged_by_line_user_id if context else None,
            is_shared_tenant=context.tenant.is_shared if context else False,
        )
        if not reply_text:
            logger.warning('Image pipeline: format_expense_items returned empty for %d item(s)', len(items))
            return _text_reply(ERROR_REPLY_TEXT)

        logger.info('Image pipeline: success with %d item(s)', len(items))
        return _text_reply(reply_text, confirmation_payload)
    except Exception:
        logger.exception(
            'Image processing failed: image=%s mime=%s',
            describe_bytes(image_bytes),
            resolved_mime,
        )
        return _text_reply(ERROR_REPLY_TEXT)
