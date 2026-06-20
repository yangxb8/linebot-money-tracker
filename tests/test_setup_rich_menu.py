import json
import unittest

from scripts.setup_rich_menu import build_rich_menu_payload


class TestSetupRichMenu(unittest.TestCase):
    def test_build_rich_menu_payload_shape(self):
        payload = build_rich_menu_payload("https://liff.line.me/1234567890-AbCdEfGh")
        self.assertEqual(payload["size"], {"width": 2500, "height": 843})
        self.assertEqual(payload["name"], "expense-dashboard-v1")
        self.assertEqual(payload["areas"][0]["action"]["type"], "uri")
        self.assertEqual(
            payload["areas"][0]["action"]["uri"],
            "https://liff.line.me/1234567890-AbCdEfGh",
        )
        self.assertEqual(payload["areas"][0]["action"]["label"], "家計簿")

    def test_payload_serializes_to_json(self):
        payload = build_rich_menu_payload("https://liff.line.me/test")
        encoded = json.dumps(payload)
        self.assertIn("expense-dashboard-v1", encoded)


if __name__ == "__main__":
    unittest.main()
