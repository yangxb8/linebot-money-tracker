import unittest
from unittest.mock import patch

from services.bot_persona import PersonaConfig
from services.tenant_context import TenantContext
from services.tenant_settings import (
    TenantBotSettings,
    normalize_reply_language_override,
    resolve_tenant_reply_language,
)


class TestTenantReplyLanguage(unittest.TestCase):
    def test_normalize_accepts_supported_codes(self):
        self.assertEqual(normalize_reply_language_override('en'), 'en')
        self.assertEqual(normalize_reply_language_override('JA'), 'ja')
        self.assertEqual(normalize_reply_language_override('zh'), 'zh')

    def test_normalize_treats_empty_and_invalid_as_default(self):
        self.assertIsNone(normalize_reply_language_override(None))
        self.assertIsNone(normalize_reply_language_override(''))
        self.assertIsNone(normalize_reply_language_override('fr'))
        self.assertIsNone(normalize_reply_language_override('english'))

    def test_resolve_keeps_base_without_override(self):
        tenant = TenantContext.personal('user-1')
        with patch(
            'services.tenant_settings.fetch_tenant_bot_settings',
            return_value=TenantBotSettings(persona=PersonaConfig(), reply_language=None),
        ):
            self.assertEqual(resolve_tenant_reply_language(tenant, 'zh'), 'zh')

    def test_resolve_applies_tenant_override(self):
        tenant = TenantContext.personal('user-1')
        with patch(
            'services.tenant_settings.fetch_tenant_bot_settings',
            return_value=TenantBotSettings(persona=PersonaConfig(), reply_language='en'),
        ):
            self.assertEqual(resolve_tenant_reply_language(tenant, 'ja'), 'en')

    def test_resolve_without_tenant_keeps_base(self):
        self.assertEqual(resolve_tenant_reply_language(None, 'zh'), 'zh')
