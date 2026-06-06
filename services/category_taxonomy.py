from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

CATEGORY_NAMESPACE = uuid.UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479')
UNKNOWN_CODE = 'unknown'
_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'category_taxonomy_ja.yaml'


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

        if level == 1:
            l1_id, l2_id, l3_id = node_id, None, None
            path = (raw['name_ja'],)
        elif level == 2:
            assert parent is not None
            l1_id = parent.l1_id
            l2_id, l3_id = node_id, None
            path = parent.path_names + (raw['name_ja'],)
        else:
            assert parent is not None
            l1_id = parent.l1_id
            l2_id = parent.l2_id
            l3_id = node_id
            path = parent.path_names + (raw['name_ja'],)

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
        children = raw.get('children') or []
        flat.extend(_flatten_nodes(children, node))
    return flat


@lru_cache(maxsize=1)
def load_category_taxonomy() -> Dict[str, CategoryNode]:
    if not _TAXONOMY_PATH.is_file():
        raise FileNotFoundError(f'Taxonomy file not found: {_TAXONOMY_PATH}')

    with _TAXONOMY_PATH.open(encoding='utf-8') as handle:
        data = yaml.safe_load(handle)

    nodes = _flatten_nodes(data.get('nodes') or [])
    by_code = {node.code: node for node in nodes}
    if UNKNOWN_CODE not in by_code:
        raise ValueError(f'Taxonomy must include {UNKNOWN_CODE!r} node')

    logger.debug('Loaded %d category node(s) from taxonomy', len(by_code))
    return by_code


def resolve_code(code: Optional[str]) -> CategoryNode:
    taxonomy = load_category_taxonomy()
    if not code or not isinstance(code, str):
        return taxonomy[UNKNOWN_CODE]

    normalized = code.strip()
    node = taxonomy.get(normalized)
    if node is None:
        logger.warning('Unknown category code %r; falling back to %s', code, UNKNOWN_CODE)
        return taxonomy[UNKNOWN_CODE]
    return node


def format_category_path(node: CategoryNode) -> str:
    return ' > '.join(node.path_names)


def reset_category_taxonomy_cache_for_tests() -> None:
    load_category_taxonomy.cache_clear()
