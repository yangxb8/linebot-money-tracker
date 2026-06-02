import asyncio
import logging
import os
from typing import Optional

from google import genai

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
        self.client = genai.Client(api_key=self.api_key)

    async def generate_reply(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        logger.debug("Sending request to Gemini API with prompt: %s", prompt[:50])
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
            )
            logger.debug("Gemini response status: success")
            text = response.text
            if not text or not text.strip():
                raise RuntimeError("Gemini returned an empty response.")
            return text.strip()
        except Exception as exc:
            logger.exception("Gemini API call failed")
            raise RuntimeError("Unable to generate response from Gemini API") from exc
