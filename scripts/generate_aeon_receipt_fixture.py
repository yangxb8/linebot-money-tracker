#!/usr/bin/env python3
"""Generate a synthetic Aeon-style receipt JPEG for local_run --image testing."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path(__file__).resolve().parent.parent / 'tests' / 'fixtures' / 'aeon_multi_line_receipt.jpg'
FONT_PATH = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'

LINES = [
    'イオン 〇〇店',
    '',
    '牛乳          198',
    '食パン        128',
    '卵            98',
    'バナナ        158',
    '',
    '合計          582',
]


def main() -> None:
    font = ImageFont.truetype(FONT_PATH, 28)
    line_height = 36
    width = 480
    height = 40 + line_height * len(LINES)
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    y = 20
    for line in LINES:
        draw.text((24, y), line, fill='black', font=font)
        y += line_height
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format='JPEG', quality=92)
    print(OUTPUT)


if __name__ == '__main__':
    main()
