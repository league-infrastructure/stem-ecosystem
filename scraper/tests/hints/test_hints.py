"""Tests for partner_scrape.hints (validation, store, archiving writer)."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from partner_scrape.hints import (
    CHANGES_KEY, HintError, HintStore, HintWriter, actor_for, domains_of,
    on_domain, validate_hints,
)
from partner_scrape.storage import LocalStore

DOMS = ["acme.org"]


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


def public(host):
    return ["93.184.216.34"]


class Fetcher:
    def __init__(self, final):
        self.final, self.calls = final, []

    def __call__(self, url):
        self.calls.append(url)
        return self.final


@pytest.fixture
def w(tmp_path):
    return HintWriter(
        LocalStore(tmp_path / "hints"), LocalStore(tmp_path / "history"),
        clock=Clock(), resolver=public,
    )


def v(hints, **kw):
    kw.setdefault("domains", DOMS)
    kw.setdefault("resolver", public)
    return validate_hints(hints, **kw)


def test_valid_kinds_accepted():
    out = v([
        {"kind": "page", "role": "events", "url": "https://www.acme.org/e"},
        {"kind": "page", "role": "about", "url": "https://sub.acme.org/a"},
        {"kind": "exclude", "match": "Bake Sale", "reason": "fundraiser"},
        {"kind": "exclude", "match": "re:^Gala\\b"},
        {"kind": "note", "text": "Camps run on the summer page."},
        {"kind": "identity", "name": "Acme Robotics"},
    ])
    assert len(out) == 6
    assert out[3]["reason"] == ""


@pytest.mark.parametrize("bad", [
    {"kind": "bogus"},
    {"kind": "note", "text": "x" * 501},
    {"kind": "note", "text": "ok", "extra": 1},
    {"kind": "note", "text": "  "},
    {"kind": "exclude", "match": "re:("},
    {"kind": "exclude", "match": "re:" + "a" * 101},
    {"kind": "exclude", "match": "a" * 101},
    {"kind": "page", "role": "nope", "url": "https://acme.org"},
    {"kind": "page", "role": "about", "url": "ftp://acme.org"},
    {"kind": "identity"},
    "not a dict",
])
def test_invalid_rejected(bad):
    with pytest.raises(HintError):
        v([bad])


def test_too_many_per_kind_and_total():
    with pytest.raises(HintError, match="too many note"):
        v([{"kind": "note", "text": f"n{i}"} for i in range(11)])
    with pytest.raises(HintError, match="too many hints"):
        v([{"kind": "note", "text": f"n{i}"} for i in range(42)])
    with pytest.raises(HintError):
        v("nope")


def test_duplicates_dropped():
    h = {"kind": "note", "text": "same"}
    assert v([h, dict(h)]) == [h]


def test_page_domain_rule():
    ok = {"kind": "page", "role": "about", "url": "https://events.acme.org/x"}
    assert v([ok])
    for url in ("https://evil.com/x", "https://acme.org.evil.com/", "https://notacme.org/"):
        with pytest.raises(HintError, match="not on"):
            v([{"kind": "page", "role": "about", "url": url}])
    assert on_domain("www.acme.org", ["acme.org"])
    assert domains_of("https://www.Acme.org/x", None, "other.com") == ["www.acme.org", "other.com"]


def test_identity_website_requires_redirect():
    f = Fetcher("https://new.org/home")
    h = {"kind": "identity", "website": "https://new.org"}
    out = v([h], current_website="https://old.org", fetcher=f)
    assert out == [{"kind": "identity", "website": "https://new.org"}]
    assert f.calls == ["https://old.org"]
    with pytest.raises(HintError, match="does not redirect"):
        v([h], current_website="https://old.org", fetcher=Fetcher("https://old.org/"))
    with pytest.raises(HintError):
        v([h], current_website="https://old.org")  # no fetcher
    with pytest.raises(HintError, match="no current website"):
        v([h], fetcher=f)


def test_identity_fetch_failure_rejected():
    def boom(url):
        raise OSError("down")
    with pytest.raises(HintError, match="could not verify"):
        v([{"kind": "identity", "website": "new.org"}], current_website="old.org", fetcher=boom)


def test_identity_no_private_fetch():
    f = Fetcher("http://10.0.0.1/")
    for cur, new in [("http://127.0.0.1", "new.org"), ("old.org", "10.0.0.1"),
                     ("http://localhost", "new.org"), ("old.org", "169.254.169.254")]:
        with pytest.raises(HintError, match="public host"):
            v([{"kind": "identity", "website": new}], current_website=cur, fetcher=f)
    # a hostname resolving to a private address is also refused
    with pytest.raises(HintError, match="public host"):
        v([{"kind": "identity", "website": "new.org"}], current_website="old.org",
          fetcher=f, resolver=lambda h: ["192.168.1.5"])
    assert f.calls == []


def test_store_absent_is_empty(w):
    s = HintStore(w.store)
    assert s.read("acme") is None
    assert s.hints("acme") == []
    assert s.get("acme")["hints"] == []
    with pytest.raises(ValueError):
        s.get("../x")


def test_writer_archives_and_logs(w):
    a = [{"kind": "note", "text": "one"}]
    b = [{"kind": "note", "text": "one"}, {"kind": "exclude", "match": "x", "reason": ""}]
    e1 = w.put_hints("acme", a, actor_for("s1"), domains=DOMS)
    assert e1["archived"] is None and e1["actor"] == "update-agent:s1"
    assert w.reader.read("acme")["version"] == 1
    assert w.history.list("hints/acme/") == []
    e2 = w.put_hints("acme", b, actor_for("s2"), domains=DOMS)
    assert e2["changed"] == ["exclude"]
    doc = w.reader.read("acme")
    assert doc["version"] == 2 and doc["hints"] == b
    keys = w.history.list("hints/acme/")
    assert len(keys) == 1 and e2["archived"] == f"history/{keys[0]}"
    assert json.loads(w.history.read_text(keys[0]))["hints"] == a
    log = [json.loads(x) for x in w.history.read_text(CHANGES_KEY).splitlines()]
    assert [x["actor"] for x in log] == ["update-agent:s1", "update-agent:s2"]


def test_identical_write_is_noop(w):
    a = [{"kind": "note", "text": "one"}]
    w.put_hints("acme", a, "update-agent:s", domains=DOMS)
    assert w.put_hints("acme", list(a), "update-agent:s", domains=DOMS) is None
    assert len(w.history.read_text(CHANGES_KEY).splitlines()) == 1
    assert w.reader.read("acme")["version"] == 1


def test_invalid_write_leaves_nothing(w):
    with pytest.raises(HintError):
        w.put_hints("acme", [{"kind": "bogus"}], "update-agent:s", domains=DOMS)
    assert w.reader.read("acme") is None
    assert w.history.read_text(CHANGES_KEY) is None


def test_writer_verifies_identity_with_injected_fetcher(tmp_path):
    w = HintWriter(LocalStore(tmp_path / "h"), LocalStore(tmp_path / "hist"),
                   clock=Clock(), fetcher=Fetcher("https://new.org/"), resolver=public)
    w.put_hints("acme", [{"kind": "identity", "website": "new.org"}], "update-agent:s",
                domains=DOMS, current_website="old.org")
    assert w.reader.hints("acme")[0]["website"] == "https://new.org"


def test_bad_slug(w):
    with pytest.raises(ValueError):
        w.put_hints("../x", [], "update-agent:s", domains=DOMS)
