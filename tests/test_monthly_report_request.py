"""Unit tests for monthly report ask orchestration (same-turn / ask-again / refresh)."""

from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.message_context import MessageContext
from services.monthly_report import SAME_TURN_BUDGET_SECONDS, handle_monthly_report_ask
from services.monthly_report_period import ReportPeriod
from services.monthly_report_repository import (
    ArtifactRecord,
    clear_memory_store,
    mark_ready,
    upsert_preparing,
)
from services.tenant_context import TenantContext


@pytest.fixture(autouse=True)
def _clear_store():
    clear_memory_store()
    yield
    clear_memory_store()


def _tenant() -> TenantContext:
    return TenantContext.personal('U-report-req')


def _period() -> ReportPeriod:
    return ReportPeriod(
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        fiscal_start_day=1,
        label='Oct 2026',
    )


def _context() -> MessageContext:
    return MessageContext(
        tenant=_tenant(),
        source_message_id='msg-1',
        reply_language='en',
    )


@pytest.mark.asyncio
async def test_same_turn_ready_delivers_image():
    period = _period()
    with patch(
        'services.monthly_report.resolve_report_period', return_value=period
    ), patch(
        'services.monthly_report.compute_data_fingerprint', return_value='data-fp'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='style-fp'
    ), patch(
        'services.monthly_report_snapshot.build_budget_snapshot',
        return_value={'has_any_budget': False, 'spending_total': 1000, 'categories': []},
    ), patch(
        'services.monthly_report_insights.generate_insight_text',
        AsyncMock(return_value='Insight'),
    ), patch(
        'services.monthly_report_render.render_report_png',
        return_value=b'\x89PNG\r\n\x1a\nfake',
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=1, custom_text=''),
    ):
        reply = await handle_monthly_report_ask('monthly report', MagicMock(), _context())

    assert reply.image is not None
    assert reply.image.png_bytes
    assert 'Oct 2026' in reply.text or 'report' in reply.text.lower()


@pytest.mark.asyncio
async def test_same_turn_timeout_returns_preparing():
    period = _period()

    async def slow_prepare(*_args, **_kwargs):
        await asyncio.sleep(SAME_TURN_BUDGET_SECONDS + 2)
        return MagicMock(status='ready')

    with patch(
        'services.monthly_report.resolve_report_period', return_value=period
    ), patch(
        'services.monthly_report.compute_data_fingerprint', return_value='data-fp'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='style-fp'
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=1, custom_text=''),
    ), patch(
        'services.monthly_report._prepare_artifact', side_effect=slow_prepare
    ), patch(
        'services.monthly_report.SAME_TURN_BUDGET_SECONDS', 0.05
    ):
        reply = await handle_monthly_report_ask('monthly report', MagicMock(), _context())

    assert reply.image is None
    assert 'prepar' in reply.text.lower() or '準備' in reply.text


@pytest.mark.asyncio
async def test_in_progress_reply():
    period = _period()
    upsert_preparing(
        _tenant(),
        period,
        data_fingerprint='data-fp',
        style_fingerprint='style-fp',
    )
    with patch(
        'services.monthly_report.resolve_report_period', return_value=period
    ), patch(
        'services.monthly_report.compute_data_fingerprint', return_value='data-fp'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='style-fp'
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=1, custom_text=''),
    ):
        reply = await handle_monthly_report_ask('monthly report', MagicMock(), _context())

    assert reply.image is None
    assert 'prepar' in reply.text.lower() or '準備' in reply.text or 'progress' in reply.text.lower()


@pytest.mark.asyncio
async def test_ready_fingerprint_match_resends_without_prepare():
    period = _period()
    artifact = mark_ready(
        _tenant(),
        period,
        artifact_id='art-1',
        data_fingerprint='data-fp',
        style_fingerprint='style-fp',
        insight_text='ok',
        snapshot_json={'has_any_budget': False, 'spending_total': 1},
        png_bytes=b'\x89PNG\r\n\x1a\nready',
    )
    assert artifact.status == 'ready'

    prepare = AsyncMock()
    with patch(
        'services.monthly_report.resolve_report_period', return_value=period
    ), patch(
        'services.monthly_report.compute_data_fingerprint', return_value='data-fp'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='style-fp'
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=1, custom_text=''),
    ), patch(
        'services.monthly_report._prepare_artifact', prepare
    ):
        reply = await handle_monthly_report_ask('monthly report', MagicMock(), _context())

    prepare.assert_not_called()
    assert reply.image is not None
    assert reply.image.png_bytes == b'\x89PNG\r\n\x1a\nready'


@pytest.mark.asyncio
async def test_fingerprint_stale_triggers_refresh():
    period = _period()
    mark_ready(
        _tenant(),
        period,
        artifact_id='art-stale',
        data_fingerprint='old-data',
        style_fingerprint='style-fp',
        insight_text='old',
        snapshot_json={'has_any_budget': False, 'spending_total': 1},
        png_bytes=b'old',
    )

    with patch(
        'services.monthly_report.resolve_report_period', return_value=period
    ), patch(
        'services.monthly_report.compute_data_fingerprint', return_value='new-data'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='style-fp'
    ), patch(
        'services.monthly_report_snapshot.build_budget_snapshot',
        return_value={'has_any_budget': False, 'spending_total': 2000, 'categories': []},
    ), patch(
        'services.monthly_report_insights.generate_insight_text',
        AsyncMock(return_value='Fresh'),
    ), patch(
        'services.monthly_report_render.render_report_png',
        return_value=b'\x89PNG\r\n\x1a\nfresh',
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=1, custom_text=''),
    ):
        reply = await handle_monthly_report_ask('monthly report', MagicMock(), _context())

    assert reply.image is not None
    assert reply.image.png_bytes == b'\x89PNG\r\n\x1a\nfresh'
