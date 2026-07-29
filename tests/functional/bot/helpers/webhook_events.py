"""LINE webhook JSON event builders for functional tests."""

from __future__ import annotations

import json
from typing import Any, Optional


def text_message_event(
    text: str,
    *,
    user_id: str = "U4af4980629",
    message_id: str = "msg-1",
    reply_token: str = "reply-token-1",
    quoted_message_id: Optional[str] = None,
    timestamp: int = 1462629479859,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "id": message_id,
        "type": "text",
        "quoteToken": "qt",
        "text": text,
    }
    if quoted_message_id:
        message["quotedMessageId"] = quoted_message_id

    return {
        "type": "message",
        "mode": "active",
        "timestamp": timestamp,
        "source": {"type": "user", "userId": user_id},
        "webhookEventId": "01GXXXXXXXXXXXX",
        "deliveryContext": {"isRedelivery": False},
        "replyToken": reply_token,
        "message": message,
    }


def webhook_body(*events: dict[str, Any], destination: str = "Udestination") -> bytes:
    payload = {"destination": destination, "events": list(events)}
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")
