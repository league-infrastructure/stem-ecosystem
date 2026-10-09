"""Abuse and cost controls: rate limits, caps, persisted spend, Turnstile. Fakes only."""

from datetime import timedelta

import pytest

pytest.importorskip("starlette")
pytest.importorskip("httpx")

from partner_scrape.sidecar.agent import AgentTurn  # noqa: E402
from partner_scrape.sidecar.app import create_app  # noqa: E402
from partner_scrape.sidecar.config import SidecarConfig  # noqa: E402
from partner_scrape.sidecar.llm import Usage  # noqa: E402
from partner_scrape.sidecar.pricing import cost_usd, parse_price_overrides  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from .test_api import Clock, SALT, ORIGIN, stores, start  # noqa: E402,F401


class CostlyAgent:
    """1M output tokens of sonnet = $15 per turn."""

    def respond(self, session, text):
        return AgentTurn("ok", None, [], [Usage("claude-sonnet-5-5", 0, 1_000_000)])


class FakeTurnstile:
    def __init__(self, ok=True):
        self.ok, self.seen = ok, []

    def verify(self, token, ip):
        self.seen.append((token, ip))
        return self.ok


def make(stores, clock=None, agent=None, turnstile=None, **cfg):
    data, history, hints = stores
    config = SidecarConfig(allowed_origins=(ORIGIN,), ip_hash_salt=SALT, **cfg)
    app = create_app(config, data_store=data, history_store=history, hints_store=hints,
                     agent=agent, clock=clock or Clock(), turnstile=turnstile)
    return TestClient(app)


def msg(c, sid, text="hi"):
    return c.post(f"/v1/sessions/{sid}/messages", json={"text": text})


def test_session_rate_limit_429_with_retry_after_then_window_slides(stores):
    clock = Clock()
    c = make(stores, clock, ip_sessions_per_hour=2)
    assert start(c).status_code == 201
    assert start(c).status_code == 201
    r = start(c)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
    assert int(r.headers["Retry-After"]) == 3600
    clock.now += timedelta(hours=1, seconds=1)
    assert start(c).status_code == 201


def test_message_rate_limit_per_ip(stores):
    c = make(stores, ip_messages_per_hour=2)
    sid = start(c).json()["session_id"]
    assert msg(c, sid).status_code == 200
    assert msg(c, sid).status_code == 200
    r = msg(c, sid)
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_per_listing_limit_spans_ips(stores):
    c = make(stores, listing_sessions_per_hour=1)
    assert c.post("/v1/sessions", json={"type": "partner", "slug": "acme"},
                  headers={"x-forwarded-for": "1.1.1.1"}).status_code == 201
    r = c.post("/v1/sessions", json={"type": "partner", "slug": "acme"},
               headers={"x-forwarded-for": "2.2.2.2"})
    assert r.status_code == 429
    # a different listing is unaffected
    assert c.post("/v1/sessions", json={"type": "opportunity", "slug": "opp-1"},
                  headers={"x-forwarded-for": "3.3.3.3"}).status_code == 201


def test_long_message_413_and_turn_cap_ends_session(stores):
    c = make(stores, max_message_chars=5, max_turns=1)
    sid = start(c).json()["session_id"]
    assert msg(c, sid, "x" * 6).status_code == 413
    r = msg(c, sid, "hello")
    assert r.status_code == 200 and r.json()["status"] == "ended"
    assert r.json()["ended_reason"] == "turn_cap"
    assert msg(c, sid, "again").status_code == 409


def test_spend_cap_blocks_new_sessions_and_messages_and_persists(stores):
    clock = Clock()
    c = make(stores, clock, agent=CostlyAgent(), daily_spend_usd=10.0)
    sid = start(c).json()["session_id"]
    assert msg(c, sid).status_code == 200  # $15 spent
    r = start(c)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "spend_cap_reached"
    assert r.json()["error"]["fallback_email"]
    r = msg(c, sid)
    assert r.status_code == 503 and r.json()["error"]["code"] == "spend_cap_reached"
    # persisted: a brand-new app on the same history store still refuses
    c2 = make(stores, clock, agent=CostlyAgent(), daily_spend_usd=10.0)
    assert start(c2).status_code == 503
    assert stores[1].read_json("state/update-spend/2026-10-09.json")["usd"] == 15.0
    # next UTC day starts fresh
    clock.now += timedelta(days=1)
    assert start(c2).status_code == 201


def test_free_fake_usage_does_not_spend(stores):
    c = make(stores, daily_spend_usd=0.01)
    sid = start(c).json()["session_id"]
    assert msg(c, sid).status_code == 200
    assert start(c).status_code == 201


def test_turnstile_off_without_secret(stores):
    fake = FakeTurnstile(ok=False)
    c = make(stores, turnstile=fake)
    assert start(c).status_code == 201
    assert fake.seen == []


def test_turnstile_enforced_with_secret(stores):
    fake = FakeTurnstile(ok=True)
    c = make(stores, turnstile=fake, turnstile_secret="fake-secret")
    r = start(c)  # no token
    assert r.status_code == 403 and r.json()["error"]["code"] == "turnstile_failed"
    ok = c.post("/v1/sessions", json={"type": "partner", "slug": "acme", "turnstile_token": "tok"})
    assert ok.status_code == 201 and fake.seen[0][0] == "tok"
    bad = make(stores, turnstile=FakeTurnstile(ok=False), turnstile_secret="fake-secret")
    r = bad.post("/v1/sessions", json={"type": "partner", "slug": "acme", "turnstile_token": "t"})
    assert r.status_code == 403


def test_config_env_defaults_and_overrides():
    d = SidecarConfig.from_env({})
    assert d.daily_spend_usd == 5.0 and d.turnstile_secret is None
    assert d.ip_sessions_per_hour == 10 and d.ip_messages_per_hour == 60
    c = SidecarConfig.from_env({
        "UPDATES_DAILY_SPEND_USD": "2.5", "TURNSTILE_SECRET": "s",
        "UPDATES_IP_SESSIONS_PER_HOUR": "3", "UPDATES_LISTING_MESSAGES_PER_HOUR": "7",
        "UPDATES_MODEL_PRICES": '{"claude-sonnet-5-5": [4, 20]}',
    })
    assert c.daily_spend_usd == 2.5 and c.turnstile_secret == "s"
    assert c.ip_sessions_per_hour == 3 and c.listing_messages_per_hour == 7
    assert c.model_prices == {"claude-sonnet-5-5": (4.0, 20.0)}
    with pytest.raises(ValueError):
        SidecarConfig.from_env({"UPDATES_DAILY_SPEND_USD": "abc"})


def test_pricing():
    u = [{"model": "claude-sonnet-5-5", "input_tokens": 1_000_000, "output_tokens": 1_000_000}]
    assert cost_usd(u) == 18.0
    assert cost_usd(u, parse_price_overrides('{"claude-sonnet-5-5": [1, 1]}')) == 2.0
    assert cost_usd([{"model": "mystery", "input_tokens": 1_000_000}]) > 3.0  # conservative
    assert cost_usd([{"model": "fake-agent", "input_tokens": 99}]) == 0
