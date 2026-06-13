import json
import logging
from typing import Optional

from services.gemini_client import GeminiClient
from services.log_utils import describe_bytes, truncate

logger = logging.getLogger(__name__)

TEXT_INTENT_PROMPT = """You judge whether a LINE chat message is the user trying to log an expense.
Accept: expense descriptions with amounts, receipt summaries, payment notes like "paid X for Y", spending logs.
Accept terse Japanese/Chinese shorthand where a number is the amount spent and following text is the place or category (e.g. "861便利店" = 861 yen at a convenience store, "1200ランチ" = lunch 1200 yen).
Reject: greetings, chitchat, jokes, requests for other features.
Reject: general knowledge or informational questions about brands, companies, stores, or places — even if the message contains numbers (e.g. asking what "861便利店" is as a company).
When unsure, prefer false — this bot only logs expenses, it does not answer questions.
Reply ONLY with JSON: {{"is_expense": true}} or {{"is_expense": false}}

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


async def is_expense_intent_text(text: Optional[str], gemini: GeminiClient) -> bool:
    """Use the LLM to judge whether a text message is an expense logging request."""
    if not text or not isinstance(text, str):
        logger.info('Intent check (text): skipped (empty or invalid input)')
        return False

    normalized = text.strip()
    if not normalized:
        logger.info('Intent check (text): skipped (blank after strip)')
        return False

    logger.info('Intent check (text): classifying message len=%d', len(normalized))
    logger.debug('Intent check (text): message=%s', truncate(normalized, 500))
    prompt = TEXT_INTENT_PROMPT.format(text=normalized)
    response = await gemini.generate_reply(prompt)
    return _parse_intent_response(response, source='text')


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
    response = await gemini.generate_reply_with_image(
        IMAGE_INTENT_PROMPT,
        image_bytes,
        mime_type,
    )
    return _parse_intent_response(response, source='image')
