import json
import logging
from typing import Optional

from services.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

TEXT_INTENT_PROMPT = """You judge whether a LINE chat message is the user trying to log an expense.
Accept: expense descriptions with amounts, receipt summaries, payment notes like "paid X for Y", spending logs.
Reject: greetings, chitchat, unrelated questions, jokes, requests for other features.
Reply ONLY with JSON: {{"is_expense": true}} or {{"is_expense": false}}

Message:
{text}"""

IMAGE_INTENT_PROMPT = """You judge whether this image is something the user sent to log an expense.
Accept: receipts, invoices, bills, payment confirmations, itemized purchase photos.
Reject: personal photos, memes, pets, landscapes, selfies, unrelated screenshots.
Reply ONLY with JSON: {"is_expense": true} or {"is_expense": false}"""


def _parse_intent_response(response: str) -> bool:
    text = response.strip()
    if not text:
        return False

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return bool(data.get('is_expense', False))
    except json.JSONDecodeError:
        pass

    lowered = text.lower()
    if '"is_expense": true' in lowered or '"is_expense":true' in lowered:
        return True
    if '"is_expense": false' in lowered or '"is_expense":false' in lowered:
        return False

    logger.debug('Intent response was not valid JSON: %s', text[:100])
    return False


async def is_expense_intent_text(text: Optional[str], gemini: GeminiClient) -> bool:
    """Use the LLM to judge whether a text message is an expense logging request."""
    if not text or not isinstance(text, str):
        return False

    normalized = text.strip()
    if not normalized:
        return False

    prompt = TEXT_INTENT_PROMPT.format(text=normalized)
    response = await gemini.generate_reply(prompt)
    return _parse_intent_response(response)


async def is_expense_intent_image(
    image_bytes: bytes,
    gemini: GeminiClient,
    mime_type: str = 'image/jpeg',
) -> bool:
    """Use the LLM to judge whether an image is a receipt or expense document."""
    if not image_bytes:
        return False

    response = await gemini.generate_reply_with_image(
        IMAGE_INTENT_PROMPT,
        image_bytes,
        mime_type,
    )
    return _parse_intent_response(response)
