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

from services.confirmation_repository import save_confirmation
from services.env_loader import load_env, require_env_vars
from services.gemini_client import GeminiClient
from services.line_event import (
    extract_image_message_id,
    extract_line_user_id,
    extract_quoted_message_id,
    extract_source_message_id,
    extract_text_message,
)
from services.tenant_context import resolve_tenant_from_event
from services.message_context import BotReply, MessageContext, ReplyContext
from services.message_handler import (
    CANNED_UNSUPPORTED_REPLY,
    ERROR_REPLY_TEXT,
    process_image_message,
    process_reply_edit,
    process_text_message,
)

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
    gemini_client = GeminiClient(api_key=gemini_api_key)
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


async def _reply_and_save_confirmation(
    reply_token: str,
    reply_text: str,
    confirmation_payload,
) -> None:
    response = await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=reply_text)],
        )
    )
    bot_message_id = _extract_sent_message_id(response)
    if confirmation_payload and bot_message_id:
        save_confirmation(
            bot_message_id=bot_message_id,
            tenant=confirmation_payload.tenant,
            confirmation_text=confirmation_payload.confirmation_text,
            items=list(confirmation_payload.items),
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

        message_context = None
        if tenant and source_message_id:
            message_context = MessageContext(
                tenant=tenant,
                source_message_id=source_message_id,
            )

        if user_text:
            if quoted_message_id and tenant and source_message_id:
                reply_context = ReplyContext(
                    tenant=tenant,
                    user_reply_message_id=source_message_id,
                    quoted_bot_message_id=quoted_message_id,
                )
                reply_text = await process_reply_edit(user_text, reply_context, gemini_client)
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply_text)],
                    )
                )
                continue

            bot_reply = await process_text_message(user_text, gemini_client, message_context)
            await _reply_and_save_confirmation(
                event.reply_token,
                bot_reply.text,
                bot_reply.confirmation,
            )
            continue

        if image_message_id:
            try:
                image_bytes = await _fetch_image_bytes(image_message_id)
                bot_reply = await process_image_message(image_bytes, gemini_client, context=message_context)
            except Exception:
                logger.exception('Image fetch failed')
                bot_reply = BotReply(text=ERROR_REPLY_TEXT)

            await _reply_and_save_confirmation(
                event.reply_token,
                bot_reply.text,
                bot_reply.confirmation,
            )
            continue

        logger.info('Unsupported or empty message event received')
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=CANNED_UNSUPPORTED_REPLY)]
            )
        )

    return 'OK'
