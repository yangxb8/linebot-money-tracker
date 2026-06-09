import asyncio
import logging
import os
from typing import Any, Dict, Optional

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from services.log_utils import describe_bytes, truncate

logger = logging.getLogger(__name__)

GEMINI_MODEL = 'gemini-2.5-flash'
GEMINI_RECEIPT_IMAGE_MODEL = 'gemini-2.5-pro'
GEMINI_MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, (ServerError, ClientError)):
        return getattr(exc, 'code', None) in RETRYABLE_STATUS_CODES
    return False


def _retry_delay_seconds(attempt: int) -> float:
    # attempt is 1-based for the failed try; backoff: 1s, 2s, 4s (capped at 8s)
    return min(2 ** (attempt - 1), 8)


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
        self.client = genai.Client(api_key=self.api_key)

    async def _generate_content_with_retry(
        self,
        *,
        label: str,
        contents: Any,
        context: str = '',
        config: Optional[types.GenerateContentConfig] = None,
        model: Optional[str] = None,
    ) -> str:
        resolved_model = model or GEMINI_MODEL
        max_attempts = GEMINI_MAX_RETRIES + 1
        last_exc: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                kwargs: Dict[str, Any] = {
                    'model': resolved_model,
                    'contents': contents,
                }
                if config is not None:
                    kwargs['config'] = config
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    **kwargs,
                )
                text = response.text
                if not text or not text.strip():
                    logger.warning('Gemini %s response was empty%s', label, context)
                    raise RuntimeError("Gemini returned an empty response.")
                text = text.strip()
                if attempt > 1:
                    logger.info(
                        'Gemini %s succeeded on attempt %d/%d',
                        label,
                        attempt,
                        max_attempts,
                    )
                logger.info('Gemini %s response: len=%d', label, len(text))
                logger.debug('Gemini %s response body: %s', label, truncate(text, 1000))
                return text
            except RuntimeError:
                raise
            except Exception as exc:
                last_exc = exc
                if _is_retryable_error(exc) and attempt < max_attempts:
                    delay = _retry_delay_seconds(attempt)
                    logger.warning(
                        'Gemini %s call failed (attempt %d/%d)%s: %s; retrying in %.1fs',
                        label,
                        attempt,
                        max_attempts,
                        context,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                logger.exception(
                    'Gemini %s API call failed (attempt %d/%d)%s: model=%s',
                    label,
                    attempt,
                    max_attempts,
                    context,
                    resolved_model,
                )
                raise RuntimeError("Unable to generate response from Gemini API") from exc

        raise RuntimeError("Unable to generate response from Gemini API") from last_exc

    async def generate_reply(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        logger.info(
            'Gemini text request: model=%s prompt_len=%d max_retries=%d',
            GEMINI_MODEL,
            len(prompt),
            GEMINI_MAX_RETRIES,
        )
        logger.debug('Gemini text prompt: %s', truncate(prompt, 1000))
        return await self._generate_content_with_retry(label='text', contents=prompt)

    async def generate_json_reply(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        logger.info(
            'Gemini JSON request: model=%s prompt_len=%d max_retries=%d',
            GEMINI_MODEL,
            len(prompt),
            GEMINI_MAX_RETRIES,
        )
        logger.debug('Gemini JSON prompt: %s', truncate(prompt, 1000))
        config = types.GenerateContentConfig(response_mime_type='application/json')
        return await self._generate_content_with_retry(
            label='json',
            contents=prompt,
            config=config,
        )

    async def generate_json_reply_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")
        if not image_bytes:
            raise ValueError("Image bytes cannot be empty.")

        context = f' image={describe_bytes(image_bytes)} mime={mime_type}'
        logger.info(
            'Gemini receipt image JSON request: model=%s image=%s mime=%s prompt_len=%d max_retries=%d',
            GEMINI_RECEIPT_IMAGE_MODEL,
            describe_bytes(image_bytes),
            mime_type,
            len(prompt),
            GEMINI_MAX_RETRIES,
        )
        logger.debug('Gemini receipt image JSON prompt: %s', truncate(prompt, 1000))
        config = types.GenerateContentConfig(response_mime_type='application/json')
        return await self._generate_content_with_retry(
            label='receipt-image-json',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt.strip(),
            ],
            context=context,
            config=config,
            model=GEMINI_RECEIPT_IMAGE_MODEL,
        )

    async def generate_reply_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")
        if not image_bytes:
            raise ValueError("Image bytes cannot be empty.")

        context = f' image={describe_bytes(image_bytes)} mime={mime_type}'
        logger.info(
            'Gemini multimodal request: model=%s image=%s mime=%s prompt_len=%d max_retries=%d',
            GEMINI_MODEL,
            describe_bytes(image_bytes),
            mime_type,
            len(prompt),
            GEMINI_MAX_RETRIES,
        )
        logger.debug('Gemini multimodal prompt: %s', truncate(prompt, 1000))
        return await self._generate_content_with_retry(
            label='multimodal',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt.strip(),
            ],
            context=context,
        )
