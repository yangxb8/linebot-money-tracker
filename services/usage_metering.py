"""Request-scoped LLM billing context and operation type."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass
class UsageBillingContext:
    billing_line_user_id: str
    sender_line_user_id: str
    source_message_id: Optional[str]
    tenant_type: Optional[str]
    tenant_id: Optional[str]
    pooled: bool
    reply_language: str = 'ja'
    message_window_recorded: bool = False
    needs_receipt_headroom: bool = False


_billing_context: ContextVar[Optional[UsageBillingContext]] = ContextVar(
    'usage_billing_context',
    default=None,
)
_operation_type: ContextVar[str] = ContextVar('llm_operation_type', default='general')


def get_billing_context() -> Optional[UsageBillingContext]:
    return _billing_context.get()


def set_billing_context(ctx: Optional[UsageBillingContext]) -> Token:
    return _billing_context.set(ctx)


def reset_billing_context(token: Token) -> None:
    _billing_context.reset(token)


@contextmanager
def usage_billing_scope(ctx: UsageBillingContext) -> Iterator[UsageBillingContext]:
    token = set_billing_context(ctx)
    try:
        yield ctx
    finally:
        reset_billing_context(token)


def get_llm_operation_type() -> str:
    return _operation_type.get()


@contextmanager
def llm_operation_scope(operation_type: str) -> Iterator[None]:
    token = _operation_type.set(operation_type)
    try:
        yield
    finally:
        _operation_type.reset(token)
