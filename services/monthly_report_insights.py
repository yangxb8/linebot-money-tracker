"""Insight commentary for monthly reports (LLM + template fallback)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from services.bot_persona import get_active_persona
from services.confirmation_i18n import t
from services.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


def template_insight(language: str, snapshot: Dict[str, Any], period_label: str) -> str:
    if not snapshot.get('has_any_budget'):
        spent = snapshot.get('spending_total') or 0
        return t(
            language,
            'monthly_report_insight_no_budget',
            period=period_label,
            spent=f'{int(spent):,}',
        )

    total = snapshot.get('total') or {}
    lines = [t(language, 'monthly_report_insight_header', period=period_label)]
    if total:
        spent = int(total.get('spent') or 0)
        limit = int(total.get('limit') or 0)
        remaining = int(total.get('remaining') or 0)
        lines.append(
            t(
                language,
                'monthly_report_insight_total',
                spent=f'{spent:,}',
                limit=f'{limit:,}',
                remaining=f'{remaining:,}',
            )
        )
        if spent > limit:
            lines.append(t(language, 'monthly_report_insight_over_total'))
        elif (total.get('pace_ratio') or 0) > 1:
            lines.append(t(language, 'monthly_report_insight_pace_ahead'))
        else:
            lines.append(t(language, 'monthly_report_insight_on_track'))

    cats = snapshot.get('categories') or []
    if cats:
        names = ', '.join(str(c.get('name')) for c in cats[:3])
        lines.append(t(language, 'monthly_report_insight_drivers', names=names))

    persona = get_active_persona()
    if persona.emoji_level > 0 and snapshot.get('overspend_severity') in ('caution', 'high'):
        lines[0] = '⚠️ ' + lines[0]
    elif persona.emoji_level > 0:
        lines[0] = '✨ ' + lines[0]
    return '\n'.join(lines)


async def generate_insight_text(
    language: str,
    snapshot: Dict[str, Any],
    period_label: str,
    gemini: Optional[GeminiClient],
) -> str:
    fallback = template_insight(language, snapshot, period_label)
    if gemini is None:
        return fallback
    try:
        prompt = (
            'Write a short monthly budget report commentary (max 80 words) for a household expense bot. '
            'Focus on meeting the budget. Use the facts only; do not invent numbers.\n'
            f'Language code: {language}\n'
            f'Period: {period_label}\n'
            f'Snapshot JSON: {snapshot}\n'
            'Reply with plain text only.'
        )
        from services.usage_metering import llm_operation_scope

        with llm_operation_scope('monthly_report_insight'):
            text = await gemini.generate_reply(prompt)
        cleaned = (text or '').strip()
        return cleaned or fallback
    except Exception:
        logger.exception('monthly report insight LLM failed; using template')
        return fallback
