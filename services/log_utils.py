from typing import Any, Optional


def truncate(text: Optional[str], max_len: int = 500) -> str:
    if text is None:
        return ''
    s = str(text)
    if len(s) <= max_len:
        return s
    return f'{s[:max_len]}… ({len(s)} chars total)'


def describe_bytes(data: Optional[bytes]) -> str:
    if not data:
        return '0 bytes'
    return f'{len(data)} bytes'
