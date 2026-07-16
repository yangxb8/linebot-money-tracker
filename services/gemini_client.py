import asyncio
import logging
import os
from typing import Any, Dict, Optional, Sequence, Tuple

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from services.log_utils import describe_bytes, truncate

logger = logging.getLogger(__name__)

GEMINI_MODEL = 'gemini-3.5-flash'
GEMINI_3_FLASH_MODEL = 'gemini-3-flash-preview'
GEMINI_GENERAL_MODEL_FALLBACK_CHAIN: Tuple[str, ...] = (
    'gemini-3.5-flash',
    GEMINI_3_FLASH_MODEL,
    'gemini-2.5-flash',
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash-lite',
)
# Receipt vision uses the same quota-fallback chain (starts at 3.5 flash).
GEMINI_RECEIPT_IMAGE_MODEL_FALLBACK_CHAIN = GEMINI_GENERAL_MODEL_FALLBACK_CHAIN
GEMINI_MAX_RETRIES = 3
SERVER_RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})


class GeminiUsageLimitError(RuntimeError):
    """Gemini quota/rate limit reached with no viable model fallback."""


def _api_error_code(exc: Exception) -> Optional[int]:
    if isinstance(exc, (ServerError, ClientError)):
        return getattr(exc, 'code', None)
    return None


def _is_quota_error(exc: Exception) -> bool:
    return _api_error_code(exc) == 429


def _is_retryable_server_error(exc: Exception) -> bool:
    return _api_error_code(exc) in SERVER_RETRYABLE_STATUS_CODES


def _retry_delay_seconds(attempt: int) -> float:
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
        models: Optional[Sequence[str]] = None,
        allow_quota_model_fallback: bool = True,
    ) -> str:
        model_chain = tuple(models) if models else (GEMINI_MODEL,)
        last_exc: Optional[Exception] = None

        for model_index, resolved_model in enumerate(model_chain):
            max_attempts = GEMINI_MAX_RETRIES + 1
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
                    if model_index > 0 or attempt > 1:
                        logger.info(
                            'Gemini %s succeeded with model=%s (model_try=%d attempt=%d)',
                            label,
                            resolved_model,
                            model_index + 1,
                            attempt,
                        )
                    logger.info('Gemini %s response: len=%d model=%s', label, len(text), resolved_model)
                    logger.debug('Gemini %s response body: %s', label, truncate(text, 1000))
                    return text
                except RuntimeError:
                    raise
                except Exception as exc:
                    last_exc = exc
                    if _is_quota_error(exc):
                        logger.warning(
                            'Gemini %s quota exceeded for model=%s%s',
                            label,
                            resolved_model,
                            context,
                        )
                        break

                    if _is_retryable_server_error(exc) and attempt < max_attempts:
                        delay = _retry_delay_seconds(attempt)
                        logger.warning(
                            'Gemini %s call failed (model=%s attempt %d/%d)%s: %s; retrying in %.1fs',
                            label,
                            resolved_model,
                            attempt,
                            max_attempts,
                            context,
                            exc,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue

                    logger.exception(
                        'Gemini %s API call failed (model=%s attempt %d/%d)%s',
                        label,
                        resolved_model,
                        attempt,
                        max_attempts,
                        context,
                    )
                    raise RuntimeError("Unable to generate response from Gemini API") from exc

            if not allow_quota_model_fallback:
                raise GeminiUsageLimitError(
                    f'Gemini usage limit reached for {label} (model={resolved_model})'
                ) from last_exc

            if model_index < len(model_chain) - 1:
                next_model = model_chain[model_index + 1]
                logger.info(
                    'Gemini %s switching model after quota: %s -> %s',
                    label,
                    resolved_model,
                    next_model,
                )
                continue

        raise GeminiUsageLimitError(
            f'Gemini usage limit reached for {label} after trying {len(model_chain)} model(s)'
        ) from last_exc

    async def generate_reply(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        logger.info(
            'Gemini text request: models=%s prompt_len=%d max_retries=%d',
            GEMINI_GENERAL_MODEL_FALLBACK_CHAIN,
            len(prompt),
            GEMINI_MAX_RETRIES,
        )
        logger.debug('Gemini text prompt: %s', truncate(prompt, 1000))
        return await self._generate_content_with_retry(
            label='text',
            contents=prompt,
            models=GEMINI_GENERAL_MODEL_FALLBACK_CHAIN,
        )

    async def generate_json_reply(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        logger.info(
            'Gemini JSON request: models=%s prompt_len=%d max_retries=%d',
            GEMINI_GENERAL_MODEL_FALLBACK_CHAIN,
            len(prompt),
            GEMINI_MAX_RETRIES,
        )
        logger.debug('Gemini JSON prompt: %s', truncate(prompt, 1000))
        config = types.GenerateContentConfig(response_mime_type='application/json')
        return await self._generate_content_with_retry(
            label='json',
            contents=prompt,
            config=config,
            models=GEMINI_GENERAL_MODEL_FALLBACK_CHAIN,
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
            'Gemini receipt image JSON request: models=%s image=%s mime=%s prompt_len=%d',
            GEMINI_RECEIPT_IMAGE_MODEL_FALLBACK_CHAIN,
            describe_bytes(image_bytes),
            mime_type,
            len(prompt),
        )
        logger.debug('Gemini receipt image JSON prompt: %s', truncate(prompt, 1000))
        # Long grocery receipts need headroom for full line-item JSON.
        config = types.GenerateContentConfig(
            response_mime_type='application/json',
            max_output_tokens=8192,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        return await self._generate_content_with_retry(
            label='receipt-image-json',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt.strip(),
            ],
            context=context,
            config=config,
            models=GEMINI_RECEIPT_IMAGE_MODEL_FALLBACK_CHAIN,
            allow_quota_model_fallback=True,
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
            'Gemini multimodal request: models=%s image=%s mime=%s prompt_len=%d',
            GEMINI_GENERAL_MODEL_FALLBACK_CHAIN,
            describe_bytes(image_bytes),
            mime_type,
            len(prompt),
        )
        logger.debug('Gemini multimodal prompt: %s', truncate(prompt, 1000))
        return await self._generate_content_with_retry(
            label='multimodal',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt.strip(),
            ],
            context=context,
            models=GEMINI_GENERAL_MODEL_FALLBACK_CHAIN,
        )
