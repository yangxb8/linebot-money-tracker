import logging
import os
import unittest
from unittest.mock import patch

from services.sentry_setup import _float_env, init_sentry


class TestSentrySetup(unittest.TestCase):
    def test_init_sentry_noop_without_dsn(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('SENTRY_DSN', None)
            self.assertFalse(init_sentry())

    def test_init_sentry_calls_sdk_with_logging_integration(self):
        with patch.dict(
            os.environ,
            {
                'SENTRY_DSN': 'https://key@o123.ingest.sentry.io/456',
                'SENTRY_ENVIRONMENT': 'test',
                'SENTRY_TRACES_SAMPLE_RATE': '0.25',
            },
            clear=False,
        ):
            with patch('sentry_sdk.init') as mock_init:
                with patch('sentry_sdk.integrations.logging.LoggingIntegration') as mock_logging:
                    mock_logging.return_value = object()
                    self.assertTrue(init_sentry())

        mock_init.assert_called_once()
        kwargs = mock_init.call_args.kwargs
        self.assertEqual(kwargs['dsn'], 'https://key@o123.ingest.sentry.io/456')
        self.assertEqual(kwargs['environment'], 'test')
        self.assertFalse(kwargs['enable_logs'])
        self.assertEqual(kwargs['traces_sample_rate'], 0.25)
        self.assertEqual(kwargs['integrations'], [mock_logging.return_value])
        mock_logging.assert_called_once_with(
            level=logging.ERROR,
            event_level=logging.ERROR,
        )

    def test_traces_sample_rate_clamped(self):
        with patch.dict(os.environ, {'SENTRY_TRACES_SAMPLE_RATE': '2.5'}, clear=False):
            self.assertEqual(_float_env('SENTRY_TRACES_SAMPLE_RATE', 0.0), 1.0)
        with patch.dict(os.environ, {'SENTRY_TRACES_SAMPLE_RATE': '-1'}, clear=False):
            self.assertEqual(_float_env('SENTRY_TRACES_SAMPLE_RATE', 0.0), 0.0)
        with patch.dict(os.environ, {'SENTRY_TRACES_SAMPLE_RATE': 'nope'}, clear=False):
            self.assertEqual(_float_env('SENTRY_TRACES_SAMPLE_RATE', 0.0), 0.0)


if __name__ == '__main__':
    unittest.main()
