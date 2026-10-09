"""updates job end to end with LocalStore and FakeProposer (sprint 043-006)."""

import json
import re
from pathlib import Path

import pytest

from partner_scrape import cli
from partner_scrape.partners.records import load_roster, read_record, record_key
from partner_scrape.partners.writer import PartnerWriter
from partner_scrape.profiles.snapshot import write_snapshot_if_changed
from partner_scrape.storage import LocalStore
from partner_scrape.updates import job as J
from partner_scrape.updates.checks import load_state
from partner_scrape.updates.job import run_updates
from partner_scrape.updates.proposer import FakeProposer, FieldProposal, Proposal
from tests.test_updates_checks import CMOD_RECORD, cmod_snapshot, dead_twitter

CMOD = dict(CMOD_RECORD, id=1)


def fp(field, value, conf=0.95):
    return FieldProposal(field, value, conf, "seen on site")


GOOD = Proposal([fp("name", "Children's Museum of Discovery"),
                 fp("website", "https://visitcmod.org/")])


class Env:
    def __init__(self, tmp_path):
        self.data = LocalStore(tmp_path / "data")
        self.history = LocalStore(tmp_path / "history")
        self.cache = LocalStore(tmp_path / "cache")
        self.writer = PartnerWriter(self.data, self.history)

    def add(self, record, snapshot):
        self.writer.put_record(record["slug"], record, actor="test")
        write_snapshot_if_changed(self.history, record["slug"], snapshot)

    def run(self, proposer, **kw):
        roster = load_roster(self.data, validate=False).as_list()
        kw.setdefault("link_checker", dead_twitter)
        return run_updates(
            roster, data_store=self.data, history_store=self.history,
            cache_store=self.cache, writer=self.writer, proposer=proposer, **kw)


@pytest.fixture
def env(tmp_path):
    e = Env(tmp_path)
    e.add(CMOD, cmod_snapshot())
    return e


def changes(env):
    return (env.history.read_text("partners/changes.jsonl") or "").splitlines()


def test_cmod_end_to_end_applies_name_and_website(env):
    prop = FakeProposer({"cmod": GOOD})
    rep = env.run(prop)
    rec = read_record(env.data, "cmod")
    assert rec["name"] == "Children's Museum of Discovery"
    assert rec["website"] == "https://visitcmod.org/"
    assert rec["phone"] == CMOD["phone"]
    last = json.loads(changes(env)[-1])
    assert last["actor"] == "haiku" and last["archived"]
    assert [o.status for o in rep.outcomes] == ["applied"]
    assert rep.consolidated and env.data.read_json("partners.json")["partner_count"] == 1
    assert rep.state_saved and "cmod" in load_state(env.cache)
    # machine-readable report in the private history store
    data = json.loads(env.history.read_text(rep.report_key))
    p = data["partners"][0]
    assert p["old_record"]["name"] == CMOD["name"]
    assert p["applied"]["website"] == {"old": "http://sdcdm.org", "new": "https://visitcmod.org/"}
    assert p["proposed"]["fields"]
    text = "\n".join(rep.lines())
    assert "APPLIED cmod name:" in text and "REDIRECT cmod home" in text and "FLAG cmod" in text


def test_dry_run_writes_nothing_but_proposes(env):
    before = env.data.read_text(record_key("cmod"))
    n = len(changes(env))
    prop = FakeProposer({"cmod": GOOD})
    rep = env.run(prop, dry_run=True)
    assert prop.calls == ["cmod"]
    assert env.data.read_text(record_key("cmod")) == before
    assert len(changes(env)) == n
    assert not rep.consolidated and env.data.read_text("partners.json") is None
    assert load_state(env.cache) == {}
    assert any(l.startswith("WOULD APPLY cmod name") for l in rep.lines())
    assert any(l.startswith("PROPOSED cmod website") for l in rep.lines())
    assert json.loads(env.history.read_text(rep.report_key))["dry_run"] is True
    # proposals were cached: a real run now makes no further calls
    env.run(prop)
    assert prop.calls == ["cmod"]


def test_no_llm_flags_only(env):
    prop = FakeProposer({"cmod": GOOD})
    rep = env.run(prop, no_llm=True)
    assert prop.calls == [] and rep.outcomes[0].status == "flagged"
    assert read_record(env.data, "cmod")["name"] == CMOD["name"]
    assert load_state(env.cache) == {}
    assert any(l.startswith("FLAG cmod") for l in rep.lines())


def test_cap_defers_extras_and_reexamines_next_run(tmp_path):
    e = Env(tmp_path)
    props = {}
    for i, s in enumerate(["a", "b", "c"], start=1):
        rec = dict(CMOD, slug=s, id=i, name=f"Old {s}")
        snap = dict(cmod_snapshot(), slug=s)
        e.add(rec, snap)
        props[s] = Proposal([fp("name", f"New {s}")])
    rep = e.run(FakeProposer(props), max_changes=2)
    assert [o.status for o in rep.outcomes] == ["applied", "applied", "deferred"]
    assert read_record(e.data, "c")["name"] == "Old c"
    assert "DEFERRED c" in "\n".join(rep.lines())
    assert "c" not in load_state(e.cache) and "a" in load_state(e.cache)
    rep2 = e.run(FakeProposer(props), max_changes=2)
    # a and b still examine (notable redirect) but have nothing left to change
    assert {o.slug: o.status for o in rep2.outcomes} == {
        "a": "unchanged", "b": "unchanged", "c": "applied"}


def test_policy_rejection_leaves_record_untouched(env):
    bad = Proposal([fp("name", "Whatever", conf=0.3), fp("latitude", "1.0"),
                    fp("website", "not a url")])
    before = env.data.read_text(record_key("cmod"))
    rep = env.run(FakeProposer({"cmod": bad}))
    assert env.data.read_text(record_key("cmod")) == before
    assert len(changes(env)) == 1  # only the setup write
    assert not rep.consolidated
    assert len([l for l in rep.lines() if l.startswith("REJECTED cmod")]) == 3


class Boom:
    def propose(self, record, flags, pages):
        raise RuntimeError("llm down")


def test_one_failure_does_not_abort_run(tmp_path):
    e = Env(tmp_path)
    for i, s in enumerate(["a", "b"], start=1):
        e.add(dict(CMOD, slug=s, id=i, name=f"Old {s}"), dict(cmod_snapshot(), slug=s))

    class Mixed:
        def propose(self, record, flags, pages):
            if record["slug"] == "a":
                raise RuntimeError("llm down")
            return Proposal([fp("name", "New b")])

    rep = e.run(Mixed())
    assert [o.status for o in rep.outcomes] == ["error", "applied"]
    assert "ERROR a: RuntimeError: llm down" in "\n".join(rep.lines())
    assert "a" not in load_state(e.cache) and "b" in load_state(e.cache)


def test_writer_called_only_with_policy_output(env, monkeypatch):
    calls = []
    real = env.writer.put_record
    env.writer.put_record = lambda slug, rec, actor: calls.append((slug, rec, actor)) or real(slug, rec, actor=actor)
    seen = []
    orig = J.apply_policy
    monkeypatch.setattr(J, "apply_policy", lambda *a, **k: seen.append(orig(*a, **k)) or seen[-1])
    env.run(FakeProposer({"cmod": GOOD}))
    assert len(calls) == 1 and calls[0][1] is seen[0].applied and calls[0][2] == "haiku"


def test_no_code_path_reaches_writer_except_job():
    root = Path(J.__file__).parent
    users = {p.name: len(re.findall(r"\.put_record\(", p.read_text()))
             for p in root.glob("*.py")}
    assert {k: v for k, v in users.items() if v} == {"job.py": 1}
    src = (root / "job.py").read_text()
    assert "put_record(pc.slug, out.policy.applied, actor=ACTOR)" in src


def test_cli_registers_updates_flags():
    args = cli._build_parser().parse_args(
        ["updates", "--dry-run", "--no-llm", "--max-changes", "3", "--slug", "x", "--all"])
    assert (args.dry_run, args.no_llm, args.max_changes, args.slug, args.all) == (
        True, True, 3, "x", True)
    assert cli._build_parser().parse_args(["updates"]).max_changes == 20


def test_event_quality_in_report_in_dry_and_real_runs(env):
    env.data.write_json("partners/cmod/events.json", {"events": [
        {"title": "Holiday Hours", "date_start": "2026-10-13T10:00:00", "link": "",
         "description": "", "age_grade_level": [], "cost_range": "Free"}]})
    keys = lambda: sorted(env.data.list(""))
    before = {k: env.data.read_text(k) for k in keys()}
    rep = env.run(FakeProposer({}), dry_run=True, today=__import__("datetime").date(2026, 10, 8))
    assert {k: env.data.read_text(k) for k in keys()} == before
    assert any(l.startswith("QUALITY cmod non_event") for l in rep.lines())
    data = json.loads(env.history.read_text(rep.report_key))
    assert data["event_quality"]["counts"]["non_event"] == 1
    assert data["event_quality"]["partners"]["cmod"][0]["check"] == "non_event"
    rep2 = env.run(FakeProposer({}), no_llm=True)
    assert any(l.startswith("event-quality:") for l in rep2.lines())
