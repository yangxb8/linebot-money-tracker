# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, softwae
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import logging
import os
import sys
from contextlib import asynccontextmanager

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

from services.ai_assist import assist_parse_ocr
from services.gemini_client import GeminiClient
from services.line_event import extract_image_message_id, extract_text_message
from services.ocr import extract_text_from_image_bytes, _guess_mime_type
from services.receipt_parser import parse_text_for_expenses
from services.intent import is_expense_intent_image, is_expense_intent_text



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


# get LINE channel credentials and Gemini API settings from environment variables
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
gemini_api_key = os.getenv('GEMINI_API_KEY', None)

missing_env = []
if channel_secret is None:
    missing_env.append('LINE_CHANNEL_SECRET')
if channel_access_token is None:
    missing_env.append('LINE_CHANNEL_ACCESS_TOKEN')
if gemini_api_key is None:
    missing_env.append('GEMINI_API_KEY')

if missing_env:
    print('Missing required environment variables:', ', '.join(missing_env))
    sys.exit(1)

configuration = Configuration(
    access_token=channel_access_token
)

async_api_client = None
line_bot_api = None
parser = WebhookParser(channel_secret)
gemini_client = GeminiClient(api_key=gemini_api_key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global async_api_client, line_bot_api
    async_api_client = AsyncApiClient(configuration)
    line_bot_api = AsyncMessagingApi(async_api_client)
    yield
    if async_api_client is not None:
        await async_api_client.close()


app = FastAPI(lifespan=lifespan)


CANNED_UNSUPPORTED_REPLY = (
    "Sorry—I only accept expense submissions right now. Please send a receipt image or a text message like: 'Lunch 120 THB at Cafe'"
)
ERROR_REPLY_TEXT = (
    "Sorry, I couldn't generate a response right now. "
    "Please try again in a moment."
)


def _format_expense_items(items):
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

    return "Detected expense(s):\n" + "\n".join(lines)


async def _fetch_image_bytes(message_id: str) -> bytes:
    if async_api_client is None:
        raise RuntimeError('Async LINE API client is not initialized')

    blob_api = AsyncMessagingApiBlob(async_api_client)

    def fetch():
        return blob_api.get_message_content(message_id)

    result = await __import__('asyncio').to_thread(fetch)
    if isinstance(result, (bytes, bytearray)):
        return bytes(result)
    raise RuntimeError('Unable to fetch image bytes from LINE message content')


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

        if user_text:
            logger.info('Processing text message from LINE event')
            logger.debug('User text: %s', user_text)
            try:
                if await is_expense_intent_text(user_text, gemini_client):
                    items = parse_text_for_expenses(user_text)
                    if items:
                        reply_text = _format_expense_items(items)
                    else:
                        reply_text = await gemini_client.generate_reply(user_text)
                        logger.info('Gemini reply generated successfully')
                else:
                    reply_text = CANNED_UNSUPPORTED_REPLY
            except Exception:
                logger.exception('Processing failed')
                reply_text = ERROR_REPLY_TEXT

            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
            continue

        if image_message_id:
            logger.info('Processing image message from LINE event')
            try:
                image_bytes = await _fetch_image_bytes(image_message_id)
                mime_type = _guess_mime_type(image_bytes)
                if not await is_expense_intent_image(image_bytes, gemini_client, mime_type):
                    reply_text = CANNED_UNSUPPORTED_REPLY
                else:
                    ocr_lines = extract_text_from_image_bytes(image_bytes)
                    ocr_text = "\n".join(ocr_lines)
                    items = parse_text_for_expenses(ocr_text)
                    if not items:
                        items = await assist_parse_ocr(ocr_text, gemini_client)
                    if items:
                        reply_text = _format_expense_items(items)
                    else:
                        reply_text = ERROR_REPLY_TEXT
                    logger.info('Image expense extraction completed')
            except Exception:
                logger.exception('Image processing failed')
                reply_text = ERROR_REPLY_TEXT

            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
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
