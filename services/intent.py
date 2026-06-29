import json
import logging
from typing import Literal, Optional

from services.gemini_client import GeminiClient
from services.log_utils import describe_bytes, truncate
from services.usage_metering import llm_operation_scope

logger = logging.getLogger(__name__)

TextMessageIntent = Literal['expense', 'webapp', 'other']

COMBINED_TEXT_INTENT_PROMPT = """You classify a LINE chat message into exactly one intent.

Intents:
- expense: user is trying to log spending (amounts, receipts, payment notes, terse JP/CN shorthand like "861便利店" or "1200ランチ")
- webapp: user wants the expense dashboard / web app / webpage link to view logged expenses online (e.g. "open dashboard", "where is the website?", "家計簿のページ", "网页在哪", "how can I see my expenses online?")
- other: greetings, chitchat, jokes, general knowledge, unsupported requests

Rules:
- Prefer expense when the message looks like logging spending.
- Prefer webapp when clearly asking for the dashboard or web link, not logging.
- Prefer other when unsure about expense or webapp; this bot does not answer general questions.
- Reject general knowledge about brands/stores even if numbers appear.

Reply ONLY with JSON: {{"intent": "expense"}} or {{"intent": "webapp"}} or {{"intent": "other"}}

Message:
{text}"""

IMAGE_INTENT_PROMPT = """You judge whether this image is something the user sent to log an expense.
Accept: receipts, invoices, bills, payment confirmations, itemized purchase photos.
Reject: personal photos, memes, pets, landscapes, selfies, unrelated screenshots.
Reply ONLY with JSON: {"is_expense": true} or {"is_expense": false}"""


def _parse_intent_response(response: str, source: str = 'unknown') -> bool:
    text = response.strip()
    if not text:
        logger.warning('Intent check (%s): empty LLM response', source)
        return False

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            is_expense = bool(data.get('is_expense', False))
            logger.info('Intent check (%s): is_expense=%s (parsed JSON)', source, is_expense)
            return is_expense
    except json.JSONDecodeError:
        logger.debug('Intent check (%s): response is not JSON, trying fallback parse', source)

    lowered = text.lower()
    if '"is_expense": true' in lowered or '"is_expense":true' in lowered:
        logger.info('Intent check (%s): is_expense=True (fallback string match)', source)
        return True
    if '"is_expense": false' in lowered or '"is_expense":false' in lowered:
        logger.info('Intent check (%s): is_expense=False (fallback string match)', source)
        return False

    logger.warning(
        'Intent check (%s): could not parse response: %s',
        source,
        truncate(text, 200),
    )
    return False


def _parse_combined_intent_response(response: str, source: str = 'unknown') -> TextMessageIntent:
    text = response.strip()
    if not text:
        logger.warning('Combined intent check (%s): empty LLM response', source)
        return 'other'

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            intent = str(data.get('intent', 'other')).strip().lower()
            if intent in ('expense', 'webapp', 'other'):
                logger.info('Combined intent check (%s): intent=%s (parsed JSON)', source, intent)
                return intent  # type: ignore[return-value]
    except json.JSONDecodeError:
        logger.debug('Combined intent check (%s): response is not JSON, trying fallback parse', source)

    lowered = text.lower()
    for candidate in ('expense', 'webapp', 'other'):
        if f'"intent": "{candidate}"' in lowered or f'"intent":"{candidate}"' in lowered:
            logger.info('Combined intent check (%s): intent=%s (fallback string match)', source, candidate)
            return candidate  # type: ignore[return-value]

    logger.warning(
        'Combined intent check (%s): could not parse response: %s',
        source,
        truncate(text, 200),
    )
    return 'other'


async def classify_text_message_intent(
    text: Optional[str],
    gemini: GeminiClient,
) -> TextMessageIntent:
    """Classify text into expense logging, webapp link request, or other."""
    if not text or not isinstance(text, str):
        logger.info('Combined intent check (text): skipped (empty or invalid input)')
        return 'other'

    normalized = text.strip()
    if not normalized:
        logger.info('Combined intent check (text): skipped (blank after strip)')
        return 'other'

    logger.info('Combined intent check (text): classifying message len=%d', len(normalized))
    logger.debug('Combined intent check (text): message=%s', truncate(normalized, 500))
    prompt = COMBINED_TEXT_INTENT_PROMPT.replace('{text}', normalized)
    with llm_operation_scope('intent'):
        response = await gemini.generate_reply(prompt)
    return _parse_combined_intent_response(response, source='text')


async def is_expense_intent_text(text: Optional[str], gemini: GeminiClient) -> bool:
    """Use the LLM to judge whether a text message is an expense logging request."""
    return await classify_text_message_intent(text, gemini) == 'expense'


async def is_expense_intent_image(
    image_bytes: bytes,
    gemini: GeminiClient,
    mime_type: str = 'image/jpeg',
) -> bool:
    """Use the LLM to judge whether an image is a receipt or expense document."""
    if not image_bytes:
        logger.info('Intent check (image): skipped (empty image bytes)')
        return False

    logger.info(
        'Intent check (image): classifying image=%s mime=%s',
        describe_bytes(image_bytes),
        mime_type,
    )
    with llm_operation_scope('intent'):
        response = await gemini.generate_reply_with_image(
            IMAGE_INTENT_PROMPT,
            image_bytes,
            mime_type,
        )
    return _parse_intent_response(response, source='image')
