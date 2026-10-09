"""Sidecar settings, read from the environment (never from files)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Mapping

DEFAULT_FALLBACK_EMAIL = "info@jointheleague.org"


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = (env.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from None
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value


@dataclass(frozen=True)
class SidecarConfig:
    allowed_origins: tuple[str, ...] = ()
    fallback_email: str = DEFAULT_FALLBACK_EMAIL
    max_turns: int = 12
    max_message_chars: int = 1000
    idle_minutes: int = 30
    #: Salt for IP hashing. Never logged or written anywhere. If the secrets
    #: bundle supplies none, a per-process random salt is used (hashes then
    #: differ across restarts, which is safe, just not correlatable).
    ip_hash_salt: str = field(default_factory=lambda: secrets.token_hex(16), repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "SidecarConfig":
        origins = tuple(
            o.strip().rstrip("/")
            for o in (env.get("UPDATES_ALLOWED_ORIGINS") or "").split(",")
            if o.strip()
        )
        salt = (env.get("IP_HASH_SALT") or "").strip() or secrets.token_hex(16)
        return cls(
            allowed_origins=origins,
            fallback_email=(env.get("UPDATES_FALLBACK_EMAIL") or "").strip()
            or DEFAULT_FALLBACK_EMAIL,
            max_turns=_int(env, "UPDATES_MAX_TURNS", 12),
            max_message_chars=_int(env, "UPDATES_MAX_MESSAGE_CHARS", 1000),
            idle_minutes=_int(env, "UPDATES_IDLE_MINUTES", 30),
            ip_hash_salt=salt,
        )
