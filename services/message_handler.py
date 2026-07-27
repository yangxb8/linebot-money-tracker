import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from services.ai_assist import assist_parse_image, assist_parse_ocr, assist_parse_text
from services.categorize import classify_expense_with_memory
from services.category_taxonomy import format_category_path, resolve_code
from services.confirmation_repository import (
    get_confirmation_by_bot_message_id,
    clear_pending_state,
    get_latest_pending_confirmation,
    set_pending_state,
    try_mark_reply_processed,
    write_audit,
)
from services.expense_repository import (
    build_insert_row,
    fetch_expense_ids_for_message,
    insert_expenses,
)
from services.gemini_client import GeminiClient, GeminiUsageLimitError
from services.metered_gemini import UserUsageLimitExceeded
from services.inbound_message_repository import has_recent_wish_list_trigger_text
from services.intent import classify_text_message_intent
from services.webapp_intent import is_webapp_request_obvious, webapp_link_reply
from services.log_utils import describe_bytes
from services.message_context import (
    BotReply,
    ConfirmationItemSnapshot,
    ConfirmationSavePayload,
    MessageContext,
    ReplyContext,
    ReplyEditResult,
)
from services.wish_list import (
    WishListCandidate,
    build_wish_list_await_details_reply,
    build_wish_list_proposal_reply,
    extract_product_url,
    format_wish_list_ask_details,
    looks_like_wish_list_intent,
)
from services.ocr import extract_text_from_image_bytes, _guess_mime_type
from services.receipt_image_preprocess import preprocess_receipt_image
from services.receipt_parser import parse_text_for_expenses
from services.receipt_store_name import propagate_receipt_store_name
from services.receipt_normalize import normalize_receipt_items
from services.receipt_validate import validate_receipt_items
from services.confirmation_i18n import format_expense_confirmation, t
from services.confirmation_display_settings import confirmation_show_item_details
from services.help_intent import help_reply, is_help_request_obvious
from services.reply_edit import apply_edit_intent, is_cancel_pending, parse_edit_intent
from services.reply_summary import format_duplicate_reply, format_unknown_confirmation
from services.user_language import maybe_update_from_user_message
from services.budget_pace import expense_rows_from_enriched, maybe_prepend_budget_pace_warning
from services.bot_persona import persona_scope, resolve_persona_for_tenant
from services.tenant_settings import resolve_tenant_reply_language
from services.wish_list import format_wish_list_cancelled

logger = logging.getLogger(__name__)

def receipt_parse_error_reply(language: str = 'ja') -> str:
    return t(language, 'parse_error')


def canned_unsupported_reply(language: str = 'ja') -> str:
    return t(language, 'unsupported')


def error_reply_text(language: str = 'ja') -> str:
    return t(language, 'error')


def usage_limit_reply(language: str = 'ja') -> str:
    return t(language, 'usage_limit')


# Backward-compatible defaults (English) for imports in tests and main.py
CANNED_UNSUPPORTED_REPLY = canned_unsupported_reply('en')
ERROR_REPLY_TEXT = error_reply_text('en')
RECEIPT_PARSE_ERROR_REPLY = receipt_parse_error_reply('en')


def _prepare_receipt_items(items: List[Dict[str, Any]], ocr_text: str) -> List[Dict[str, Any]]:
    """OCR pipeline: normalize shelf prices then validate against OCR totals (unused in production)."""
    if not items:
        return []
    normalized = normalize_receipt_items(items, ocr_text)
    validated = validate_receipt_items(normalized, ocr_text)
    return validated or []


def _prepare_llm_receipt_items(
    items: List[Dict[str, Any]],
    receipt_total: Decimal,
) -> List[Dict[str, Any]]:
    """LLM vision pipeline: trust tax-inclusive line amounts; validate sum vs LLM total."""
    if not items:
        return []
    validated = validate_receipt_items(items, receipt_total=receipt_total)
    return validated or []
def format_expense_items(
    items: Optional[List[Dict[str, Any]]],
    *,
    language: str = 'ja',
    logged_by_line_user_id: Optional[str] = None,
    logged_by_display_name: Optional[str] = None,
    is_shared_tenant: bool = False,
    show_item_details: bool = False,
) -> Optional[str]:
    return format_expense_confirmation(
        items or [],
        language=language,
        logged_by_line_user_id=logged_by_line_user_id,
        logged_by_display_name=logged_by_display_name,
        is_shared_tenant=is_shared_tenant,
        show_item_details=show_item_details,
    )


def _confirmation_format_kwargs(context: Optional[MessageContext]) -> Dict[str, Any]:
    if context is None:
        return {
            'logged_by_line_user_id': None,
            'logged_by_display_name': None,
            'is_shared_tenant': False,
            'show_item_details': False,
        }
    return {
        'logged_by_line_user_id': context.tenant.logged_by_line_user_id,
        'logged_by_display_name': context.logged_by_display_name,
        'is_shared_tenant': context.tenant.is_shared,
        'show_item_details': confirmation_show_item_details(context.tenant),
    }


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
    *,
    memory_mode: str = 'merchant',
) -> tuple[List[Dict[str, Any]], Optional[ConfirmationSavePayload]]:
    enriched: List[Dict[str, Any]] = []
    insert_rows = []

    for index, item in enumerate(items):
        tenant = context.tenant if context is not None else None
        cat_result = await classify_expense_with_memory(
            item,
            gemini,
            tenant=tenant,
            exclude_source_message_id=context.source_message_id if context is not None else None,
            memory_mode=memory_mode,  # type: ignore[arg-type]
        )
        guess_node = resolve_code(cat_result.guessed, tenant)
        alt_paths = [
            format_category_path(resolve_code(code, tenant)) for code in cat_result.alternatives
        ]

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
                    category_guess_code=cat_result.guessed,
                    category_source=cat_result.source,
                    merchant_key=cat_result.merchant_key,
                    display_merchant=cat_result.display_merchant,
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
                language=context.reply_language,
                **_confirmation_format_kwargs(context),
            )
            if reply_text_preview:
                confirmation_payload = _build_confirmation_payload(
                    enriched,
                    reply_text_preview,
                    context,
                )

    return enriched, confirmation_payload


def _text_reply(
    text: str,
    confirmation: Optional[ConfirmationSavePayload] = None,
    *,
    retryable_failure: Optional[str] = None,
) -> BotReply:
    return BotReply(text=text, confirmation=confirmation, retryable_failure=retryable_failure)


async def _finalize_expense_reply(
    reply_text: Optional[str],
    items: List[Dict[str, Any]],
    gemini: GeminiClient,
    context: Optional[MessageContext],
    confirmation_payload: Optional[ConfirmationSavePayload],
) -> BotReply:
    language = context.reply_language if context else 'ja'
    if not reply_text:
        return _text_reply(
            error_reply_text(language),
            retryable_failure='processing_error',
        )
    if context is not None:
        reply_text = await maybe_prepend_budget_pace_warning(
            reply_text,
            expense_rows=expense_rows_from_enriched(items, context),
            tenant=context.tenant,
            language=language,
            gemini=gemini,
        )
    return _text_reply(reply_text, confirmation_payload)


async def process_reply_edit(
    text: str,
    reply_context: ReplyContext,
    gemini: GeminiClient,
) -> ReplyEditResult:
    language = reply_context.reply_language
    explicit = maybe_update_from_user_message(reply_context.line_user_id, text)
    if explicit:
        language = explicit
    language = resolve_tenant_reply_language(reply_context.tenant, language)

    persona = resolve_persona_for_tenant(reply_context.tenant)
    with persona_scope(persona):
        if not try_mark_reply_processed(reply_context.tenant, reply_context.user_reply_message_id):
            return ReplyEditResult(text=format_duplicate_reply(language))

        confirmation = get_confirmation_by_bot_message_id(
            reply_context.quoted_bot_message_id,
            reply_context.tenant,
        )
        if confirmation is None:
            return ReplyEditResult(text=format_unknown_confirmation(language))

        try:
            if confirmation.pending_action == 'wish_list_await_details':
                return await _handle_wish_list_await_details_text(
                    text,
                    confirmation,
                    reply_context,
                    gemini,
                    language,
                )

            intent = await parse_edit_intent(
                text,
                list(confirmation.items_snapshot),
                confirmation.pending_action,
                gemini,
                confirmation.pending_payload,
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


async def _handle_wish_list_await_details_text(
    text: str,
    confirmation,
    reply_context: ReplyContext,
    gemini: GeminiClient,
    language: str,
) -> ReplyEditResult:
    if is_cancel_pending(text):
        clear_pending_state(confirmation.id)
        summary = format_wish_list_cancelled(language)
        write_audit(
            confirmation.id,
            reply_context.line_user_id,
            reply_context.user_reply_message_id,
            text,
            {'action': 'cancel_pending', 'pending_action': 'wish_list_await_details'},
            'applied',
            summary,
        )
        return ReplyEditResult(text=summary, confirmation_id=confirmation.id)

    msg_context = MessageContext(
        tenant=reply_context.tenant,
        source_message_id=reply_context.user_reply_message_id,
        reply_language=language,
    )
    bot_reply = await process_wish_list_details_from_text(text, gemini, msg_context)
    pending_action = (
        bot_reply.confirmation.pending_action if bot_reply.confirmation else 'wish_list_await_details'
    )
    pending_payload = (
        bot_reply.confirmation.pending_payload if bot_reply.confirmation else {}
    ) or {}
    set_pending_state(confirmation.id, pending_action, pending_payload)
    write_audit(
        confirmation.id,
        reply_context.line_user_id,
        reply_context.user_reply_message_id,
        text,
        {'action': 'wish_list_provide_details', 'pending_action': pending_action},
        'applied',
        bot_reply.text,
    )
    return ReplyEditResult(
        text=bot_reply.text,
        confirmation_id=confirmation.id,
        anchor_reply_to_sent_message=True,
    )


async def process_reply_wish_list_image(
    image_bytes: bytes,
    reply_context: ReplyContext,
    gemini: GeminiClient,
    *,
    mime_type: Optional[str] = None,
) -> ReplyEditResult:
    """Handle an image reply to a wish_list_await_details confirmation."""
    language = resolve_tenant_reply_language(
        reply_context.tenant,
        reply_context.reply_language,
    )
    persona = resolve_persona_for_tenant(reply_context.tenant)
    with persona_scope(persona):
        if not try_mark_reply_processed(reply_context.tenant, reply_context.user_reply_message_id):
            return ReplyEditResult(text=format_duplicate_reply(language))

        confirmation = get_confirmation_by_bot_message_id(
            reply_context.quoted_bot_message_id,
            reply_context.tenant,
        )
        if confirmation is None or confirmation.pending_action != 'wish_list_await_details':
            return ReplyEditResult(text=format_unknown_confirmation(language))

        try:
            msg_context = MessageContext(
                tenant=reply_context.tenant,
                source_message_id=reply_context.user_reply_message_id,
                reply_language=language,
            )
            bot_reply = await process_wish_list_details_from_image(
                image_bytes,
                gemini,
                msg_context,
                mime_type=mime_type,
            )
            pending_action = (
                bot_reply.confirmation.pending_action
                if bot_reply.confirmation
                else 'wish_list_await_details'
            )
            pending_payload = (
                bot_reply.confirmation.pending_payload if bot_reply.confirmation else {}
            ) or {}
            set_pending_state(confirmation.id, pending_action, pending_payload)
            write_audit(
                confirmation.id,
                reply_context.line_user_id,
                reply_context.user_reply_message_id,
                '[image]',
                {'action': 'wish_list_provide_details_image', 'pending_action': pending_action},
                'applied',
                bot_reply.text,
            )
            return ReplyEditResult(
                text=bot_reply.text,
                confirmation_id=confirmation.id,
                anchor_reply_to_sent_message=True,
            )
        except UserUsageLimitExceeded as exc:
            return ReplyEditResult(text=str(exc), confirmation_id=confirmation.id)
        except GeminiUsageLimitError:
            return ReplyEditResult(
                text=usage_limit_reply(language),
                confirmation_id=confirmation.id,
            )
        except Exception:
            logger.exception('process_reply_wish_list_image failed')
            return ReplyEditResult(
                text=error_reply_text(language),
                confirmation_id=confirmation.id,
            )


async def process_text_message(
    text: str,
    gemini: GeminiClient,
    context: Optional[MessageContext] = None,
) -> BotReply:
    persona = resolve_persona_for_tenant(context.tenant if context else None)
    with persona_scope(persona):
        return await _process_text_message_inner(text, gemini, context)


async def _enrich_items_without_persist(
    items: List[Dict[str, Any]],
    gemini: GeminiClient,
    context: Optional[MessageContext],
    *,
    memory_mode: str = 'merchant',
) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for item in items:
        tenant = context.tenant if context is not None else None
        cat_result = await classify_expense_with_memory(
            item,
            gemini,
            tenant=tenant,
            exclude_source_message_id=context.source_message_id if context is not None else None,
            memory_mode=memory_mode,  # type: ignore[arg-type]
        )
        guess_node = resolve_code(cat_result.guessed, tenant)
        enriched_item = dict(item)
        enriched_item['category_guess_path'] = format_category_path(guess_node)
        enriched_item['category_guess_code'] = guess_node.code
        enriched_item['category_node_id'] = guess_node.id
        enriched_item['assigned_level'] = guess_node.level
        enriched_item['category_l1_id'] = guess_node.l1_id
        enriched_item['category_l2_id'] = guess_node.l2_id
        enriched_item['category_l3_id'] = guess_node.l3_id
        enriched.append(enriched_item)
    return enriched


async def _wish_list_reply_from_items(
    items: List[Dict[str, Any]],
    gemini: GeminiClient,
    context: Optional[MessageContext],
    *,
    source_text: Optional[str] = None,
    memory_mode: str = 'merchant',
) -> BotReply:
    language = context.reply_language if context else 'ja'
    if context is None:
        return _text_reply(format_wish_list_ask_details(language))

    enriched = await _enrich_items_without_persist(
        items,
        gemini,
        context,
        memory_mode=memory_mode,
    )
    if not enriched:
        return build_wish_list_await_details_reply(context)

    first = enriched[0]
    amount_raw = first.get('amount')
    try:
        amount = Decimal(str(amount_raw)).quantize(Decimal('0.01'))
    except Exception:
        amount = Decimal('0')
    if amount <= 0:
        return build_wish_list_await_details_reply(context)

    name = str(first.get('description') or 'Item').strip() or 'Item'
    product_url = extract_product_url(source_text)
    candidate = WishListCandidate(
        name=name,
        amount=amount,
        currency=str(first.get('currency') or 'JPY').strip().upper()[:3] or 'JPY',
        assigned_level=int(first.get('assigned_level') or 1),
        category_node_id=str(first['category_node_id']),
        category_l1_id=str(first['category_l1_id']),
        category_l2_id=first.get('category_l2_id'),
        category_l3_id=first.get('category_l3_id'),
        category_label=str(first.get('category_guess_path') or ''),
        product_url=product_url,
    )
    logger.info('Wish-list pipeline: proposing add for %s ¥%s', name, amount)
    return build_wish_list_proposal_reply(candidate, context)


async def process_wish_list_details_from_text(
    text: str,
    gemini: GeminiClient,
    context: MessageContext,
) -> BotReply:
    """Parse reply text into a wish-list proposal (budget impact + yes/no)."""
    items = parse_text_for_expenses(text)
    if not items:
        items = await assist_parse_text(text, gemini)
    if not items:
        return build_wish_list_await_details_reply(context)
    return await _wish_list_reply_from_items(
        items,
        gemini,
        context,
        source_text=text,
    )


async def process_wish_list_details_from_image(
    image_bytes: bytes,
    gemini: GeminiClient,
    context: MessageContext,
    *,
    mime_type: Optional[str] = None,
) -> BotReply:
    """Extract product from a reply image into a wish-list proposal."""
    resolved_mime = mime_type or _guess_mime_type(image_bytes)
    try:
        items = await _extract_expense_items_from_image(image_bytes, gemini, resolved_mime)
    except (UserUsageLimitExceeded, GeminiUsageLimitError):
        raise
    if not items:
        return build_wish_list_await_details_reply(context)
    return await _wish_list_reply_from_items(
        items,
        gemini,
        context,
        memory_mode='item',
    )


async def _process_text_message_inner(
    text: str,
    gemini: GeminiClient,
    context: Optional[MessageContext] = None,
) -> BotReply:
    language = context.reply_language if context else 'ja'
    logger.info('Processing text message len=%d', len(text or ''))
    try:
        # Wish intent must be checked before expense persist (deterministic parse may match).
        if looks_like_wish_list_intent(text):
            logger.info('Text pipeline: wish_list phrase gate')
            items = parse_text_for_expenses(text)
            if not items:
                items = await assist_parse_text(text, gemini)
            if not items:
                if context is None:
                    return _text_reply(format_wish_list_ask_details(language))
                return build_wish_list_await_details_reply(context)
            return await _wish_list_reply_from_items(
                items,
                gemini,
                context,
                source_text=text,
            )

        items = parse_text_for_expenses(text)
        if items:
            logger.info('Text pipeline: deterministic parser returned %d item(s)', len(items))
            items, confirmation_payload = await _enrich_and_persist_items(items, gemini, context)
            reply_text = format_expense_items(
                items,
                language=language,
                **_confirmation_format_kwargs(context),
            )
            return await _finalize_expense_reply(
                reply_text,
                items,
                gemini,
                context,
                confirmation_payload,
            )

        if is_webapp_request_obvious(text):
            logger.info('Text pipeline: obvious webapp request (shortcut)')
            return _text_reply(webapp_link_reply(language))

        if is_help_request_obvious(text):
            logger.info('Text pipeline: help/how-to request (shortcut)')
            return _text_reply(help_reply(language))

        message_intent = await classify_text_message_intent(text, gemini)

        if message_intent == 'webapp':
            logger.info('Text pipeline: webapp intent detected')
            return _text_reply(webapp_link_reply(language))

        if message_intent == 'wish_list':
            logger.info('Text pipeline: wish_list intent (LLM)')
            items = await assist_parse_text(text, gemini)
            if not items:
                return build_wish_list_await_details_reply(context) if context else _text_reply(
                    format_wish_list_ask_details(language)
                )
            return await _wish_list_reply_from_items(
                items,
                gemini,
                context,
                source_text=text,
            )

        if message_intent == 'expense':
            confirmation_payload = None
            logger.info('Text pipeline: no deterministic items; trying assist_parse_text')
            items = await assist_parse_text(text, gemini)

            if items:
                logger.info('Text pipeline: assist returned %d item(s)', len(items))
                items, confirmation_payload = await _enrich_and_persist_items(items, gemini, context)
                reply_text = format_expense_items(
                    items,
                    language=language,
                    **_confirmation_format_kwargs(context),
                )
                return await _finalize_expense_reply(
                    reply_text,
                    items,
                    gemini,
                    context,
                    confirmation_payload,
                )

            logger.warning('Text pipeline: expense intent but no parseable items')
            return _text_reply(receipt_parse_error_reply(language))

        logger.info('Text pipeline: message rejected as non-expense intent')
        return _text_reply(canned_unsupported_reply(language))
    except UserUsageLimitExceeded as exc:
        return _text_reply(str(exc))
    except GeminiUsageLimitError:
        return _text_reply(usage_limit_reply(language))
    except Exception:
        logger.exception('Text message processing failed')
        return _text_reply(
            error_reply_text(language),
            retryable_failure='processing_error',
        )


async def _extract_expense_items_from_ocr(
    image_bytes: bytes,
    gemini: GeminiClient,
) -> List[Dict[str, Any]]:
    """Legacy OCR pipeline (kept for future use — not called in production).

    OCR → deterministic parser → assist_parse_ocr fallback.
    Re-enable by wiring this into ``process_image_message`` instead of the LLM path.
    """
    ocr_text = ''
    try:
        ocr_lines = extract_text_from_image_bytes(image_bytes)
        ocr_text = '\n'.join(ocr_lines)
        logger.info('OCR pipeline: OCR returned %d line(s), text_len=%d', len(ocr_lines), len(ocr_text))
    except Exception:
        logger.warning('OCR pipeline: OCR raised unexpectedly', exc_info=True)

    parsed = parse_text_for_expenses(ocr_text)
    prepared = _prepare_receipt_items(parsed, ocr_text)
    if prepared:
        logger.info('OCR pipeline: deterministic parser returned %d item(s)', len(prepared))
        return prepared

    if ocr_text:
        assist_prepared = _prepare_receipt_items(await assist_parse_ocr(ocr_text, gemini), ocr_text)
        if assist_prepared:
            logger.info('OCR pipeline: assist_parse_ocr returned %d item(s)', len(assist_prepared))
            return assist_prepared

    return []


async def _extract_expense_items_from_image(
    image_bytes: bytes,
    gemini: GeminiClient,
    mime_type: str,
) -> List[Dict[str, Any]]:
    """Production image pipeline: preprocess → Gemini vision → validate against LLM total."""
    processed_bytes, processed_mime = preprocess_receipt_image(image_bytes)

    parse_result = await assist_parse_image(processed_bytes, gemini, processed_mime)
    if parse_result:
        prepared = _prepare_llm_receipt_items(parse_result.items, parse_result.total)
        if prepared:
            prepared = propagate_receipt_store_name(prepared, parse_result.store_name)
            logger.info(
                'Image pipeline: LLM returned %d item(s), total=%s %s store_name=%r',
                len(prepared),
                parse_result.total,
                parse_result.currency,
                parse_result.store_name,
            )
            return prepared
        logger.warning(
            'Image pipeline: LLM parse failed validation (items=%d total=%s); retrying once',
            len(parse_result.items),
            parse_result.total,
        )
    else:
        logger.warning(
            'Image pipeline: assist_parse_image returned no valid parse; retrying once'
        )

    retry_result = await assist_parse_image(
        processed_bytes,
        gemini,
        processed_mime,
        retry=True,
    )
    if not retry_result:
        logger.warning('Image pipeline: assist_parse_image retry returned no valid parse')
        return []

    prepared = _prepare_llm_receipt_items(retry_result.items, retry_result.total)
    if prepared:
        prepared = propagate_receipt_store_name(prepared, retry_result.store_name)
        logger.info(
            'Image pipeline: LLM retry returned %d item(s), total=%s %s store_name=%r',
            len(prepared),
            retry_result.total,
            retry_result.currency,
            retry_result.store_name,
        )
        return prepared

    logger.warning(
        'Image pipeline: LLM retry also failed validation (items=%d total=%s)',
        len(retry_result.items),
        retry_result.total,
    )
    return []


async def process_image_message(
    image_bytes: bytes,
    gemini: GeminiClient,
    mime_type: Optional[str] = None,
    context: Optional[MessageContext] = None,
    accompanying_text: Optional[str] = None,
) -> BotReply:
    persona = resolve_persona_for_tenant(context.tenant if context else None)
    with persona_scope(persona):
        return await _process_image_message_inner(
            image_bytes,
            gemini,
            mime_type,
            context,
            accompanying_text=accompanying_text,
        )


async def _process_image_message_inner(
    image_bytes: bytes,
    gemini: GeminiClient,
    mime_type: Optional[str] = None,
    context: Optional[MessageContext] = None,
    accompanying_text: Optional[str] = None,
) -> BotReply:
    resolved_mime = mime_type or _guess_mime_type(image_bytes)
    logger.info(
        'Processing image message: image=%s mime=%s (provided=%s) accompanying_text=%s',
        describe_bytes(image_bytes),
        resolved_mime,
        mime_type or 'auto-detected',
        bool(accompanying_text),
    )
    language = context.reply_language if context else 'ja'
    try:
        wish_pending = None
        wish_triggered = False
        if context is not None:
            # 30s workaround for LINE: text ("want to buy") and image arrive as separate events.
            # We only trigger for the same sender in group chats (tenant + line_user_id scoped).
            wish_pending = get_latest_pending_confirmation(
                context.tenant,
                pending_action='wish_list_await_details',
                within_seconds=30,
            )
            if wish_pending is None:
                wish_triggered = has_recent_wish_list_trigger_text(
                    context.tenant,
                    within_seconds=30,
                )

        try:
            items = await _extract_expense_items_from_image(image_bytes, gemini, resolved_mime)
        except UserUsageLimitExceeded as exc:
            return _text_reply(str(exc))
        except GeminiUsageLimitError:
            logger.warning('Image pipeline: Gemini usage limit reached for receipt parse')
            return _text_reply(usage_limit_reply(language))

        if not items:
            logger.warning(
                'Image pipeline: no expense items extracted (image=%s mime=%s)',
                describe_bytes(image_bytes),
                resolved_mime,
            )
            return _text_reply(receipt_parse_error_reply(language))

        if accompanying_text and looks_like_wish_list_intent(accompanying_text):
            logger.info('Image pipeline: wish_list intent via accompanying text')
            return await _wish_list_reply_from_items(
                items,
                gemini,
                context,
                source_text=accompanying_text,
                memory_mode='item',
            )

        if wish_pending is not None or wish_triggered:
            log_id = wish_pending.id if wish_pending is not None else 'recent-wish-text'
            logger.info(
                'Image pipeline: wish_list correlation (confirmation_id=%s triggered=%s); treating image as wish details',
                log_id,
                wish_triggered,
            )
            bot_reply = await _wish_list_reply_from_items(
                items,
                gemini,
                context,
                source_text=None,
                memory_mode='item',
            )
            if (
                wish_pending is not None
                and bot_reply.confirmation
                and bot_reply.confirmation.pending_action == 'wish_list_add'
            ):
                clear_pending_state(wish_pending.id)
            return bot_reply

        items, confirmation_payload = await _enrich_and_persist_items(
            items,
            gemini,
            context,
            memory_mode='item',
        )
        reply_text = format_expense_items(
            items,
            language=language,
            **_confirmation_format_kwargs(context),
        )
        if not reply_text:
            logger.warning('Image pipeline: format_expense_items returned empty for %d item(s)', len(items))
            return _text_reply(
                error_reply_text(language),
                retryable_failure='processing_error',
            )

        logger.info('Image pipeline: success with %d item(s)', len(items))
        return await _finalize_expense_reply(
            reply_text,
            items,
            gemini,
            context,
            confirmation_payload,
        )
    except Exception:
        logger.exception(
            'Image processing failed: image=%s mime=%s',
            describe_bytes(image_bytes),
            resolved_mime,
        )
        return _text_reply(
            error_reply_text(language),
            retryable_failure='processing_error',
        )

