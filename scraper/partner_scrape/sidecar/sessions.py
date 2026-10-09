"""In-memory update sessions. The unguessable id is the capability."""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from partner_scrape.sidecar.resolver import Entity


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Session:
    id: str
    entity: Entity
    started: datetime
    last_active: datetime
    ip_hash: str
    messages: list[dict[str, str]] = field(default_factory=list)
    proposed_hints: list[dict[str, Any]] = field(default_factory=list)
    status: str = "active"  # active | ended
    ended_reason: str | None = None  # guard | turn_cap
    confirmed: bool = False
    #: Guard category and reason when the guard ended the session (logged).
    guard_reason: str | None = None
    #: Token usage of every model call, for spend accounting.
    usage: list[dict[str, Any]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def user_turns(self) -> int:
        return sum(1 for m in self.messages if m["role"] == "user")

    def transcript(self) -> dict[str, Any]:
        return {
            "session_id": self.id,
            "entity": self.entity.public(),
            "started": _iso(self.started),
            "updated": _iso(self.last_active),
            "ip_hash": self.ip_hash,
            "status": self.status,
            "ended_reason": self.ended_reason,
            "confirmed": self.confirmed,
            "guard_reason": self.guard_reason,
            "usage": self.usage,
            "messages": self.messages,
            "proposed_hints": self.proposed_hints,
        }


class SessionStore:
    """Sessions keyed by id; idle ones expire (and are forgotten)."""

    def __init__(self, idle_minutes: int = 30, clock: Callable[[], datetime] = utcnow):
        self.idle = timedelta(minutes=idle_minutes)
        self.clock = clock
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, entity: Entity, ip_hash: str) -> Session:
        now = self.clock()
        s = Session(secrets.token_urlsafe(24), entity, now, now, ip_hash)  # 192 bits
        with self._lock:
            self._purge(now)
            self._sessions[s.id] = s
        return s

    def get(self, session_id: str) -> Session | None:
        """The live session, touching its idle timer; None if unknown or expired."""
        now = self.clock()
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                return None
            if now - s.last_active > self.idle:
                del self._sessions[session_id]
                return None
            s.last_active = now
            return s

    def _purge(self, now: datetime) -> None:
        for sid in [k for k, v in self._sessions.items() if now - v.last_active > self.idle]:
            del self._sessions[sid]
