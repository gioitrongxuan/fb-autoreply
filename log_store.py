from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading


@dataclass
class LogEntry:
    sender_id: str
    direction: str  # "in" | "out"
    text: str
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_lock = threading.Lock()
_log: deque = deque(maxlen=200)
_sessions: dict = {}


def record(sender_id: str, direction: str, text: str):
    entry = LogEntry(sender_id=sender_id, direction=direction, text=text)
    with _lock:
        _log.append(entry)
        s = _sessions.setdefault(sender_id, {"msg_count": 0, "last_seen": None, "last_msg": ""})
        s["msg_count"] += 1
        s["last_seen"] = entry.ts.strftime("%H:%M:%S")
        if direction == "in":
            s["last_msg"] = text[:80]


def recent(limit: int = 100) -> list:
    with _lock:
        entries = list(_log)[-limit:]
    return [
        {
            "sender": e.sender_id[:4] + "***" if len(e.sender_id) > 4 else e.sender_id,
            "direction": e.direction,
            "text": e.text[:300],
            "ts": e.ts.strftime("%H:%M:%S"),
        }
        for e in reversed(entries)
    ]


def sessions() -> list:
    with _lock:
        data = dict(_sessions)
    return [
        {"sender": k[:4] + "***" if len(k) > 4 else k, **v}
        for k, v in sorted(data.items(), key=lambda x: x[1]["last_seen"] or "", reverse=True)
    ]


def stats() -> dict:
    with _lock:
        return {
            "total_messages": len(_log),
            "active_sessions": len(_sessions),
        }
