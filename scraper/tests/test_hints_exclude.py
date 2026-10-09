"""Exclude hints at normalize, and hints fingerprint in updates state
(sprint 044-006). Fakes only."""

from datetime import datetime

from partner_scrape.hints import HintStore, exclude_matcher, hints_fingerprint
from partner_scrape.normalize.run import run as normalize_run
from partner_scrape.storage import LocalStore
from partner_scrape.updates.checks import load_state
from partner_scrape.updates.proposer import FakeProposer
from tests.test_hints_consumption import page, put_hints
from tests.test_normalize_run import _event
from tests.test_updates_checks import CMOD_RECORD, cmod_snapshot
from tests.test_updates_job import GOOD, Env

ROSTER = [{"id": 1, "slug": "coastal", "name": "Coastal Roots Farm"},
          {"id": 2, "slug": "other", "name": "Other Org"}]
ORGS = {"src-a": "Coastal Roots Farm", "src-b": "Other Org"}
WHEN = datetime(2099, 6, 1, 10)


def ev(title, source="src-a"):
    return _event(source_id=source, title=title, start=WHEN)


def excl(*matches):
    return [{"kind": "exclude", "match": m, "reason": "r"} for m in matches]


def run(events, hints_by_slug, counts):
    m = {s: exclude_matcher(h) for s, h in hints_by_slug.items() if exclude_matcher(h)}
    return normalize_run(events, ROSTER, source_org_names=ORGS, today=WHEN.date(),
                         exclude_matchers=m, excluded_counts=counts)


def titles(opps):
    return sorted(o.title for o in opps)


# ------------------------------------------------------------------ matcher

def test_matcher_substring_regex_nonmatch_and_none():
    assert exclude_matcher([]) is None and exclude_matcher([{"kind": "note", "text": "x"}]) is None
    m = exclude_matcher(excl("Yoga", "re:^cancel+ed\\b"))
    assert m("Morning YOGA class") and m("Cancelled: Robotics") and m("canceled")
    assert not m("Robotics") and not m("Not cancelled")  # regex anchored at start


def test_matcher_regex_safety():
    # invalid, empty and over-long regexes are skipped, never raise
    m = exclude_matcher(excl("re:(unclosed", "re:", "re:" + "a" * 101, "keep-out"))
    assert m("keep-out event") and not m("aaa")
    assert exclude_matcher(excl("re:(unclosed")) is None
    # very long text is capped before matching
    m = exclude_matcher(excl("re:needle$"))
    assert not m("x" * 600 + "needle")


# ---------------------------------------------------------------- normalize

def test_normalize_drops_matches_only_for_that_partner_and_counts():
    counts = {}
    events = [ev("Yoga for kids"), ev("Robotics"), ev("Yoga night", "src-b")]
    opps = run(events, {"coastal": excl("yoga")}, counts)
    assert titles(opps) == ["Robotics", "Yoga night"]
    assert counts == {"coastal": 1}


def test_normalize_no_hints_identical():
    events = [ev("Yoga for kids"), ev("Robotics")]
    counts = {}
    assert titles(run(events, {}, counts)) == titles(
        normalize_run(events, ROSTER, source_org_names=ORGS, today=WHEN.date()))
    assert counts == {}


def test_normalize_regex_exclude():
    counts = {}
    opps = run([ev("Camp A"), ev("Camp B"), ev("Robotics")], {"coastal": excl("re:^camp [ab]$")}, counts)
    assert titles(opps) == ["Robotics"] and counts == {"coastal": 2}


# --------------------------------------------------- updates hints fingerprint

def test_fingerprint_stable_and_empty():
    assert hints_fingerprint([]) == ""
    a = [{"kind": "note", "text": "x", "b": 1}]
    assert hints_fingerprint(a) == hints_fingerprint([{"b": 1, "text": "x", "kind": "note"}])
    assert hints_fingerprint(a) != hints_fingerprint([{"kind": "note", "text": "y"}])


def test_hint_change_reexamines_unchanged_partner(tmp_path):
    e = Env(tmp_path)
    e.add(dict(CMOD_RECORD, id=1), cmod_snapshot())
    hdir = tmp_path / "hints"
    store = HintStore(LocalStore(hdir))
    # Run 1 without hints: examined, state saved with the plain snapshot hash.
    r1 = e.run(FakeProposer({"cmod": GOOD}), hint_store=store, no_llm=False, dry_run=False)
    assert len(r1.outcomes) == 1
    plain = load_state(e.cache)["cmod"]
    assert "+h:" not in plain
    # Run 2, nothing changed (and snapshot has no redirect): skipped.
    snap = cmod_snapshot()
    snap["redirects"] = []
    # Run 3 after a hint is saved: re-examined, state records the fingerprint.
    put_hints(tmp_path, "cmod", [{"kind": "note", "text": "events at /shows"}])
    store2 = HintStore(LocalStore(hdir))
    e2 = e.run(FakeProposer({"cmod": GOOD}), hint_store=store2, all_partners=False)
    assert [o.slug for o in e2.outcomes] == ["cmod"]
    hashed = load_state(e.cache)["cmod"]
    assert hashed.startswith(plain) and "+h:" in hashed
    # Run 4, same hints: state matches (unchanged partner not re-examined
    # unless a redirect keeps it in play).
    assert hashed == load_state(e.cache)["cmod"]


def test_run_checks_skips_when_hints_and_snapshot_unchanged(tmp_path):
    from partner_scrape.updates.checks import run_checks, save_state, snapshot_hash

    e = Env(tmp_path)
    snap = cmod_snapshot()
    snap["redirects"] = []
    e.add(dict(CMOD_RECORD, id=1), snap)
    roster = [dict(CMOD_RECORD, id=1)]
    h = snapshot_hash(snap)
    save_state(e.cache, {"cmod": h})
    # No fingerprint: unchanged -> skipped.
    assert run_checks(roster, e.history, e.cache).skipped_unchanged == 1
    assert run_checks(roster, e.history, e.cache, hints_fp=lambda s: "").skipped_unchanged == 1
    # Hints appear: examined.
    rep = run_checks(roster, e.history, e.cache, hints_fp=lambda s: "abc")
    assert rep.examined == 1 and rep.new_state["cmod"] == f"{h}+h:abc"
    # Same fingerprint already saved: skipped again.
    save_state(e.cache, {"cmod": f"{h}+h:abc"})
    assert run_checks(roster, e.history, e.cache, hints_fp=lambda s: "abc").skipped_unchanged == 1
    # Hints removed: state differs, re-examined.
    assert run_checks(roster, e.history, e.cache, hints_fp=lambda s: "").examined == 1
