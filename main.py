# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
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
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from services.gemini_client import GeminiClient
from services.line_event import extract_text_message


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


# get LINE channel credentials and Gemini API settings from environment variables
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
gemini_api_key = os.getenv('GEMINI_API_KEY', None)
gemini_api_url = os.getenv('GEMINI_API_URL', None)

missing_env = []
if channel_secret is None:
    missing_env.append('LINE_CHANNEL_SECRET')
if channel_access_token is None:
    missing_env.append('LINE_CHANNEL_ACCESS_TOKEN')
if gemini_api_key is None:
    missing_env.append('GEMINI_API_KEY')
if gemini_api_url is None:
    missing_env.append('GEMINI_API_URL')

if missing_env:
    print('Missing required environment variables:', ', '.join(missing_env))
    sys.exit(1)

configuration = Configuration(
    access_token=channel_access_token
)

async_api_client = None
line_bot_api = None
parser = WebhookParser(channel_secret)
gemini_client = GeminiClient(api_key=gemini_api_key, api_url=gemini_api_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global async_api_client, line_bot_api
    async_api_client = AsyncApiClient(configuration)
    line_bot_api = AsyncMessagingApi(async_api_client)
    yield
    if async_api_client is not None:
        await async_api_client.close()


app = FastAPI(lifespan=lifespan)


FALLBACK_TEXT = (
    "I can only respond to text messages for now. "
    "Please send a text message and I will reply using Gemini."
)
ERROR_REPLY_TEXT = (
    "Sorry, I couldn't generate a response right now. "
    "Please try again in a moment."
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
        if not user_text:
            logger.info('Unsupported or empty message event received')
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=FALLBACK_TEXT)]
                )
            )
            continue

        logger.info('Processing text message from LINE event')
        logger.debug('User text: %s', user_text)

        try:
            reply_text = await gemini_client.generate_reply(user_text)
            logger.info('Gemini reply generated successfully')
        except Exception:
            logger.exception('Gemini generation failed')
            reply_text = ERROR_REPLY_TEXT

        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

    return 'OK'
