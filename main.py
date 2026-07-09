# -*- coding: utf-8 -*-

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Request, FastAPI, HTTPException

from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.messaging.api.async_messaging_api_blob import AsyncMessagingApiBlob
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent

from services.confirmation_repository import (
    get_confirmation_by_bot_message_id,
    save_confirmation,
    try_mark_reply_processed,
    update_interaction_bot_message_id,
)
from services.env_loader import load_env, require_env_vars
from services.inbound_message_repository import (
    get_failure_retry_anchor,
    save_failure_retry_anchor,
    save_inbound_image_message,
    save_inbound_text_message,
)
from services.metered_gemini import UserUsageLimitExceeded, create_gemini_client
from services.line_event import (
    extract_image_message_id,
    extract_line_user_id,
    extract_quoted_message_id,
    extract_source_message_id,
    extract_text_message,
)
from services.tenant_context import TenantContext, resolve_tenant_from_event
from services.bot_persona import persona_scope, resolve_persona_for_tenant
from services.message_context import BotReply, MessageContext, ReplyContext, ReplyEditResult, RetryContext
from services.line_profile import fetch_line_display_name, fetch_line_profile_language
from services.line_chat import fetch_chat_display_name
from services.message_retry import is_retry_intent, process_message_retry, retry_not_found_reply
from services.reply_summary import format_duplicate_reply
from services.usage_limiter import format_denial_reply, prepare_inbound_usage
from services.usage_metering import usage_billing_scope
from services.message_handler import (
    CANNED_UNSUPPORTED_REPLY,
    ERROR_REPLY_TEXT,
    canned_unsupported_reply,
    error_reply_text,
    process_image_message,
    process_reply_edit,
    process_text_message,
)
from services.user_language import maybe_update_from_line_profile, resolve_reply_language

_log_level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger('services').setLevel(_log_level)
logger = logging.getLogger(__name__)

load_env()

WEBHOOK_REQUIRED_VARS = [
    'LINE_CHANNEL_SECRET',
    'LINE_CHANNEL_ACCESS_TOKEN',
    'GEMINI_API_KEY',
]

async_api_client = None
line_bot_api = None
parser = None
gemini_client = None
configuration = None


def _validate_supabase_env() -> list[str]:
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if url or key:
        if not (url and key):
            return ['SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must both be set when either is present']
    return []


def _init_webhook_state() -> list[str]:
    global configuration, parser, gemini_client

    missing = require_env_vars(WEBHOOK_REQUIRED_VARS)
    if missing:
        return missing

    supabase_missing = _validate_supabase_env()
    if supabase_missing:
        return supabase_missing

    channel_secret = os.getenv('LINE_CHANNEL_SECRET')
    channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    gemini_api_key = os.getenv('GEMINI_API_KEY')

    configuration = Configuration(access_token=channel_access_token)
    parser = WebhookParser(channel_secret)
    gemini_client = create_gemini_client(api_key=gemini_api_key)
    return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global async_api_client, line_bot_api

    missing = _init_webhook_state()
    if missing:
        print('Missing required environment variables:', ', '.join(missing))
        sys.exit(1)

    async_api_client = AsyncApiClient(configuration)
    line_bot_api = AsyncMessagingApi(async_api_client)
    yield
    if async_api_client is not None:
        await async_api_client.close()


app = FastAPI(lifespan=lifespan)

_startup_missing = _init_webhook_state()
if not _startup_missing:
    logger.debug('Webhook clients initialized at import time')


async def _fetch_image_bytes(message_id: str) -> bytes:
    if async_api_client is None:
        raise RuntimeError('Async LINE API client is not initialized')

    blob_api = AsyncMessagingApiBlob(async_api_client)
    result = blob_api.get_message_content(message_id)
    if __import__('inspect').isawaitable(result):
        result = await result
    elif not isinstance(result, (bytes, bytearray)):
        result = await __import__('asyncio').to_thread(blob_api.get_message_content, message_id)

    if isinstance(result, (bytes, bytearray)):
        return bytes(result)
    raise RuntimeError('Unable to fetch image bytes from LINE message content')


def _extract_sent_message_id(response) -> Optional[str]:
    sent_messages = getattr(response, 'sent_messages', None) or getattr(response, 'sentMessages', None)
    if not sent_messages:
        return None
    first = sent_messages[0]
    message_id = getattr(first, 'id', None)
    if isinstance(message_id, str) and message_id.strip():
        return message_id.strip()
    return None


async def _resolve_reply_language(line_user_id: Optional[str], user_text: Optional[str] = None) -> str:
    if line_user_id:
        profile_language = await fetch_line_profile_language(line_bot_api, line_user_id)
        maybe_update_from_line_profile(line_user_id, profile_language)
    return resolve_reply_language(line_user_id, user_text)


def _localized_for_tenant(tenant: Optional[TenantContext], builder):
    with persona_scope(resolve_persona_for_tenant(tenant)):
        return builder()


async def _reply_and_save_confirmation(
    reply_token: str,
    bot_reply: BotReply,
    *,
    tenant: Optional[TenantContext],
    line_user_id: Optional[str],
    source_message_id: Optional[str],
    failure_original_message_id: Optional[str] = None,
    failure_original_line_user_id: Optional[str] = None,
) -> None:
    response = await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=bot_reply.text)],
        )
    )
    bot_message_id = _extract_sent_message_id(response)
    if bot_reply.confirmation and bot_message_id:
        save_confirmation(
            bot_message_id=bot_message_id,
            tenant=bot_reply.confirmation.tenant,
            confirmation_text=bot_reply.confirmation.confirmation_text,
            items=list(bot_reply.confirmation.items),
        )
    anchor_original_message_id = failure_original_message_id or source_message_id
    anchor_original_line_user_id = failure_original_line_user_id or line_user_id
    if (
        bot_reply.retryable_failure
        and bot_message_id
        and tenant
        and anchor_original_line_user_id
        and anchor_original_message_id
    ):
        save_failure_retry_anchor(
            bot_error_message_id=bot_message_id,
            original_message_id=anchor_original_message_id,
            original_line_user_id=anchor_original_line_user_id,
            tenant=tenant,
            failure_kind=bot_reply.retryable_failure,
        )


async def _reply_text(reply_token: str, reply_text: str) -> None:
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=reply_text)],
        )
    )


@app.post("/callback")
async def handle_callback(request: Request):
    signature = request.headers.get('X-Line-Signature', '')

    body_bytes = await request.body()
    body = body_bytes.decode('utf-8', errors='replace')

    logger.info('Received LINE webhook request: %d bytes', len(body_bytes))

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        logger.warning('Invalid LINE signature')
        raise HTTPException(status_code=400, detail='Invalid signature')

    for event in events:
        if not isinstance(event, MessageEvent):
            logger.debug('Ignoring non-message event: %s', type(event).__name__)
            continue

        user_text = extract_text_message(event)
        image_message_id = extract_image_message_id(event)
        line_user_id = extract_line_user_id(event)
        source_message_id = extract_source_message_id(event)
        quoted_message_id = extract_quoted_message_id(event)

        tenant = resolve_tenant_from_event(event, line_user_id) if line_user_id else None
        if tenant is None and line_user_id:
            tenant = TenantContext.personal(line_user_id)

        reply_language = await _resolve_reply_language(line_user_id, user_text)

        logged_by_display_name = None
        chat_display_name = None
        if tenant and tenant.is_shared and line_user_id:
            logged_by_display_name = await fetch_line_display_name(line_bot_api, tenant, line_user_id)
            chat_display_name = await fetch_chat_display_name(line_bot_api, tenant)

        message_context = None
        if tenant and source_message_id:
            message_context = MessageContext(
                tenant=tenant,
                source_message_id=source_message_id,
                reply_language=reply_language,
                logged_by_display_name=logged_by_display_name,
            )

        if user_text:
            if quoted_message_id and tenant and source_message_id and line_user_id:
                confirmation = get_confirmation_by_bot_message_id(quoted_message_id, tenant)
                if confirmation is not None:
                    reply_context = ReplyContext(
                        tenant=tenant,
                        user_reply_message_id=source_message_id,
                        quoted_bot_message_id=quoted_message_id,
                        reply_language=reply_language,
                    )
                    usage_prep = prepare_inbound_usage(
                        tenant,
                        line_user_id,
                        source_message_id,
                        reply_language=reply_language,
                        text=user_text,
                        chat_display_name=chat_display_name,
                    )
                    if not usage_prep.allowed:
                        await _reply_text(
                            event.reply_token,
                            _localized_for_tenant(
                                tenant,
                                lambda: format_denial_reply(reply_language, usage_prep.reason),
                            ),
                        )
                        continue
                    with usage_billing_scope(usage_prep.billing_context):
                        try:
                            edit_result = await process_reply_edit(user_text, reply_context, gemini_client)
                        except UserUsageLimitExceeded as exc:
                            edit_result = ReplyEditResult(text=str(exc))
                    response = await line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=edit_result.text)],
                        )
                    )
                    if edit_result.anchor_reply_to_sent_message and edit_result.confirmation_id:
                        prompt_message_id = _extract_sent_message_id(response)
                        if prompt_message_id:
                            update_interaction_bot_message_id(
                                edit_result.confirmation_id,
                                prompt_message_id,
                            )
                    continue

                if is_retry_intent(user_text):
                    if not try_mark_reply_processed(tenant, source_message_id):
                        await _reply_text(
                            event.reply_token,
                            _localized_for_tenant(
                                tenant,
                                lambda: format_duplicate_reply(reply_language),
                            ),
                        )
                        continue

                    retry_context = RetryContext(
                        tenant=tenant,
                        retry_reply_message_id=source_message_id,
                        bot_error_message_id=quoted_message_id,
                        reply_language=reply_language,
                    )
                    usage_prep = prepare_inbound_usage(
                        tenant,
                        line_user_id,
                        source_message_id,
                        reply_language=reply_language,
                        text=user_text,
                        chat_display_name=chat_display_name,
                    )
                    if not usage_prep.allowed:
                        await _reply_text(
                            event.reply_token,
                            _localized_for_tenant(
                                tenant,
                                lambda: format_denial_reply(reply_language, usage_prep.reason),
                            ),
                        )
                        continue

                    anchor = get_failure_retry_anchor(quoted_message_id, tenant)
                    original_display_name = None
                    if anchor is not None and tenant.is_shared:
                        original_display_name = await fetch_line_display_name(
                            line_bot_api,
                            TenantContext(
                                tenant_type=anchor.tenant_type,
                                tenant_id=anchor.tenant_id,
                                logged_by_line_user_id=anchor.original_line_user_id,
                            ),
                            anchor.original_line_user_id,
                        )

                    with usage_billing_scope(usage_prep.billing_context):
                        bot_reply = await process_message_retry(
                            retry_context,
                            gemini_client,
                            _fetch_image_bytes,
                            logged_by_display_name=original_display_name,
                        )
                    if bot_reply.text == retry_not_found_reply(reply_language):
                        await _reply_text(event.reply_token, bot_reply.text)
                        continue
                    await _reply_and_save_confirmation(
                        event.reply_token,
                        bot_reply,
                        tenant=tenant,
                        line_user_id=line_user_id,
                        source_message_id=source_message_id,
                        failure_original_message_id=anchor.original_message_id if anchor else None,
                        failure_original_line_user_id=anchor.original_line_user_id if anchor else None,
                    )
                    continue

            if tenant and line_user_id and source_message_id:
                save_inbound_text_message(
                    message_id=source_message_id,
                    line_user_id=line_user_id,
                    tenant=tenant,
                    text_content=user_text,
                )
                usage_prep = prepare_inbound_usage(
                    tenant,
                    line_user_id,
                    source_message_id,
                    reply_language=reply_language,
                    text=user_text,
                    chat_display_name=chat_display_name,
                )
                if not usage_prep.allowed:
                    await _reply_text(
                        event.reply_token,
                        _localized_for_tenant(
                            tenant,
                            lambda: format_denial_reply(reply_language, usage_prep.reason),
                        ),
                    )
                    continue
                with usage_billing_scope(usage_prep.billing_context):
                    bot_reply = await process_text_message(user_text, gemini_client, message_context)
            else:
                bot_reply = await process_text_message(user_text, gemini_client, message_context)
            await _reply_and_save_confirmation(
                event.reply_token,
                bot_reply,
                tenant=tenant,
                line_user_id=line_user_id,
                source_message_id=source_message_id,
            )
            continue

        if image_message_id:
            if tenant and line_user_id and source_message_id:
                save_inbound_image_message(
                    message_id=source_message_id,
                    line_user_id=line_user_id,
                    tenant=tenant,
                )
            try:
                image_bytes = await _fetch_image_bytes(image_message_id)
            except Exception:
                logger.exception('Image fetch failed')
                error_reply = BotReply(
                    text=_localized_for_tenant(
                        tenant,
                        lambda: error_reply_text(reply_language),
                    ),
                    retryable_failure='image_fetch_error',
                )
                await _reply_and_save_confirmation(
                    event.reply_token,
                    error_reply,
                    tenant=tenant,
                    line_user_id=line_user_id,
                    source_message_id=source_message_id,
                )
                continue

            if tenant and line_user_id and source_message_id:
                usage_prep = prepare_inbound_usage(
                    tenant,
                    line_user_id,
                    source_message_id,
                    reply_language=reply_language,
                    image_bytes=image_bytes,
                    chat_display_name=chat_display_name,
                )
                if not usage_prep.allowed:
                    await _reply_text(
                        event.reply_token,
                        _localized_for_tenant(
                            tenant,
                            lambda: format_denial_reply(reply_language, usage_prep.reason),
                        ),
                    )
                    continue
                with usage_billing_scope(usage_prep.billing_context):
                    bot_reply = await process_image_message(image_bytes, gemini_client, context=message_context)
            else:
                bot_reply = await process_image_message(image_bytes, gemini_client, context=message_context)

            await _reply_and_save_confirmation(
                event.reply_token,
                bot_reply,
                tenant=tenant,
                line_user_id=line_user_id,
                source_message_id=source_message_id,
            )
            continue

        logger.info('Unsupported or empty message event received')
        unsupported_language = await _resolve_reply_language(line_user_id)
        unsupported_text = _localized_for_tenant(
            tenant,
            lambda: canned_unsupported_reply(unsupported_language),
        )
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=unsupported_text)]
            )
        )

    return 'OK'
