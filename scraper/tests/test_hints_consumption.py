"""Scraper consumption of hints: profiles page overrides, updates context,
identity gating, event-source report (sprint 044-005). Fakes only."""

import json

import pytest

from partner_scrape.hints import HintStore, context_hints, load_hints, page_hint_urls
from partner_scrape.profiles.job import run_profiles
from partner_scrape.profiles.snapshot import read_snapshot
from partner_scrape.storage import LocalStore
from partner_scrape.updates.checks import load_state
from partner_scrape.updates.proposer import (
    FakeProposer, FieldProposal, Proposal, build_user_prompt, cache_hash,
)
from tests.test_profiles_job import PAGES, ROSTER, _polite
from tests.test_updates_checks import CMOD_RECORD, cmod_snapshot, dead_twitter
from tests.test_updates_job import GOOD, Env, changes, fp

from partner_scrape.partners.records import read_record


def put_hints(tmp_path, slug, hints):
    store = LocalStore(tmp_path / "hints")
    store.write_json(f"{slug}.json", {"slug": slug, "version": 1, "updated": "x", "hints": hints})
    return HintStore(store)


def page(role, url):
    return {"kind": "page", "role": role, "url": url}


# ------------------------------------------------------------- pure helpers

def test_page_hint_urls_filters_roles_and_off_domain():
    hints = [page("about", "https://alpha.org/who"), page("about", "https://evil.com/x"),
             page("events", "https://shows.alpha.org/e"), {"kind": "note", "text": "hi"}]
    got = page_hint_urls(hints, "https://alpha.org/", ("about", "contact", "other"))
    assert got == {"about": ["https://alpha.org/who"]}
    ev = page_hint_urls(hints, "https://alpha.org/", ("events",))
    assert ev == {"events": ["https://shows.alpha.org/e"]}


def test_load_hints_tolerates_none_missing_and_broken(tmp_path):
    assert load_hints(None, "alpha") == []
    store = HintStore(LocalStore(tmp_path / "hints"))
    assert load_hints(store, "alpha") == []
    (tmp_path / "hints").mkdir(exist_ok=True)
    (tmp_path / "hints" / "alpha.json").write_text("{not json")
    assert load_hints(store, "alpha") == []
    assert load_hints(store, "Bad Slug!") == []


def test_context_hints_identity_gated_by_evidence():
    hs = [{"kind": "note", "text": "events live on /shows"},
          {"kind": "identity", "name": "New Name", "website": "https://new.org"},
          page("about", "https://alpha.org/x")]
    ctx, ignored = context_hints(hs, allow_identity=False)
    assert [h["kind"] for h in ctx] == ["note"] and len(ignored) == 1
    ctx, ignored = context_hints(hs, allow_identity=True)
    assert [h["kind"] for h in ctx] == ["note", "identity"] and ignored == []


# ----------------------------------------------------------------- profiles

def test_profiles_without_hints_identical(tmp_path):
    a, b = LocalStore(tmp_path / "h1"), LocalStore(tmp_path / "h2")
    r1 = run_profiles(ROSTER[:1], _polite(tmp_path / "c1", PAGES), a)
    r2 = run_profiles(ROSTER[:1], _polite(tmp_path / "c2", PAGES), b,
                      hint_store=HintStore(LocalStore(tmp_path / "nohints")))
    assert r1.lines() == r2.lines() and not r2.hint_lines
    s1, s2 = read_snapshot(a, "alpha"), read_snapshot(b, "alpha")
    s1.pop("fetched_at"), s2.pop("fetched_at")
    assert s1["pages"].keys() == s2["pages"].keys()


def test_profiles_page_hints_override_discovery_and_add_other(tmp_path):
    pages = dict(PAGES)
    pages["https://alpha.org/team-story"] = (200, "<title>Story</title>", None)
    pages["https://alpha.org/find-us"] = (200, '<a href="tel:6195551212">x</a>', None)
    pages["https://alpha.org/faq"] = (200, "<title>FAQ</title>", None)
    store = put_hints(tmp_path, "alpha", [
        page("about", "https://alpha.org/team-story"),
        page("contact", "https://alpha.org/find-us"),
        page("other", "https://alpha.org/faq"),
        page("about", "https://elsewhere.com/about"),  # off-domain: ignored
        {"kind": "note", "text": "n"},
    ])
    hist = LocalStore(tmp_path / "hist")
    fetcher = _polite(tmp_path, pages)
    rep = run_profiles(ROSTER[:1], fetcher, hist, hint_store=store)
    snap = read_snapshot(hist, "alpha")
    assert snap["pages"]["about"]["url"] == "https://alpha.org/team-story"
    assert snap["pages"]["contact"]["url"] == "https://alpha.org/find-us"
    assert snap["pages"]["other"]["url"] == "https://alpha.org/faq"
    assert "https://elsewhere.com/about" not in json.dumps(snap)
    text = "\n".join(rep.lines())
    assert "HINT alpha page about: https://alpha.org/team-story" in text
    assert "HINT alpha page other: https://alpha.org/faq" in text
    assert "hints_used=3" in text


def test_profiles_partial_hint_keeps_discovery_for_other_role(tmp_path):
    pages = dict(PAGES)
    pages["https://alpha.org/team-story"] = (200, "<title>Story</title>", None)
    store = put_hints(tmp_path, "alpha", [page("about", "https://alpha.org/team-story")])
    hist = LocalStore(tmp_path / "hist")
    run_profiles(ROSTER[:1], _polite(tmp_path, pages), hist, hint_store=store)
    snap = read_snapshot(hist, "alpha")
    assert snap["pages"]["about"]["url"] == "https://alpha.org/team-story"
    assert snap["pages"]["contact"]["url"] == "https://alpha.org/contact"


# ------------------------------------------------------------------ updates

@pytest.fixture
def env(tmp_path):
    e = Env(tmp_path)
    e.add(dict(CMOD_RECORD, id=1), cmod_snapshot())
    return e


def test_updates_no_hints_matches_today(env, tmp_path):
    prop = FakeProposer({"cmod": GOOD})
    rep = env.run(prop, hint_store=HintStore(LocalStore(tmp_path / "hints")))
    assert not prop.hints_seen and rep.outcomes[0].status == "applied"
    assert not rep.event_source_hints
    assert not any(l.startswith(("HINT", "EVENT SOURCE")) for l in rep.lines())


def test_updates_note_and_identity_reach_proposer_with_evidence(env, tmp_path):
    store = put_hints(tmp_path, "cmod", [
        {"kind": "note", "text": "we rebranded to Children's Museum of Discovery"},
        {"kind": "identity", "name": "Children's Museum of Discovery"},
    ])
    prop = FakeProposer({"cmod": GOOD})
    rep = env.run(prop, hint_store=store)
    assert [h["kind"] for h in prop.hints_seen["cmod"]] == ["note", "identity"]
    text = "\n".join(rep.lines())
    assert "HINT cmod note:" in text and "HINT cmod identity:" in text
    data = json.loads(env.history.read_text(rep.report_key))
    assert len(data["partners"][0]["hints_used"]) == 2


def test_identity_without_evidence_ignored_and_policy_unbypassed(tmp_path):
    e = Env(tmp_path)
    snap = cmod_snapshot()
    snap["redirects"] = []
    snap["pages"]["home"]["final_url"] = "http://sdcdm.org"
    rec = dict(CMOD_RECORD, id=1, name="Children's Museum of Discovery",
               email="a@sdcdm.org", phone="760 233 7755", twitter="",
               facebook="https://facebook.com/childrensmuseumofdiscovery",
               instagram="https://www.instagram.com/childrensmuseumofdiscovery/")
    e.add(rec, snap)
    store = put_hints(tmp_path, "cmod", [
        {"kind": "note", "text": "call 619"},
        {"kind": "identity", "name": "Totally New", "website": "https://new.example.org"},
    ])
    # Medium flag only (phone mismatch); proposer tries a rebrand anyway.
    e.writer.put_record("cmod", dict(rec, phone="619-000-1111"), actor="test")
    prop = FakeProposer({"cmod": Proposal([fp("name", "Totally New"),
                                           fp("website", "https://new.example.org")])})
    rep = e.run(prop, hint_store=store)
    assert [h["kind"] for h in prop.hints_seen["cmod"]] == ["note"]
    assert any("identity hint ignored" in l for l in rep.lines())
    got = read_record(e.data, "cmod")
    assert got["name"] == "Children's Museum of Discovery"  # hints set no field
    assert got["website"] == CMOD_RECORD["website"]
    assert rep.outcomes[0].status != "applied"


def test_hints_change_cache_key_only_when_present():
    rec, pages = {"slug": "a"}, {"home": "t"}
    assert cache_hash(rec, pages) == cache_hash(rec, pages, [])
    assert cache_hash(rec, pages) != cache_hash(rec, pages, [{"kind": "note", "text": "x"}])
    p = build_user_prompt(rec, [], pages, [{"kind": "note", "text": "x"}])
    assert "PARTNER HINTS" in p and "PARTNER HINTS" not in build_user_prompt(rec, [], pages)


def test_updates_report_lists_event_source_hints(env, tmp_path):
    store = put_hints(tmp_path, "cmod", [
        page("events", "https://visitcmod.org/events"),
        page("camps", "https://sdcdm.org/camps"),
        page("programs", "https://evil.com/p"),  # off-domain
    ])
    rep = env.run(FakeProposer(), hint_store=store, dry_run=True, no_llm=True)
    # record website is sdcdm.org: only the on-domain hint is reported
    assert rep.event_source_hints == {"cmod": [
        {"role": "camps", "url": "https://sdcdm.org/camps"}]}
    text = "\n".join(rep.lines())
    assert "EVENT SOURCE HINT cmod camps: https://sdcdm.org/camps" in text
    assert "evil.com" not in text
    assert "event_source_hints" in json.loads(env.history.read_text(rep.report_key))
