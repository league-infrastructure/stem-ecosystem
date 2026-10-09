"""Sidecar settings, read from the environment (never from files)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Mapping

from partner_scrape.sidecar.pricing import parse_price_overrides

DEFAULT_FALLBACK_EMAIL = "info@jointheleague.org"


def _float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = (env.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {raw!r}") from None
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value


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
    #: Guard backend: "anthropic" (default) or "openrouter" (optional, off).
    guard_backend: str = "anthropic"
    #: Model override for the OpenRouter guard (None = module default).
    openrouter_guard_model: str | None = None
    #: Sliding one-hour windows (in memory; a restart resets them).
    ip_sessions_per_hour: int = 10
    ip_messages_per_hour: int = 60
    listing_sessions_per_hour: int = 30
    listing_messages_per_hour: int = 150
    #: Estimated USD per UTC day across all sessions (persisted).
    daily_spend_usd: float = 5.0
    #: Extra/override per-model prices {model: (in, out)} $/MTok.
    model_prices: dict = field(default_factory=dict)
    #: Turnstile is enforced only when this is set.
    turnstile_secret: str | None = field(default=None, repr=False)
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
            guard_backend=(env.get("UPDATES_GUARD_BACKEND") or "").strip().lower() or "anthropic",
            openrouter_guard_model=(env.get("UPDATES_OPENROUTER_GUARD_MODEL") or "").strip() or None,
            ip_sessions_per_hour=_int(env, "UPDATES_IP_SESSIONS_PER_HOUR", 10),
            ip_messages_per_hour=_int(env, "UPDATES_IP_MESSAGES_PER_HOUR", 60),
            listing_sessions_per_hour=_int(env, "UPDATES_LISTING_SESSIONS_PER_HOUR", 30),
            listing_messages_per_hour=_int(env, "UPDATES_LISTING_MESSAGES_PER_HOUR", 150),
            daily_spend_usd=_float(env, "UPDATES_DAILY_SPEND_USD", 5.0),
            model_prices=parse_price_overrides(env.get("UPDATES_MODEL_PRICES")),
            turnstile_secret=(env.get("TURNSTILE_SECRET") or "").strip() or None,
            ip_hash_salt=salt,
        )
