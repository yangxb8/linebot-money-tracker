"""Pillow PNG composition for monthly expense reports."""

from __future__ import annotations

import io
from typing import Any, Dict, Optional, Tuple

# Shared layout family
WIDTH = 900
HEIGHT = 1200
MARGIN = 48
CHART_TOP = 220
CHART_HEIGHT = 420

_THEME_COLORS = {
    'default': (46, 125, 122),
    'food': (194, 98, 54),
    'transport': (41, 98, 155),
    'housing': (92, 64, 51),
    'fun': (142, 68, 173),
    'shopping': (39, 174, 96),
}


def _font(size: int):
    from PIL import ImageFont

    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
    except OSError:
        try:
            return ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', size)
        except OSError:
            return ImageFont.load_default()


def _theme_rgb(top_name: Optional[str], severity: str) -> Tuple[int, int, int]:
    name = (top_name or '').lower()
    base = _THEME_COLORS['default']
    for key, color in _THEME_COLORS.items():
        if key != 'default' and key in name:
            base = color
            break
    if '食' in (top_name or '') or 'food' in name or '外食' in (top_name or ''):
        base = _THEME_COLORS['food']
    elif '交通' in (top_name or '') or 'transport' in name:
        base = _THEME_COLORS['transport']
    if severity == 'high':
        return (176, 58, 46)
    if severity == 'caution':
        return (tuple(min(255, c + 30) for c in base) if False else (180, 110, 40))
    return base


def render_report_png(
    *,
    snapshot: Dict[str, Any],
    insight_text: str,
    period_label: str,
    title: str = 'Monthly Report',
) -> bytes:
    """Compose one PNG: primary budget-vs-actual chart + commentary."""
    # Import Pillow only when rendering so Cloud Run cold start does not load it.
    from PIL import Image, ImageDraw

    severity = str(snapshot.get('overspend_severity') or 'none')
    top = snapshot.get('top_spend_category') or {}
    accent = _theme_rgb(top.get('name'), severity)

    img = Image.new('RGB', (WIDTH, HEIGHT), (252, 250, 247))
    draw = ImageDraw.Draw(img)

    # Header band
    draw.rectangle([0, 0, WIDTH, 160], fill=(accent[0], accent[1], accent[2]))
    title_font = _font(40)
    sub_font = _font(22)
    body_font = _font(20)
    small_font = _font(16)

    draw.text((MARGIN, 40), title, fill=(255, 255, 255), font=title_font)
    draw.text((MARGIN, 100), period_label, fill=(240, 240, 240), font=sub_font)

    # Chart panel
    panel_top = CHART_TOP - 20
    draw.rounded_rectangle(
        [MARGIN - 8, panel_top, WIDTH - MARGIN + 8, panel_top + CHART_HEIGHT + 40],
        radius=18,
        fill=(255, 255, 255),
        outline=(230, 226, 220),
        width=2,
    )

    series = _chart_series(snapshot)
    _draw_bars(draw, series, accent, body_font, small_font)

    # Commentary
    comment_y = panel_top + CHART_HEIGHT + 70
    draw.text((MARGIN, comment_y), 'Insights', fill=(40, 40, 40), font=sub_font)
    wrapped = _wrap_text(insight_text or '', body_font, WIDTH - 2 * MARGIN)
    y = comment_y + 40
    for line in wrapped[:18]:
        draw.text((MARGIN, y), line, fill=(55, 55, 55), font=body_font)
        y += 28

    # Footer brand frame
    draw.rectangle([0, HEIGHT - 36, WIDTH, HEIGHT], fill=accent)
    draw.text((MARGIN, HEIGHT - 28), 'linebot-money-tracker', fill=(255, 255, 255), font=small_font)

    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _chart_series(snapshot: Dict[str, Any]) -> list[dict]:
    series: list[dict] = []
    if snapshot.get('has_any_budget'):
        total = snapshot.get('total')
        if total:
            series.append(
                {
                    'label': 'Total',
                    'limit': float(total.get('limit') or 0),
                    'spent': float(total.get('spent') or 0),
                }
            )
        for cat in snapshot.get('categories') or []:
            series.append(
                {
                    'label': str(cat.get('name') or 'Cat')[:10],
                    'limit': float(cat.get('limit') or 0),
                    'spent': float(cat.get('spent') or 0),
                }
            )
        return series

    # Fallback: spending only
    spent = float(snapshot.get('spending_total') or 0)
    series.append({'label': 'Spend', 'limit': max(spent, 1.0), 'spent': spent, 'fallback': True})
    return series


def _draw_bars(draw, series: list[dict], accent, body_font, small_font) -> None:
    if not series:
        draw.text((MARGIN + 20, CHART_TOP + 160), 'No data', fill=(120, 120, 120), font=body_font)
        return

    chart_left = MARGIN + 20
    chart_right = WIDTH - MARGIN - 20
    chart_bottom = CHART_TOP + CHART_HEIGHT - 30
    chart_top = CHART_TOP + 30
    usable_w = chart_right - chart_left
    group_w = usable_w / max(len(series), 1)
    max_val = max(max(s['limit'], s['spent']) for s in series) or 1.0

    for idx, item in enumerate(series):
        cx = chart_left + group_w * idx + group_w / 2
        bar_w = min(36, group_w * 0.28)
        limit_h = (item['limit'] / max_val) * (chart_bottom - chart_top)
        spent_h = (item['spent'] / max_val) * (chart_bottom - chart_top)
        # budget (outline)
        x0 = cx - bar_w - 4
        draw.rectangle(
            [x0, chart_bottom - limit_h, x0 + bar_w, chart_bottom],
            outline=accent,
            width=3,
        )
        # spent (fill)
        x1 = cx + 4
        fill = (176, 58, 46) if item['spent'] > item['limit'] and not item.get('fallback') else accent
        draw.rectangle(
            [x1, chart_bottom - spent_h, x1 + bar_w, chart_bottom],
            fill=fill,
        )
        draw.text((cx - 28, chart_bottom + 8), item['label'], fill=(70, 70, 70), font=small_font)

    draw.text((MARGIN + 20, CHART_TOP + 4), 'Budget (outline) vs Actual (fill)', fill=(90, 90, 90), font=small_font)


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    words = text.replace('\n', ' \n ').split()
    lines: list[str] = []
    current = ''
    for word in words:
        if word == '\n':
            lines.append(current)
            current = ''
            continue
        candidate = f'{current} {word}'.strip()
        bbox = font.getbbox(candidate)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
