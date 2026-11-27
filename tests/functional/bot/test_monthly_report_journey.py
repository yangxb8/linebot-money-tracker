"""Functional journeys: monthly report ask, tip, no expense side effects."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.message_context import BotReply, MessageContext, ReportImagePayload
from services.message_handler import process_text_message
from services.monthly_report_period import ReportPeriod
from services.monthly_report_repository import clear_memory_store
from services.tenant_context import TenantContext
from tests.functional.bot.conftest import assert_callback_ok, post_signed
from tests.functional.bot.helpers.webhook_events import text_message_event, webhook_body


@pytest.fixture(autouse=True)
def _clear_store():
    clear_memory_store()
    yield
    clear_memory_store()


def _ctx(tenant: TenantContext | None = None) -> MessageContext:
    return MessageContext(
        tenant=tenant or TenantContext.personal('U4af4980629'),
        source_message_id='msg-report-1',
        reply_language='en',
    )


def _period() -> ReportPeriod:
    return ReportPeriod(
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        fiscal_start_day=1,
        label='Oct 2026',
    )


@pytest.mark.functional
def test_bot_monthly_report_webhook_delivers_image(client, reply_mock):
    body = webhook_body(text_message_event('monthly report', message_id='msg-mr-1'))
    with patch('main.save_inbound_text_message'), patch(
        'main.process_text_message',
        AsyncMock(
            return_value=BotReply(
                text='Here’s your report for Oct 2026.',
                image=ReportImagePayload(
                    original_url='https://example.com/report.png',
                    preview_url='https://example.com/report.png',
                    png_bytes=b'\x89PNG',
                ),
            )
        ),
    ):
        assert_callback_ok(post_signed(client, body))

    reply_mock.assert_awaited()
    messages = reply_mock.call_args[0][0].messages
    assert any(getattr(m, 'text', None) for m in messages)
    assert any(getattr(m, 'original_content_url', None) for m in messages)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_monthly_report_ask_no_expense_or_wish_side_effects():
    expense_insert = MagicMock()
    wish_insert = MagicMock()
    with patch(
        'services.monthly_report.resolve_report_period', return_value=_period()
    ), patch(
        'services.monthly_report.compute_data_fingerprint', return_value='df'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='sf'
    ), patch(
        'services.monthly_report_snapshot.build_budget_snapshot',
        return_value={
            'has_any_budget': True,
            'total': {'limit': 100000, 'spent': 90000, 'remaining': 10000, 'pace_ratio': 0.9},
            'categories': [],
            'top_spend_category': {'id': 'food', 'name': 'Food'},
            'overspend_severity': 'none',
        },
    ), patch(
        'services.monthly_report_insights.generate_insight_text',
        AsyncMock(return_value='On track.'),
    ), patch(
        'services.monthly_report_render.render_report_png',
        return_value=b'\x89PNG\r\n\x1a\nreport',
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=1, custom_text=''),
    ), patch(
        'services.message_handler.insert_expenses', expense_insert
    ), patch(
        'services.wish_list.insert_active_wish_list_item', wish_insert
    ), patch(
        'services.message_handler.maybe_new_period_tip', return_value=None
    ):
        reply = await process_text_message('monthly report', MagicMock(), _ctx())

    assert reply.image is not None
    assert reply.image.png_bytes
    expense_insert.assert_not_called()
    wish_insert.assert_not_called()


@pytest.mark.functional
@pytest.mark.asyncio
async def test_monthly_report_group_ledger_period_default():
    group = TenantContext.group('C123', 'U4af4980629')
    with patch(
        'services.monthly_report.resolve_report_period', return_value=_period()
    ) as resolve, patch(
        'services.monthly_report.compute_data_fingerprint', return_value='df'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='sf'
    ), patch(
        'services.monthly_report_snapshot.build_budget_snapshot',
        return_value={'has_any_budget': False, 'spending_total': 0, 'categories': []},
    ), patch(
        'services.monthly_report_insights.generate_insight_text',
        AsyncMock(return_value='No budget.'),
    ), patch(
        'services.monthly_report_render.render_report_png',
        return_value=b'\x89PNG\r\n\x1a\ng',
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=0, custom_text=''),
    ), patch(
        'services.message_handler.maybe_new_period_tip', return_value=None
    ):
        reply = await process_text_message('レポート', MagicMock(), _ctx(group))

    resolve.assert_called()
    assert resolve.call_args[0][0].tenant_type == 'group'
    assert reply.image is not None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_preparing_then_deliver_journey():
    period = _period()
    call_count = {'n': 0}

    async def prepare_side_effect(*_a, **_k):
        call_count['n'] += 1
        if call_count['n'] == 1:
            import asyncio

            await asyncio.sleep(10)
        from services.monthly_report_repository import mark_ready

        return mark_ready(
            TenantContext.personal('U4af4980629'),
            period,
            artifact_id='art-j',
            data_fingerprint='df',
            style_fingerprint='sf',
            insight_text='ready',
            snapshot_json={'has_any_budget': False, 'spending_total': 1},
            png_bytes=b'\x89PNG\r\n\x1a\ndeliver',
        )

    with patch(
        'services.monthly_report.resolve_report_period', return_value=period
    ), patch(
        'services.monthly_report.compute_data_fingerprint', return_value='df'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='sf'
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=1, custom_text=''),
    ), patch(
        'services.monthly_report._prepare_artifact', side_effect=prepare_side_effect
    ), patch(
        'services.monthly_report.SAME_TURN_BUDGET_SECONDS', 0.05
    ), patch(
        'services.message_handler.maybe_new_period_tip', return_value=None
    ):
        first = await process_text_message('monthly report', MagicMock(), _ctx())
        # Simulate ready artifact from background completion for second ask
        from services.monthly_report_repository import mark_ready

        mark_ready(
            TenantContext.personal('U4af4980629'),
            period,
            artifact_id='art-j',
            data_fingerprint='df',
            style_fingerprint='sf',
            insight_text='ready',
            snapshot_json={'has_any_budget': False, 'spending_total': 1},
            png_bytes=b'\x89PNG\r\n\x1a\ndeliver',
        )
        second = await process_text_message('monthly report', MagicMock(), _ctx())

    assert first.image is None
    assert 'prepar' in first.text.lower() or '準備' in first.text
    assert second.image is not None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_tip_on_first_message_not_on_second_and_report_precedence():
    tenant = TenantContext.personal('U-tip-j')
    with patch(
        'services.message_handler.maybe_new_period_tip',
        side_effect=['Tip about monthly report', None],
    ), patch(
        'services.message_handler._process_text_message_inner',
        AsyncMock(return_value=BotReply(text='Logged Lunch')),
    ):
        first = await process_text_message('Lunch 1200 yen', MagicMock(), _ctx(tenant))
        second = await process_text_message('Coffee 500 yen', MagicMock(), _ctx(tenant))

    assert 'Tip about monthly report' in first.text
    assert 'Tip about monthly report' not in second.text

    with patch(
        'services.message_handler.maybe_new_period_tip'
    ) as tip_skip, patch(
        'services.monthly_report.resolve_report_period', return_value=_period()
    ), patch(
        'services.monthly_report.compute_data_fingerprint', return_value='df'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='sf'
    ), patch(
        'services.monthly_report_snapshot.build_budget_snapshot',
        return_value={'has_any_budget': False, 'spending_total': 0, 'categories': []},
    ), patch(
        'services.monthly_report_insights.generate_insight_text',
        AsyncMock(return_value='x'),
    ), patch(
        'services.monthly_report_render.render_report_png',
        return_value=b'\x89PNG\r\n\x1a\n',
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=1, custom_text=''),
    ):
        report = await process_text_message('monthly report', MagicMock(), _ctx(tenant))

    # Report ask skips tip attachment entirely
    tip_skip.assert_not_called()
    assert report.image is not None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_budgeted_vs_no_budget_snapshot_paths():
    budgeted = {
        'has_any_budget': True,
        'total': {'limit': 50000, 'spent': 60000, 'remaining': -10000, 'pace_ratio': 1.4},
        'categories': [{'name': 'Food', 'limit': 20000, 'spent': 30000}],
        'top_spend_category': {'id': 'food', 'name': 'Food'},
        'overspend_severity': 'high',
    }
    no_budget = {
        'has_any_budget': False,
        'spending_total': 1234,
        'categories': [],
        'overspend_severity': 'none',
    }

    async def _ask(snapshot):
        with patch(
            'services.monthly_report.resolve_report_period', return_value=_period()
        ), patch(
            'services.monthly_report.compute_data_fingerprint', return_value='df'
        ), patch(
            'services.monthly_report.compute_style_fingerprint', return_value='sf'
        ), patch(
            'services.monthly_report_snapshot.build_budget_snapshot', return_value=snapshot
        ), patch(
            'services.monthly_report_insights.generate_insight_text',
            AsyncMock(side_effect=lambda lang, snap, label, g: (
                'Over total budget' if snap.get('has_any_budget') else 'No budget set'
            )),
        ), patch(
            'services.monthly_report_render.render_report_png',
            return_value=b'\x89PNG\r\n\x1a\nx',
        ), patch(
            'services.monthly_report.resolve_persona_for_tenant',
            return_value=MagicMock(preset='judy_hopps', emoji_level=1, custom_text=''),
        ), patch(
            'services.message_handler.maybe_new_period_tip', return_value=None
        ):
            from services.monthly_report_repository import clear_memory_store

            clear_memory_store()
            return await process_text_message('monthly report', MagicMock(), _ctx())

    r1 = await _ask(budgeted)
    r2 = await _ask(no_budget)
    assert r1.image and r2.image


@pytest.mark.functional
@pytest.mark.asyncio
async def test_style_fingerprint_refresh_when_persona_changes():
    period = _period()
    tenant = TenantContext.personal('U-style')
    from services.monthly_report_repository import mark_ready

    mark_ready(
        tenant,
        period,
        artifact_id='art-style',
        data_fingerprint='df',
        style_fingerprint='old-style',
        insight_text='old',
        snapshot_json={'has_any_budget': False, 'spending_total': 1},
        png_bytes=b'old-png',
    )

    with patch(
        'services.monthly_report.resolve_report_period', return_value=period
    ), patch(
        'services.monthly_report.compute_data_fingerprint', return_value='df'
    ), patch(
        'services.monthly_report.compute_style_fingerprint', return_value='new-style'
    ), patch(
        'services.monthly_report_snapshot.build_budget_snapshot',
        return_value={'has_any_budget': False, 'spending_total': 2, 'categories': []},
    ), patch(
        'services.monthly_report_insights.generate_insight_text',
        AsyncMock(return_value='new insight'),
    ), patch(
        'services.monthly_report_render.render_report_png',
        return_value=b'\x89PNG\r\n\x1a\nnew',
    ), patch(
        'services.monthly_report.resolve_persona_for_tenant',
        return_value=MagicMock(preset='judy_hopps', emoji_level=2, custom_text='x'),
    ), patch(
        'services.message_handler.maybe_new_period_tip', return_value=None
    ):
        reply = await process_text_message('monthly report', MagicMock(), _ctx(tenant))

    assert reply.image is not None
    assert reply.image.png_bytes == b'\x89PNG\r\n\x1a\nnew'
