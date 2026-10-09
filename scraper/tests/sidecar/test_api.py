"""Sidecar skeleton: API contract, resolver, transcripts. Fakes only."""

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("starlette")
pytest.importorskip("httpx")

from starlette.testclient import TestClient  # noqa: E402

from partner_scrape.sidecar.agent import AgentTurn  # noqa: E402
from partner_scrape.sidecar.app import create_app  # noqa: E402
from partner_scrape.sidecar.config import SidecarConfig  # noqa: E402
from partner_scrape.storage import LocalStore  # noqa: E402

ORIGIN = "https://site.example"
SALT = "test-salt"
PAGE = {"kind": "page", "role": "contact", "url": "https://www.acme.org/contact"}


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


class ScriptedAgent:
    def __init__(self, proposals=None):
        self.proposals = proposals
        self.calls = []

    def respond(self, session, text):
        self.calls.append(text)
        return AgentTurn("ok", self.proposals, ["rejected: x"])


@pytest.fixture
def stores(tmp_path):
    data, history, hints = (LocalStore(tmp_path / n) for n in ("d", "h", "hi"))
    data.write_json("partners/acme/partner.json", {
        "slug": "acme", "id": 7, "name": "Acme Labs", "website": "https://www.acme.org/",
    })
    data.write_json("partners.json", {"partners": [{"id": 7, "slug": "acme", "name": "Acme Labs"}]})
    data.write_json("opportunities.json", [{
        "slug": "opp-1", "title": "Robot Camp", "partner_id": 7,
        "link": "https://events.acme.org/robot-camp",
    }, {"slug": "opp-2", "title": "Orphan", "link": "https://other.org/x"}])
    data.write_json("teams.json", {"teams": [{
        "team_id": "team-1", "name": "Team One", "website": "https://team1.example/",
        "organization_website": "www.school.example",
    }]})
    data.write_json("clubs.json", {"clubs": [{"club_id": "club-1", "name": "Club One"}]})
    data.write_json("places.json", {"places": [{
        "place_id": "place-1", "name": "Maker Lab", "website": "https://lab.example",
        "related_partner_id": 7,
    }]})
    return data, history, hints


def make(stores, agent=None, clock=None, **cfg):
    data, history, hints = stores
    config = SidecarConfig(
        allowed_origins=(ORIGIN,), ip_hash_salt=SALT, **cfg
    )
    app = create_app(
        config, data_store=data, history_store=history, hints_store=hints,
        agent=agent, clock=clock or Clock(),
    )
    return TestClient(app)


def start(client, type_="partner", slug="acme", **kw):
    return client.post("/v1/sessions", json={"type": type_, "slug": slug}, **kw)


def test_healthz(stores):
    r = make(stores).get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and "version" in r.json()


def test_start_session_shape(stores):
    r = start(make(stores))
    assert r.status_code == 201
    j = r.json()
    assert len(j["session_id"]) >= 32
    assert j["entity"] == {
        "type": "partner", "slug": "acme", "name": "Acme Labs", "partner_slug": "acme",
    }
    assert j["hints"] == [] and j["proposed_hints"] == []
    assert j["limits"] == {"max_message_chars": 1000, "max_turns": 12}
    assert j["turns_left"] == 12
    assert j["fallback_email"] and j["greeting"]


def test_resolver_types(stores):
    c = make(stores)
    opp = start(c, "opportunity", "opp-1").json()["entity"]
    assert opp["name"] == "Robot Camp" and opp["partner_slug"] == "acme"
    assert start(c, "opportunity", "opp-2").json()["entity"]["partner_slug"] is None
    assert start(c, "team", "team-1").json()["entity"]["name"] == "Team One"
    assert start(c, "club", "club-1").json()["entity"]["partner_slug"] is None
    place = start(c, "place", "place-1").json()["entity"]
    assert place["partner_slug"] == "acme"


@pytest.mark.parametrize("body", [
    {"type": "partner", "slug": "nope"},
    {"type": "team", "slug": "club-1"},
    {"type": "partner", "slug": "../etc"},
])
def test_unknown_entity_not_found(stores, body):
    r = make(stores).post("/v1/sessions", json=body)
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "not_found" and err["fallback_email"]


@pytest.mark.parametrize("body", [{"type": "dog", "slug": "x"}, {"type": "partner"}, [1]])
def test_bad_start_body(stores, body):
    r = make(stores).post("/v1/sessions", json=body)
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"


def test_invalid_json_and_unknown_route(stores):
    c = make(stores)
    r = c.post("/v1/sessions", content=b"{nope", headers={"content-type": "application/json"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"
    r = c.get("/nothing")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_message_flow_and_get(stores):
    agent = ScriptedAgent([PAGE])
    c = make(stores, agent)
    sid = start(c).json()["session_id"]
    r = c.post(f"/v1/sessions/{sid}/messages", json={"text": "contact is here"})
    assert r.status_code == 200
    j = r.json()
    assert j["reply"] == "ok" and j["proposed_hints"] == [PAGE]
    assert j["status"] == "active" and j["ended_reason"] is None
    assert j["turns_left"] == 11 and j["notices"] == ["rejected: x"]
    g = c.get(f"/v1/sessions/{sid}").json()
    assert g["status"] == "active"
    assert g["messages"] == [
        {"role": "user", "text": "contact is here"}, {"role": "assistant", "text": "ok"},
    ]


def test_message_validation(stores):
    c = make(stores, max_message_chars=10)
    sid = start(c).json()["session_id"]
    url = f"/v1/sessions/{sid}/messages"
    assert c.post(url, json={"text": "x" * 11}).status_code == 413
    assert c.post(url, json={"text": "x" * 11}).json()["error"]["code"] == "message_too_long"
    assert c.post(url, json={"text": "  "}).status_code == 400
    assert c.post(url, json={}).status_code == 400


def test_turn_cap_ends_session(stores):
    c = make(stores, max_turns=2)
    sid = start(c).json()["session_id"]
    url = f"/v1/sessions/{sid}/messages"
    assert c.post(url, json={"text": "a"}).json()["status"] == "active"
    last = c.post(url, json={"text": "b"}).json()
    assert last["status"] == "ended" and last["ended_reason"] == "turn_cap"
    assert last["turns_left"] == 0 and "@" in last["reply"]
    r = c.post(url, json={"text": "c"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "session_ended"


def test_idle_expiry_and_unknown_session(stores):
    clock = Clock()
    c = make(stores, clock=clock, idle_minutes=30)
    sid = start(c).json()["session_id"]
    clock.now += timedelta(minutes=29)
    assert c.get(f"/v1/sessions/{sid}").status_code == 200  # touch resets timer
    clock.now += timedelta(minutes=31)
    r = c.post(f"/v1/sessions/{sid}/messages", json={"text": "hi"})
    assert r.status_code == 410 and r.json()["error"]["code"] == "session_expired"
    assert c.get("/v1/sessions/doesnotexist").status_code == 410
    assert c.post("/v1/sessions/doesnotexist/confirm").status_code == 410


def test_confirm_writes_idempotently_via_hintwriter(stores):
    data, history, hints = stores
    c = make(stores, ScriptedAgent([PAGE]))
    sid = start(c).json()["session_id"]
    c.post(f"/v1/sessions/{sid}/messages", json={"text": "x"})
    r = c.post(f"/v1/sessions/{sid}/confirm")
    assert r.status_code == 200
    j = r.json()
    assert j["saved"] is True and j["hints"] == [PAGE]
    assert j["effective"] == "next scheduled scrape"
    assert hints.read_json("acme.json")["hints"] == [PAGE]
    log = history.read_text("hints/changes.jsonl")
    assert f"update-agent:{sid}" in log
    again = c.post(f"/v1/sessions/{sid}/confirm").json()
    assert again["saved"] is False and again["hints"] == [PAGE]
    assert hints.read_json("acme.json")["version"] == 1
    # a new session starts from the stored hints and shows them
    j2 = start(c).json()
    assert j2["hints"] == [PAGE] and j2["proposed_hints"] == [PAGE]


def test_confirm_with_nothing_proposed_is_noop(stores):
    c = make(stores)
    sid = start(c).json()["session_id"]
    assert c.post(f"/v1/sessions/{sid}/confirm").json()["saved"] is False
    assert not stores[2].exists("acme.json")


def test_confirm_rejects_invalid_proposal(stores):
    bad = {"kind": "page", "role": "contact", "url": "https://evil.example/x"}
    c = make(stores, ScriptedAgent([bad]))
    sid = start(c).json()["session_id"]
    c.post(f"/v1/sessions/{sid}/messages", json={"text": "x"})
    r = c.post(f"/v1/sessions/{sid}/confirm")
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"
    assert not stores[2].exists("acme.json")


def test_hints_for_opportunity_stored_under_its_slug(stores):
    page = {"kind": "page", "role": "other", "url": "https://events.acme.org/robot-camp"}
    c = make(stores, ScriptedAgent([page]))
    sid = start(c, "opportunity", "opp-1").json()["session_id"]
    c.post(f"/v1/sessions/{sid}/messages", json={"text": "x"})
    assert c.post(f"/v1/sessions/{sid}/confirm").json()["saved"] is True
    assert stores[2].read_json("opp-1.json")["hints"] == [page]


def test_transcript_written_each_turn_with_hashed_ip(stores):
    history = stores[1]
    c = make(stores)
    r = start(c, headers={"x-forwarded-for": "203.0.113.9, 10.0.0.1"})
    sid = r.json()["session_id"]
    keys = history.list("update-sessions/")
    assert keys == [f"update-sessions/20261009T120000Z-acme-{sid}.json"]
    c.post(f"/v1/sessions/{sid}/messages", json={"text": "hello"})
    t = history.read_json(keys[0])
    assert [m["role"] for m in t["messages"]] == ["user", "assistant"]
    assert t["ip_hash"] == hashlib.sha256(f"{SALT}203.0.113.9".encode()).hexdigest()
    raw = history.read_text(keys[0])
    assert "203.0.113.9" not in raw and SALT not in raw
    c.post(f"/v1/sessions/{sid}/confirm")
    assert history.read_json(keys[0])["confirmed"] is True
    assert len(history.list("update-sessions/")) == 1


def test_cors_only_configured_origins(stores):
    c = make(stores)
    ok = c.options("/v1/sessions", headers={
        "Origin": ORIGIN, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == ORIGIN
    assert "access-control-allow-credentials" not in ok.headers
    bad = c.options("/v1/sessions", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST",
    })
    assert "access-control-allow-origin" not in bad.headers
    g = c.get("/healthz", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in g.headers
    e = c.post("/v1/sessions", json={}, headers={"Origin": ORIGIN})
    assert e.status_code == 400 and e.headers["access-control-allow-origin"] == ORIGIN


def test_config_from_env():
    cfg = SidecarConfig.from_env({
        "UPDATES_ALLOWED_ORIGINS": "https://a.example/, https://b.example",
        "UPDATES_MAX_TURNS": "5", "IP_HASH_SALT": "s",
    })
    assert cfg.allowed_origins == ("https://a.example", "https://b.example")
    assert cfg.max_turns == 5 and cfg.max_message_chars == 1000 and cfg.ip_hash_salt == "s"
    assert SidecarConfig.from_env({}).allowed_origins == ()
    assert SidecarConfig.from_env({}).ip_hash_salt  # random per-process fallback
    with pytest.raises(ValueError):
        SidecarConfig.from_env({"UPDATES_MAX_TURNS": "abc"})
