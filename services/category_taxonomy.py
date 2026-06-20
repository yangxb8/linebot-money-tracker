from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml

from services.supabase_client import is_supabase_configured

if TYPE_CHECKING:
    from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)

CATEGORY_NAMESPACE = uuid.UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479')
UNKNOWN_CODE = 'unknown'
_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'category_taxonomy_ja.yaml'
_LEGACY_L3_TO_L2: Dict[str, str] = {
    'food.dining.cafe': 'food.dining',
    'food.dining.restaurant': 'food.dining',
    'food.dining.fastfood': 'food.dining',
}


@dataclass(frozen=True)
class CategoryNode:
    id: str
    code: str
    name_ja: str
    level: int
    parent_id: Optional[str]
    l1_id: str
    l2_id: Optional[str]
    l3_id: Optional[str]
    path_names: tuple[str, ...]


def category_id_for_code(code: str) -> str:
    return str(uuid.uuid5(CATEGORY_NAMESPACE, code))


def _flatten_nodes(
    nodes: List[Dict[str, Any]],
    parent: Optional[CategoryNode] = None,
) -> List[CategoryNode]:
    flat: List[CategoryNode] = []
    for raw in nodes:
        code = raw['code']
        level = int(raw['level'])
        node_id = category_id_for_code(code)
        parent_id = parent.id if parent else None

        if level > 2:
            raise ValueError(f'Category {code!r} exceeds max depth of 2 (level={level})')

        if level == 1:
            l1_id, l2_id, l3_id = node_id, None, None
            path = (raw['name_ja'],)
        else:
            assert parent is not None
            l1_id = parent.l1_id
            l2_id, l3_id = node_id, None
            path = parent.path_names + (raw['name_ja'],)

        children = raw.get('children') or []
        if children and level >= 2:
            raise ValueError(f'Category {code!r} at level {level} cannot have children')

        node = CategoryNode(
            id=node_id,
            code=code,
            name_ja=raw['name_ja'],
            level=level,
            parent_id=parent_id,
            l1_id=l1_id,
            l2_id=l2_id,
            l3_id=l3_id,
            path_names=path,
        )
        flat.append(node)
        flat.extend(_flatten_nodes(children, node))
    return flat


@lru_cache(maxsize=1)
def _load_yaml_taxonomy() -> Dict[str, CategoryNode]:
    if not _TAXONOMY_PATH.is_file():
        raise FileNotFoundError(f'Taxonomy file not found: {_TAXONOMY_PATH}')

    with _TAXONOMY_PATH.open(encoding='utf-8') as handle:
        data = yaml.safe_load(handle)

    nodes = _flatten_nodes(data.get('nodes') or [])
    by_code = {node.code: node for node in nodes}
    if UNKNOWN_CODE not in by_code:
        raise ValueError(f'Taxonomy must include {UNKNOWN_CODE!r} node')

    logger.debug('Loaded %d category node(s) from YAML taxonomy', len(by_code))
    return by_code


def _build_taxonomy_from_db_rows(rows: List[Dict[str, Any]]) -> Dict[str, CategoryNode]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (int(row['level']), int(row.get('sort_order') or 0), str(row['code'])),
    )
    by_id: Dict[str, CategoryNode] = {}
    by_code: Dict[str, CategoryNode] = {}

    for raw in sorted_rows:
        node_id = str(raw['id'])
        level = int(raw['level'])
        parent_id = str(raw['parent_id']) if raw.get('parent_id') else None
        name_ja = str(raw['name_ja'])

        if level == 1:
            l1_id, l2_id, l3_id = node_id, None, None
            path = (name_ja,)
        else:
            parent = by_id.get(str(raw['parent_id']))
            if parent is None:
                raise ValueError(f'Missing parent for category {raw.get("code")!r}')
            l1_id = parent.l1_id
            l2_id, l3_id = node_id, None
            path = parent.path_names + (name_ja,)

        node = CategoryNode(
            id=node_id,
            code=str(raw['code']),
            name_ja=name_ja,
            level=level,
            parent_id=parent_id,
            l1_id=l1_id,
            l2_id=l2_id,
            l3_id=l3_id,
            path_names=path,
        )
        by_id[node_id] = node
        by_code[node.code] = node

    if UNKNOWN_CODE not in by_code:
        raise ValueError(f'Tenant taxonomy must include {UNKNOWN_CODE!r} node')

    return by_code


def _load_tenant_taxonomy_from_db(tenant_type: str, tenant_id: str) -> Optional[Dict[str, CategoryNode]]:
    from services.supabase_client import get_supabase_client

    client = get_supabase_client()
    response = (
        client.table('category_nodes')
        .select('id, code, name_ja, level, parent_id, sort_order')
        .eq('tenant_type', tenant_type)
        .eq('tenant_id', tenant_id)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None

    taxonomy = _build_taxonomy_from_db_rows(rows)
    logger.debug(
        'Loaded %d tenant category node(s) for %s:%s',
        len(taxonomy),
        tenant_type,
        tenant_id,
    )
    return taxonomy


@lru_cache(maxsize=128)
def load_category_taxonomy(tenant_type: str = '', tenant_id: str = '') -> Dict[str, CategoryNode]:
    if tenant_type and tenant_id and is_supabase_configured():
        try:
            tenant_taxonomy = _load_tenant_taxonomy_from_db(tenant_type, tenant_id)
            if tenant_taxonomy:
                return tenant_taxonomy
        except Exception:
            logger.exception('Failed to load tenant taxonomy for %s:%s', tenant_type, tenant_id)
    return _load_yaml_taxonomy()


def load_category_taxonomy_for_tenant(tenant: Optional[TenantContext] = None) -> Dict[str, CategoryNode]:
    if tenant is None:
        return load_category_taxonomy()
    return load_category_taxonomy(tenant.tenant_type, tenant.tenant_id)


def resolve_code(code: Optional[str], tenant: Optional[TenantContext] = None) -> CategoryNode:
    taxonomy = load_category_taxonomy_for_tenant(tenant)
    if not code or not isinstance(code, str):
        return taxonomy[UNKNOWN_CODE]

    normalized = code.strip()
    normalized = _LEGACY_L3_TO_L2.get(normalized, normalized)
    node = taxonomy.get(normalized)
    if node is None:
        logger.warning('Unknown category code %r; falling back to %s', code, UNKNOWN_CODE)
        return taxonomy[UNKNOWN_CODE]
    return node


def format_category_path(node: CategoryNode) -> str:
    return ' > '.join(node.path_names)


def reset_category_taxonomy_cache_for_tests() -> None:
    load_category_taxonomy.cache_clear()
    _load_yaml_taxonomy.cache_clear()
