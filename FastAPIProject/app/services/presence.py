from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock


_lock = Lock()
_last_seen: dict[int, datetime] = {}


def mark_user_active(user_id: int) -> None:
    with _lock:
        _last_seen[user_id] = datetime.utcnow()


def mark_user_inactive(user_id: int) -> None:
    with _lock:
        _last_seen.pop(user_id, None)


def is_user_active(user_id: int, ttl_seconds: int) -> bool:
    with _lock:
        ts = _last_seen.get(user_id)
    if not ts:
        return False
    return datetime.utcnow() - ts <= timedelta(seconds=max(1, ttl_seconds))
