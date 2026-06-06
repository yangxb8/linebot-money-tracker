#!/usr/bin/env python3
"""Local console harness — simulate LINE text/image input and print bot reply."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from services.env_loader import load_env, require_env_vars
from services.gemini_client import GeminiClient
from services.message_handler import process_image_message, process_text_message

logger = logging.getLogger(__name__)

CONSOLE_REQUIRED_VARS = ['GEMINI_API_KEY']


def _configure_logging(debug: bool = False) -> None:
    level_name = 'DEBUG' if debug else __import__('os').getenv('LOG_LEVEL', 'INFO')
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        force=True,
    )
    logging.getLogger('services').setLevel(level)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Simulate LINE message processing locally and print the bot reply.',
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--text', help='Expense message text to process')
    group.add_argument('--image', help='Path to a receipt image file')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug-level logging (or set LOG_LEVEL=DEBUG)',
    )
    return parser


def _read_image(path_str: str) -> bytes:
    path = Path(path_str)
    if not path.is_file():
        raise FileNotFoundError(f'Image file not found: {path}')
    try:
        return path.read_bytes()
    except OSError as exc:
        raise OSError(f'Unable to read image file: {path}') from exc


async def _run(args: argparse.Namespace) -> str:
    gemini = GeminiClient(api_key=__import__('os').getenv('GEMINI_API_KEY'))
    if args.text is not None:
        return await process_text_message(args.text, gemini)
    image_bytes = _read_image(args.image)
    return await process_image_message(image_bytes, gemini)


def main() -> int:
    load_env()

    missing = require_env_vars(CONSOLE_REQUIRED_VARS)
    if missing:
        print('Missing required environment variables:', ', '.join(missing))
        return 1

    parser = _build_parser()
    args = parser.parse_args()
    _configure_logging(debug=args.debug)

    try:
        reply = asyncio.run(_run(args))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        logger.exception('Console processing failed')
        return 1

    print(reply)
    return 0


if __name__ == '__main__':
    sys.exit(main())
