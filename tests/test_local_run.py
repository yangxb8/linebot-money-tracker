import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, patch

from services.message_context import BotReply

os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
class TestLocalRun(unittest.TestCase):
    def test_missing_gemini_key_exits(self):
        env = {'GEMINI_API_KEY': ''}
        with patch.dict(os.environ, env, clear=False):
            with patch.object(sys, 'argv', ['local_run.py', '--text', 'hello']):
                import importlib
                import local_run
                importlib.reload(local_run)
                self.assertEqual(local_run.main(), 1)

    def test_usage_without_flags(self):
        with patch.object(sys, 'argv', ['local_run.py']):
            import local_run
            with self.assertRaises(SystemExit) as ctx:
                local_run.main()
            self.assertEqual(ctx.exception.code, 2)

    def test_text_prints_reply_to_stdout(self):
        with patch.object(sys, 'argv', ['local_run.py', '--text', 'Lunch 1200 yen']), patch(
            'local_run.process_text_message',
            AsyncMock(return_value=BotReply(text='Detected expense(s):\n- Lunch: 1200.0 yen')),
        ):
            import local_run
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = local_run.main()
            self.assertEqual(code, 0)
            self.assertIn('Detected expense(s):', buf.getvalue())

    def test_image_missing_file(self):
        with patch.object(sys, 'argv', ['local_run.py', '--image', 'nonexistent-file.jpg']):
            import local_run
            code = local_run.main()
            self.assertEqual(code, 1)

    def test_image_prints_reply(self):
        sample = Path('specs/002-expense-intent-analysis/samples/japanese_receipt.ocr.txt')
        if not sample.is_file():
            self.skipTest('sample file not available')

        with patch.object(sys, 'argv', ['local_run.py', '--image', str(sample)]), patch(
            'local_run.process_image_message',
            AsyncMock(return_value=BotReply(text='Detected expense(s):\n- total: 600.0 JPY')),
        ):
            import local_run
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = local_run.main()
            self.assertEqual(code, 0)
            self.assertIn('Detected expense(s):', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
