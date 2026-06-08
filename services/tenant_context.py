from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


TENANT_USER = 'user'
TENANT_GROUP = 'group'
TENANT_ROOM = 'room'


@dataclass(frozen=True)
class TenantContext:
    """Expense ledger scope derived from a LINE message source."""

    tenant_type: str
    tenant_id: str
    logged_by_line_user_id: str

    @classmethod
    def personal(cls, line_user_id: str) -> TenantContext:
        return cls(
            tenant_type=TENANT_USER,
            tenant_id=line_user_id,
            logged_by_line_user_id=line_user_id,
        )

    @classmethod
    def group(cls, group_id: str, logged_by_line_user_id: str) -> TenantContext:
        return cls(
            tenant_type=TENANT_GROUP,
            tenant_id=group_id,
            logged_by_line_user_id=logged_by_line_user_id,
        )

    @classmethod
    def room(cls, room_id: str, logged_by_line_user_id: str) -> TenantContext:
        return cls(
            tenant_type=TENANT_ROOM,
            tenant_id=room_id,
            logged_by_line_user_id=logged_by_line_user_id,
        )

    @property
    def is_shared(self) -> bool:
        return self.tenant_type in (TENANT_GROUP, TENANT_ROOM)


def resolve_tenant_from_event(event, line_user_id: str) -> Optional[TenantContext]:
    """Map a LINE message event source to the expense ledger tenant."""
    if not line_user_id:
        return None

    source = getattr(event, 'source', None)
    if source is None:
        return TenantContext.personal(line_user_id)

    source_type = getattr(source, 'type', None)
    if not isinstance(source_type, str):
        return TenantContext.personal(line_user_id)

    normalized = source_type.strip().lower()
    if normalized == TENANT_GROUP:
        group_id = getattr(source, 'group_id', None) or getattr(source, 'groupId', None)
        if isinstance(group_id, str) and group_id.strip():
            return TenantContext.group(group_id.strip(), line_user_id)
        return None

    if normalized == TENANT_ROOM:
        room_id = getattr(source, 'room_id', None) or getattr(source, 'roomId', None)
        if isinstance(room_id, str) and room_id.strip():
            return TenantContext.room(room_id.strip(), line_user_id)
        return None

    return TenantContext.personal(line_user_id)


def resolve_tenant_for_console(
    line_user_id: str,
    *,
    group_id: Optional[str] = None,
    room_id: Optional[str] = None,
) -> TenantContext:
    """Resolve tenant for local console harness."""
    if group_id:
        return TenantContext.group(group_id, line_user_id)
    if room_id:
        return TenantContext.room(room_id, line_user_id)
    return TenantContext.personal(line_user_id)
