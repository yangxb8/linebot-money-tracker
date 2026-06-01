import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10.0


class GeminiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.api_url = api_url or os.getenv("GEMINI_API_URL")
        self.timeout = timeout

    async def generate_reply(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        if not self.api_key or not self.api_url:
            raise RuntimeError("Gemini API configuration is missing.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "max_output_tokens": 256,
            "temperature": 0.7,
        }

        logger.debug("Sending Gemini request to %s", self.api_url)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            logger.debug("Gemini response payload: %s", data)
            text = self._extract_text(data)
            if not text:
                raise RuntimeError("Gemini returned an unexpected response format.")
            return text
        except httpx.RequestError as exc:
            logger.exception("Gemini request failed")
            raise RuntimeError("Unable to reach Gemini API") from exc
        except httpx.HTTPStatusError as exc:
            logger.exception("Gemini API returned an error status")
            raise RuntimeError(
                f"Gemini API error: {exc.response.status_code}"
            ) from exc

    @staticmethod
    def _extract_text(data: Any) -> Optional[str]:
        if isinstance(data, dict):
            for key in ("text", "reply", "message", "result"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            # Handle common nested response shapes
            if isinstance(data.get("output"), dict):
                output = data["output"]
                if isinstance(output.get("text"), str) and output["text"].strip():
                    return output["text"].strip()

        return None
