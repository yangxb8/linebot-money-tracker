import unittest
from unittest.mock import patch

from services.bot_persona import PersonaConfig
from services.tenant_context import TenantContext
from services.tenant_settings import (
    TenantBotSettings,
    normalize_reply_language_override,
    resolve_effective_bot_settings,
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

    def test_resolve_shared_tenant_falls_back_to_personal_override(self):
        group = TenantContext.group('group-1', 'user-1')
        personal = TenantContext.personal('user-1')
        with patch(
            'services.tenant_settings.fetch_tenant_bot_settings',
            side_effect=lambda tenant: TenantBotSettings(
                persona=PersonaConfig(),
                reply_language='zh' if tenant.tenant_id == 'user-1' else None,
            ),
        ):
            self.assertEqual(resolve_tenant_reply_language(group, 'en'), 'zh')
            self.assertEqual(resolve_tenant_reply_language(personal, 'en'), 'zh')

    def test_resolve_effective_persona_falls_back_to_personal_in_group(self):
        from services.bot_persona import EMOJI_LEVEL_LIGHT, PersonaConfig

        group = TenantContext.group('group-1', 'user-1')
        personal_persona = PersonaConfig(emoji_level=EMOJI_LEVEL_LIGHT)
        with patch(
            'services.tenant_settings.fetch_tenant_bot_settings',
            side_effect=lambda tenant: TenantBotSettings(
                persona=personal_persona if tenant.tenant_id == 'user-1' else PersonaConfig(),
                reply_language=None,
            ),
        ):
            settings = resolve_effective_bot_settings(group)
        self.assertEqual(settings.persona.emoji_level, EMOJI_LEVEL_LIGHT)
