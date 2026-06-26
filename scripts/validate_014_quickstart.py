#!/usr/bin/env python3
"""Validate 014 quickstart (T030) and SC-001 spot check (T031).

Runs automated integration tests always. When GEMINI_API_KEY and Supabase are
configured, also executes a live local_run image flow and queries metadata rows.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from services.env_loader import load_env, require_env_vars

logger = logging.getLogger(__name__)

FIXTURE_IMAGE = REPO_ROOT / 'tests' / 'fixtures' / 'aeon_multi_line_receipt.jpg'
GENERATOR = REPO_ROOT / 'scripts' / 'generate_aeon_receipt_fixture.py'


def _run_pytest_integration() -> int:
    cmd = [
        sys.executable,
        '-m',
        'pytest',
        'tests/test_014_quickstart_integration.py',
        '-q',
    ]
    logger.info('Running integration tests: %s', ' '.join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT)


def _ensure_fixture_image() -> Path:
    if not FIXTURE_IMAGE.is_file():
        logger.info('Generating receipt fixture image')
        subprocess.check_call([sys.executable, str(GENERATOR)], cwd=REPO_ROOT)
    return FIXTURE_IMAGE


def _run_live_image_flow() -> int:
    missing = require_env_vars(['GEMINI_API_KEY'])
    if missing:
        logger.warning('Skipping live local_run (--image): missing %s', ', '.join(missing))
        return 0

    image_path = _ensure_fixture_image()
    cmd = [
        sys.executable,
        str(REPO_ROOT / 'local_run.py'),
        '--image',
        str(image_path),
        '--skip-usage-limits',
    ]
    logger.info('Running live image flow: %s', ' '.join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        logger.error('local_run failed with exit code %s', result.returncode)
        return result.returncode

    missing_sb = require_env_vars(['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'])
    if missing_sb:
        logger.warning('Skipping Supabase metadata check: missing %s', ', '.join(missing_sb))
        return 0

    from services.supabase_client import get_supabase_client

    client = get_supabase_client()
    rows = (
        client.table('expenses')
        .select('description, metadata')
        .not_.is_('metadata->store_name', 'null')
        .order('created_at', desc=True)
        .limit(10)
        .execute()
    ).data or []

    if not rows:
        logger.warning('No expenses with metadata.store_name found after live run')
        return 1

    store_names = {str(r.get('metadata', {}).get('store_name', '')) for r in rows}
    logger.info('Recent metadata.store_name values: %s', store_names)
    if len(store_names) > 1:
        logger.error('SC-001 check: inconsistent store_name across lines: %s', store_names)
        return 1

    logger.info('Live quickstart OK: %d row(s) with shared store_name', len(rows))
    return 0


def _sc001_supabase_spot_check() -> int:
    missing_sb = require_env_vars(['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'])
    if missing_sb:
        logger.info('Skipping Supabase SC-001 spot check (no Supabase credentials)')
        return 0

    from tests.test_014_quickstart_integration import sc001_line_share_rate
    from services.merchant_resolve import merchant_key_from_expense_row
    from services.supabase_client import get_supabase_client

    client = get_supabase_client()
    rows = (
        client.table('expenses')
        .select('description, metadata, source_message_id')
        .not_.is_('metadata->store_name', 'null')
        .is_('deleted_at', 'null')
        .order('created_at', desc=True)
        .limit(200)
        .execute()
    ).data or []

    if not rows:
        logger.info('No vision receipt rows in DB yet; SC-001 covered by fixture tests')
        return 0

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        meta = row.get('metadata') or {}
        store = str(meta.get('store_name', '')).strip()
        if not store:
            continue
        msg_id = str(row.get('source_message_id', uuid.uuid4()))
        grouped.setdefault(msg_id, []).append(
            {
                'description': row.get('description'),
                'store_name': store,
            }
        )

    passing = 0
    total = 0
    for msg_id, items in grouped.items():
        if len(items) < 2:
            continue
        total += 1
        rate = sc001_line_share_rate(items)
        store_key = merchant_key_from_expense_row(
            {'description': '', 'metadata': {'store_name': items[0]['store_name']}}
        )
        logger.info('Receipt %s: %d lines, SC-001 rate=%.0f%%, store_key=%s', msg_id, len(items), rate * 100, store_key)
        if rate >= 0.70:
            passing += 1

    if total == 0:
        logger.info('No multi-line receipt groups in DB; SC-001 validated via fixtures')
        return 0

    share = passing / total
    logger.info('SC-001 spot check: %d/%d receipt groups >= 70%%', passing, total)
    return 0 if share >= 0.70 or passing == total else 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate 014 quickstart and SC-001')
    parser.add_argument('--live', action='store_true', help='Run live local_run when credentials exist')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s %(message)s',
    )
    load_env()

    code = _run_pytest_integration()
    if code != 0:
        return code

    if args.live:
        code = _run_live_image_flow()
        if code != 0:
            return code

    return _sc001_supabase_spot_check()


if __name__ == '__main__':
    raise SystemExit(main())
