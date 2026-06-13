#!/usr/bin/env python3
"""Local console harness — simulate LINE text/image input and print bot reply."""

import argparse
import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path

from services.confirmation_repository import save_confirmation
from services.env_loader import load_env, require_env_vars
from services.metered_gemini import create_gemini_client
from services.message_context import MessageContext, ReplyContext
from services.tenant_context import resolve_tenant_for_console
from services.usage_limiter import format_denial_reply, prepare_inbound_usage
from services.usage_metering import usage_billing_scope
from services.message_handler import process_image_message, process_reply_edit, process_text_message

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
        '--reply-to',
        help='Bot confirmation message ID to simulate reply-to-message flow',
    )
    parser.add_argument(
        '--group-id',
        help='Simulate a LINE group chat (shared ledger for this group ID)',
    )
    parser.add_argument(
        '--room-id',
        help='Simulate a LINE multi-person room (shared ledger for this room ID)',
    )
    parser.add_argument(
        '--skip-usage-limits',
        action='store_true',
        help='Skip per-user LLM usage limits (still runs Gemini when configured)',
    )
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


async def _run(args: argparse.Namespace) -> tuple[str, str | None]:
    gemini = create_gemini_client(api_key=os.getenv('GEMINI_API_KEY'))
    line_user_id = os.getenv('LOCAL_LINE_USER_ID', 'local-dev-user')

    if args.group_id and args.room_id:
        raise ValueError('Use only one of --group-id or --room-id')

    tenant = resolve_tenant_for_console(
        line_user_id,
        group_id=args.group_id,
        room_id=args.room_id,
    )

    source_message_id = str(uuid.uuid4())

    if args.reply_to:
        if not args.text:
            raise ValueError('--reply-to requires --text')
        reply_context = ReplyContext(
            tenant=tenant,
            user_reply_message_id=source_message_id,
            quoted_bot_message_id=args.reply_to,
        )
        usage_prep = prepare_inbound_usage(
            tenant,
            line_user_id,
            source_message_id,
            text=args.text,
            skip_limits=args.skip_usage_limits,
        )
        if not usage_prep.allowed:
            return format_denial_reply('en', usage_prep.reason), None
        with usage_billing_scope(usage_prep.billing_context):
            edit_result = await process_reply_edit(args.text, reply_context, gemini)
        return edit_result.text, None

    context = MessageContext(
        tenant=tenant,
        source_message_id=source_message_id,
    )

    if args.text is not None:
        usage_prep = prepare_inbound_usage(
            tenant,
            line_user_id,
            source_message_id,
            text=args.text,
            skip_limits=args.skip_usage_limits,
        )
        if not usage_prep.allowed:
            return format_denial_reply('en', usage_prep.reason), None
        with usage_billing_scope(usage_prep.billing_context):
            bot_reply = await process_text_message(args.text, gemini, context)
    else:
        image_bytes = _read_image(args.image)
        usage_prep = prepare_inbound_usage(
            tenant,
            line_user_id,
            source_message_id,
            image_bytes=image_bytes,
            skip_limits=args.skip_usage_limits,
        )
        if not usage_prep.allowed:
            return format_denial_reply('en', usage_prep.reason), None
        with usage_billing_scope(usage_prep.billing_context):
            bot_reply = await process_image_message(image_bytes, gemini, context=context)

    bot_message_id = None
    if bot_reply.confirmation:
        bot_message_id = f'console-{uuid.uuid4()}'
        save_confirmation(
            bot_message_id=bot_message_id,
            tenant=bot_reply.confirmation.tenant,
            confirmation_text=bot_reply.confirmation.confirmation_text,
            items=list(bot_reply.confirmation.items),
        )

    return bot_reply.text, bot_message_id


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
        reply, bot_message_id = asyncio.run(_run(args))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        logger.exception('Console processing failed')
        return 1

    print(reply)
    if bot_message_id:
        print(f'[confirmation] bot_message_id={bot_message_id} (use with --reply-to)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
