#!/usr/bin/env python3
"""Create and set default LINE rich menu pointing to expense dashboard LIFF."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def _post_json(url: str, payload: dict, access_token: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def build_rich_menu_payload(liff_url: str) -> dict:
    return {
        "size": {"width": 2500, "height": 843},
        "selected": True,
        "name": "expense-dashboard-v1",
        "chatBarText": "メニュー",
        "areas": [
            {
                "bounds": {"x": 0, "y": 0, "width": 2500, "height": 843},
                "action": {
                    "type": "uri",
                    "label": "家計簿",
                    "uri": liff_url,
                },
            }
        ],
    }


def main() -> None:
    access_token = _require_env("LINE_CHANNEL_ACCESS_TOKEN")
    liff_url = _require_env("DASHBOARD_LIFF_URL")

    payload = build_rich_menu_payload(liff_url)
    created = _post_json(
        "https://api.line.me/v2/bot/richmenu",
        payload,
        access_token,
    )
    rich_menu_id = created["richMenuId"]
    _post_json(
        f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
        {},
        access_token,
    )
    print(f"Rich menu created and set as default: {rich_menu_id}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"LINE API error: {exc.code} {exc.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
