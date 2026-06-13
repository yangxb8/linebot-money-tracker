"""Gemini client wrapper that records per-user LLM usage."""

from __future__ import annotations

import logging
from typing import Optional

from services.gemini_client import GeminiClient, GeminiUsageLimitError
from services.usage_limiter import check_billing_headroom_for_operation, format_denial_reply
from services.usage_metering import get_billing_context, get_llm_operation_type
from services.usage_repository import is_usage_tracking_enabled, record_llm_backed_message, record_llm_usage

logger = logging.getLogger(__name__)

_LABEL_TO_OPERATION = {
    'text': 'general',
    'json': 'general',
    'receipt-image-json': 'receipt_analysis',
    'multimodal': 'general',
}


class UserUsageLimitExceeded(GeminiUsageLimitError):
    """Per-user quota exhausted mid-flow."""


class MeteredGeminiClient(GeminiClient):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key)

    def _resolve_operation_type(self, label: str) -> str:
        scoped = get_llm_operation_type()
        if scoped != 'general':
            return scoped
        return _LABEL_TO_OPERATION.get(label, 'general')

    async def _after_success(self, label: str, text: str) -> str:
        billing = get_billing_context()
        if billing is None or not is_usage_tracking_enabled():
            return text

        operation_type = self._resolve_operation_type(label)
        deny = check_billing_headroom_for_operation(billing, operation_type)
        if deny is not None:
            raise UserUsageLimitExceeded(format_denial_reply(billing.reply_language, deny))

        if not billing.message_window_recorded and billing.source_message_id:
            record_llm_backed_message(billing.sender_line_user_id, billing.source_message_id)
            billing.message_window_recorded = True

        record_llm_usage(
            charged_line_user_id=billing.billing_line_user_id,
            sender_line_user_id=billing.sender_line_user_id,
            operation_type=operation_type,
            operation_label=label,
            source_message_id=billing.source_message_id,
            tenant_type=billing.tenant_type,
            tenant_id=billing.tenant_id,
            pooled=billing.pooled,
        )
        return text

    async def generate_reply(self, prompt: str) -> str:
        text = await super().generate_reply(prompt)
        return await self._after_success('text', text)

    async def generate_json_reply(self, prompt: str) -> str:
        text = await super().generate_json_reply(prompt)
        return await self._after_success('json', text)

    async def generate_json_reply_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = 'image/jpeg',
    ) -> str:
        text = await super().generate_json_reply_with_image(prompt, image_bytes, mime_type)
        return await self._after_success('receipt-image-json', text)

    async def generate_reply_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = 'image/jpeg',
    ) -> str:
        text = await super().generate_reply_with_image(prompt, image_bytes, mime_type)
        return await self._after_success('multimodal', text)


def create_gemini_client(api_key: Optional[str] = None):
    if is_usage_tracking_enabled():
        return MeteredGeminiClient(api_key=api_key)
    return GeminiClient(api_key=api_key)
