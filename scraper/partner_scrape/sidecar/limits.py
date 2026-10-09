"""Abuse and cost controls: sliding-window rate limits, persisted daily spend
cap, and optional Turnstile verification.

Rate-limit counters live in memory (single replica; a restart resets them).
The daily spend counter is persisted per UTC day at
``state/update-spend/<YYYY-MM-DD>.json`` in the history store so restarts keep
it. Everything time-based takes an injected clock.
"""

from __future__ import annotations

import json
import math
import threading
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from datetime import datetime
from typing import Callable, Mapping, Protocol

from partner_scrape.sidecar.pricing import cost_usd
from partner_scrape.storage import Store

WINDOW_SECONDS = 3600.0
TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        super().__init__(f"rate limited; retry after {retry_after}s")
        self.retry_after = retry_after


class SlidingWindow:
    """At most `limit` hits per `window` seconds per key."""

    def __init__(self, limit: int, window: float = WINDOW_SECONDS):
        self.limit, self.window = limit, window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float) -> int | None:
        """Record a hit. Return None if allowed, else seconds until a slot frees."""
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return max(1, math.ceil(self.window - (now - q[0])))
            q.append(now)
            return None


class SpendTracker:
    """Estimated dollars spent per UTC day, persisted in the history store."""

    def __init__(
        self,
        history: Store,
        daily_cap_usd: float,
        clock: Callable[[], datetime],
        prices: Mapping[str, tuple[float, float]] | None = None,
    ):
        self.history, self.cap, self.clock, self.prices = history, daily_cap_usd, clock, prices
        self._lock = threading.Lock()

    def _key(self) -> str:
        return f"state/update-spend/{self.clock().strftime('%Y-%m-%d')}.json"

    def spent(self) -> float:
        data = self.history.read_json(self._key())
        try:
            return float(data.get("usd", 0.0)) if isinstance(data, dict) else 0.0
        except (TypeError, ValueError):
            return 0.0

    def cap_reached(self) -> bool:
        return self.spent() >= self.cap

    def record(self, usage: list[Mapping[str, object]]) -> float:
        """Add the estimated cost of `usage`; returns the new day total."""
        cost = cost_usd(usage, self.prices)
        with self._lock:
            total = self.spent() + cost
            if cost > 0:
                self.history.write_json(self._key(), {"usd": round(total, 6)})
            return total


class TurnstileVerifier(Protocol):
    def verify(self, token: str, ip: str) -> bool: ...


class CloudflareTurnstile:
    """Production verifier (siteverify). Not used in tests; inject a fake there."""

    def __init__(self, secret: str, timeout: float = 5.0):
        self._secret, self._timeout = secret, timeout

    def verify(self, token: str, ip: str) -> bool:
        body = urllib.parse.urlencode(
            {"secret": self._secret, "response": token, "remoteip": ip}
        ).encode()
        try:
            with urllib.request.urlopen(
                urllib.request.Request(TURNSTILE_URL, data=body), timeout=self._timeout
            ) as resp:
                return bool(json.loads(resp.read()).get("success"))
        except Exception:  # fail closed
            return False


class Limits:
    """Facade the app calls; keeps the app free of limit bookkeeping."""

    def __init__(
        self,
        config,
        history: Store,
        clock: Callable[[], datetime],
        turnstile: TurnstileVerifier | None = None,
    ):
        self.clock = clock
        self.spend = SpendTracker(history, config.daily_spend_usd, clock, config.model_prices)
        self._ip_sessions = SlidingWindow(config.ip_sessions_per_hour)
        self._ip_messages = SlidingWindow(config.ip_messages_per_hour)
        self._listing_sessions = SlidingWindow(config.listing_sessions_per_hour)
        self._listing_messages = SlidingWindow(config.listing_messages_per_hour)
        if turnstile is None and config.turnstile_secret:
            turnstile = CloudflareTurnstile(config.turnstile_secret)
        self.turnstile = turnstile if config.turnstile_secret else None

    def _now(self) -> float:
        return self.clock().timestamp()

    def _hit(self, window: SlidingWindow, key: str) -> None:
        retry = window.check(key, self._now())
        if retry is not None:
            raise RateLimited(retry)

    def check_session_start(self, ip_hash: str, listing: str) -> None:
        self._hit(self._ip_sessions, ip_hash)
        self._hit(self._listing_sessions, listing)

    def check_message(self, ip_hash: str, listing: str) -> None:
        self._hit(self._ip_messages, ip_hash)
        self._hit(self._listing_messages, listing)

    def verify_turnstile(self, token: object, ip: str) -> bool:
        """True when Turnstile is off or the token verifies."""
        if self.turnstile is None:
            return True
        if not isinstance(token, str) or not token:
            return False
        return bool(self.turnstile.verify(token, ip))
