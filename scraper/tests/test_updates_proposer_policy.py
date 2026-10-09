"""Haiku proposer cache and apply policy (sprint 043-005). No network."""

import json
from types import SimpleNamespace

import pytest

from partner_scrape.fetch.cache import write_cache_entry
from partner_scrape.fetch.fetcher import FetchResponse
from partner_scrape.storage import LocalStore
from partner_scrape.updates import proposer as P
from partner_scrape.updates.checks import compare_partner
from partner_scrape.updates.policy import apply_policy
from partner_scrape.updates.proposer import (
    FakeProposer,
    FieldProposal,
    Proposal,
    propose_for_partner,
)
from tests.test_updates_checks import CMOD_RECORD, cmod_snapshot, dead_twitter

HOME_HTML = (
    "<html><head><title>x</title><style>p{}</style></head><body><script>var a=1;</script>"
    "<h1>Children's Museum of Discovery</h1><p>Hands-on exhibits for kids.</p></body></html>"
)
ABOUT_HTML = "<body><p>" + " ".join(f"w{i}" for i in range(40)) + "</p></body>"


@pytest.fixture
def cache(tmp_path):
    return LocalStore(tmp_path / "cache")


def snapshot_with_pages(cache):
    snap = cmod_snapshot()
    snap["pages"]["about"] = {"url": "https://visitcmod.org/about", "error": ""}
    for url, body in (("http://sdcdm.org", HOME_HTML), ("https://visitcmod.org/about", ABOUT_HTML)):
        write_cache_entry(cache, url, FetchResponse(url=url, status=200, headers={}, body=body))
    return snap


def fp(field, value, conf=0.9, reason="r"):
    return FieldProposal(field, value, conf, reason)


def flags():
    return compare_partner(CMOD_RECORD, cmod_snapshot(), dead_twitter)


# ---------------------------------------------------------------- proposer

def test_page_text_strips_scripts_and_trims(cache):
    texts = P.load_page_texts(snapshot_with_pages(cache), cache)
    assert texts["home"] == "Children's Museum of Discovery Hands-on exhibits for kids."
    assert "about" in texts and "contact" not in texts
    assert len(P.html_to_text("<p>" + "a " * 10000 + "</p>")) <= P.MAX_PAGE_CHARS


def test_cache_hit_makes_zero_calls_and_change_busts_it(cache):
    snap = snapshot_with_pages(cache)
    fake = FakeProposer(default=Proposal([fp("name", "Children's Museum of Discovery")]))
    p1, hit1 = propose_for_partner(CMOD_RECORD, flags(), snap, cache, fake)
    p2, hit2 = propose_for_partner(CMOD_RECORD, flags(), snap, cache, fake)
    assert (hit1, hit2) == (False, True)
    assert len(fake.calls) == 1
    assert p2.to_dict() == p1.to_dict()
    key = P.cache_key("cmod", CMOD_RECORD, P.load_page_texts(snap, cache))
    assert cache.read_json(key)["proposal"]["fields"][0]["field"] == "name"
    assert key.startswith("updates/cmod/")
    # changed record -> miss
    propose_for_partner(dict(CMOD_RECORD, phone="1"), flags(), snap, cache, fake)
    assert len(fake.calls) == 2
    # changed page content -> miss
    write_cache_entry(cache, "http://sdcdm.org", FetchResponse(
        url="http://sdcdm.org", status=200, headers={}, body=HOME_HTML + "<p>new</p>"))
    propose_for_partner(CMOD_RECORD, flags(), snap, cache, fake)
    assert len(fake.calls) == 3


def test_prompt_version_is_part_of_key(cache, monkeypatch):
    texts = {"home": "x"}
    k1 = P.cache_key("cmod", CMOD_RECORD, texts)
    monkeypatch.setattr(P, "PROMPT_VERSION", 99)
    assert P.cache_key("cmod", CMOD_RECORD, texts) != k1


def test_copied_description_rejected_original_kept(cache):
    snap = snapshot_with_pages(cache)
    copied = " ".join(f"w{i}" for i in range(20))
    fake = FakeProposer(default=Proposal([fp("description", copied)]))
    p, _ = propose_for_partner(CMOD_RECORD, flags(), snap, cache, fake)
    assert p.get("description") is None and "verbatim" in p.notes[0]
    fake = FakeProposer(default=Proposal([fp("description", "A museum where kids explore science.")]))
    p, _ = propose_for_partner(dict(CMOD_RECORD, x="1"), flags(), snap, cache, fake)
    assert p.get("description") is not None


def test_short_quote_allowed():
    src = {"home": " ".join(f"w{i}" for i in range(40))}
    pr = Proposal([fp("description", "They say " + " ".join(f"w{i}" for i in range(14)))])
    assert P.drop_copied_description(pr, src).get("description")


def test_parse_proposal_validation():
    ok = P.parse_proposal({"fields": [{"field": "name", "value": "A", "confidence": 2, "reason": ""}]})
    assert ok.fields[0].confidence == 1.0
    for bad in ({}, {"fields": [{"field": "slug", "value": "a", "confidence": 1, "reason": ""}]},
                {"fields": [{"field": "name", "value": "a"}]}):
        with pytest.raises(P.ProposalError):
            P.parse_proposal(bad)


def test_anthropic_proposer_uses_haiku_schema_and_no_api_key(monkeypatch):
    seen = {}

    class Msgs:
        def create(self, **kw):
            seen.update(kw)
            body = json.dumps({"fields": [
                {"field": "phone", "value": "760-233-7755", "confidence": 0.95, "reason": "contact page"}]})
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=body)])

    class FakeAnthropic:
        def __init__(self, *a, **kw):
            seen["init"] = (a, kw)
            self.messages = Msgs()

    monkeypatch.setattr("anthropic.Anthropic", FakeAnthropic)
    out = P.AnthropicProposer().propose(CMOD_RECORD, flags(), {"home": "hello"})
    assert seen["init"] == ((), {})
    assert seen["model"] == "claude-haiku-4-5-20251001"
    assert seen["output_config"]["format"]["schema"] is P.PROPOSAL_JSON_SCHEMA
    assert "hello" in seen["messages"][0]["content"] and "phone_mismatch" in seen["messages"][0]["content"]
    assert out.get("phone").value == "760-233-7755"


# ------------------------------------------------------------------ policy

def run(*fields, record=None, flags_=None, snap=None, **kw):
    return apply_policy(
        record or CMOD_RECORD, Proposal(list(fields)),
        flags=flags() if flags_ is None else flags_,
        snapshot=cmod_snapshot() if snap is None else snap, **kw)


def review_fields(r):
    return [i["field"] for i in r.needs_review]


def moved_flag(severity="high"):
    return {"kind": "website_moved", "severity": severity, "field": "website"}


def test_applies_rebrand_fields_and_is_pure():
    before = json.dumps(CMOD_RECORD, sort_keys=True)
    r = run(fp("website", "https://visitcmod.org"),
            fp("linkedin", "https://linkedin.com/company/childrensmuseumofdiscovery"),
            fp("description", "A hands-on museum."), fp("name", "Children's Museum of Discovery"))
    assert r.applied_fields == ["website", "linkedin", "description", "name"]
    assert r.applied["website"] == "https://visitcmod.org" and r.applied["slug"] == "cmod"
    assert r.rejected == [] and r.needs_review == []
    assert json.dumps(CMOD_RECORD, sort_keys=True) == before


def test_confidence_threshold_configurable():
    p = fp("linkedin", "https://linkedin.com/company/x", conf=0.79)
    assert run(p).applied is None and "confidence" in run(p).rejected[0][1]
    assert run(p, min_confidence=0.7).applied_fields == ["linkedin"]
    assert run(fp("linkedin", "https://linkedin.com/company/x", conf=0.8)).applied_fields == ["linkedin"]


@pytest.mark.parametrize("name", ["slug", "id", "latitude", "longitude", "organization_type"])
def test_protected_fields_never_change(name):
    r = run(fp(name, "5", conf=1.0))
    assert r.applied is None and r.rejected[0][0] == name and r.needs_review == []


@pytest.mark.parametrize("name,value", [("logo_src", "https://visitcmod.org/l.png"), ("bogus", "5")])
def test_logo_and_unknown_fields_are_needs_review(name, value):
    r = run(fp(name, value, conf=1.0))
    assert r.applied is None and r.rejected == [] and review_fields(r) == [name]


@pytest.mark.parametrize("name", ["name", "phone", "email", "location", "website", "twitter", "description"])
def test_never_blank(name):
    r = run(fp(name, "  "))
    assert r.applied is None and r.applied_fields == []
    assert r.rejected[0][0] == name


def test_social_never_removed_but_dead_link_replaced_same_network_only():
    r = run(fp("twitter", ""))
    assert r.applied is None and "report-only" in r.rejected[0][1]
    r = run(fp("twitter", "https://x.com/cmod"))
    assert r.applied["twitter"] == "https://x.com/cmod"
    r = run(fp("twitter", "https://facebook.com/cmod"))
    assert r.applied is None and "not a twitter domain" in r.needs_review[0]["reason"]


def test_fill_empty_phone_email_social_applies():
    rec = dict(CMOD_RECORD, phone="", email="", linkedin="")
    r = run(fp("phone", "760-233-7755"), fp("email", "info@sdcdm.org"),
            fp("linkedin", "https://linkedin.com/company/sdcdm"), record=rec)
    assert r.applied_fields == ["phone", "email", "linkedin"] and r.needs_review == []


@pytest.mark.parametrize("name,cur,new", [
    ("email", "Samantha@theABF.org", "info@theabf.org"),
    ("email", "bradford@bsd.education", "info@bsd.education"),
    ("email", "lschmelz@csusm.edu", "cstem@csusm.edu"),
    ("phone", "8189150336", "7607670446"),
])
def test_changing_existing_email_phone_is_needs_review(name, cur, new):
    r = run(fp(name, new), record=dict(CMOD_RECORD, **{name: cur}))
    assert r.applied is None and r.rejected == []
    assert r.needs_review == [{"field": name, "current": cur, "proposed": new,
                               "reason": r.needs_review[0]["reason"]}]


@pytest.mark.parametrize("cur,new", [
    ("Discover U at San Diego Public Library", "San Diego Public Library"),
    ("EAA Chapter 14", "Chapter 14"),
    ("Coronado Public Library", "Coronado Library"),
])
def test_lossy_names_need_review_without_rebrand_evidence(cur, new):
    r = run(fp("name", new), record=dict(CMOD_RECORD, name=cur), flags_=[])
    assert r.applied is None and review_fields(r) == ["name"]
    # a medium website_moved is not rebrand evidence either
    r = run(fp("name", new), record=dict(CMOD_RECORD, name=cur), flags_=[moved_flag("medium")])
    assert r.applied is None
    r = run(fp("name", new), record=dict(CMOD_RECORD, name=cur), flags_=[moved_flag()])
    assert r.applied_fields == ["name"]


@pytest.mark.parametrize("name", ["name", "description", "location"])
def test_rebrand_fields_gated_on_high_website_moved(name):
    assert run(fp(name, "New value"), flags_=[]).needs_review
    assert run(fp(name, "New value"), flags_=[moved_flag()]).applied_fields == [name]


def test_website_gating():
    rec = dict(CMOD_RECORD, website="https://www.batiquitoslagoon.org")
    stage = "https://batiquitos-lagoon-foundation-142729.multiscreensite.com/"
    snap = cmod_snapshot()
    snap["pages"]["home"]["final_url"] = stage
    r = run(fp("website", stage), record=rec, flags_=[moved_flag()], snap=snap)
    assert r.applied is None and "staging" in r.needs_review[0]["reason"]
    # no website_moved flag
    assert run(fp("website", "https://visitcmod.org"), flags_=[]).needs_review
    # host differs from the observed redirect host
    r = run(fp("website", "https://other.org"))
    assert r.applied is None and "redirect host" in r.needs_review[0]["reason"]
    # www is ignored
    assert run(fp("website", "https://www.visitcmod.org/")).applied_fields == ["website"]


def test_staging_host_suffix_match():
    from partner_scrape.updates.policy import is_staging_host
    for h in ("x.multiscreensite.com", "a.b.wixsite.com", "foo.github.io", "squarespace.com"):
        assert is_staging_host(h)
    assert not is_staging_host("notgithub.io") and not is_staging_host("visitcmod.org")


def test_shape_checks():
    for f, v in (("email", "nope"), ("website", "visitcmod.org"), ("phone", "123")):
        assert run(fp(f, v), record=dict(CMOD_RECORD, **{f: ""})).applied is None


def test_partial_apply_and_unchanged_value_skipped():
    r = run(fp("linkedin", "https://linkedin.com/company/x"), fp("email", "info@visitcmod.org", conf=0.5),
            fp("name", CMOD_RECORD["name"]), fp("phone", "760-233-7755"))
    assert r.applied_fields == ["linkedin"]
    assert [f for f, _ in r.rejected] == ["email"]
    assert review_fields(r) == ["phone"]


def test_record_validator_gate():
    bad = dict(CMOD_RECORD, latitude=1.0, longitude=2.0)
    r = run(fp("linkedin", "https://linkedin.com/company/x"), record=bad)
    assert r.applied is None and "validation" in r.rejected[0][1]


def test_cmod_end_to_end_with_fake(cache):
    snap = snapshot_with_pages(cache)
    fake = FakeProposer(default=Proposal([
        fp("website", "https://visitcmod.org/", 0.95),
        fp("name", "Children's Museum of Discovery", 0.9),
        fp("facebook", "https://facebook.com/childrensmuseumofdiscovery", 0.9),
        fp("description", "A hands-on museum.", 0.9),
        fp("phone", "760-233-7755", 0.9),
        fp("twitter", "", 0.99),
        fp("logo_src", "https://visitcmod.org/l.png", 0.99),
    ]))
    prop, _ = propose_for_partner(CMOD_RECORD, flags(), snap, cache, fake)
    r = apply_policy(CMOD_RECORD, prop, flags=flags(), snapshot=snap)
    # facebook is live and on the right network -> needs_review (043-011)
    assert r.applied_fields == ["website", "name", "description"]
    assert {f for f, _ in r.rejected} == {"twitter"}
    assert review_fields(r) == ["facebook", "phone", "logo_src"]


# ------------------------------------------------- 043-011 social replacement

def _social(net, cur, new, *, dead=None, site=None):
    """Run policy for one social field; ``dead`` is the link checker's verdict
    (True dead / False alive / None no checker)."""
    rec = dict(CMOD_RECORD, **{net: cur})
    checker = None if dead is None else (lambda url: not dead)
    snap = cmod_snapshot()
    fl = compare_partner(rec, snap, checker)
    return apply_policy(rec, Proposal([fp(net, new)]), flags=fl, snapshot=snap)


@pytest.mark.parametrize("net,cur,new", [
    ("linkedin", "https://twitter.com/aguahedionda", "https://linkedin.com/company/agua"),
    ("facebook", "https://instagram.com/aquillius", "https://facebook.com/aquillius"),
])
def test_wrong_network_current_value_still_applies(net, cur, new):
    r = _social(net, cur, new, dead=False)
    assert r.applied[net] == new and r.needs_review == []


@pytest.mark.parametrize("net,cur,new", [
    ("facebook", "https://facebook.com/ChallengeIslandSDCoastal", "https://facebook.com/ChallengeIslandHQ"),
    ("facebook", "https://facebook.com/brainbalancesandiego", "https://facebook.com/brainbalancecenters"),
    ("facebook", "https://facebook.com/aopscampus", "https://facebook.com/aops"),
    ("linkedin", "https://linkedin.com/company/citizen-schools", "https://linkedin.com/company/12345"),
    ("facebook", "https://facebook.com/encorps", "https://facebook.com/encorpsnational"),
])
def test_live_correct_network_link_is_needs_review(net, cur, new):
    r = _social(net, cur, new, dead=False)
    assert r.applied is None and review_fields(r) == [net]
    assert "not reported dead" in r.needs_review[0]["reason"]


@pytest.mark.parametrize("status", [404, 410, "exception"])
def test_dead_current_link_allows_same_network_replacement(status):
    cur, new = "https://facebook.com/old", "https://facebook.com/new"
    rec = dict(CMOD_RECORD, facebook=cur)
    snap = cmod_snapshot()

    def checker(url):  # mirrors fetcher_link_checker's dead rules
        if status == "exception":
            return False
        return status not in (404, 410)

    fl = compare_partner(rec, snap, checker)
    r = apply_policy(rec, Proposal([fp("facebook", new)]), flags=fl, snapshot=snap)
    assert r.applied["facebook"] == new


def test_empty_social_field_fill_still_applies():
    r = _social("linkedin", "", "https://linkedin.com/company/x", dead=False)
    assert r.applied["linkedin"] == "https://linkedin.com/company/x"


def test_no_link_checker_means_needs_review():
    r = _social("facebook", "https://facebook.com/old", "https://facebook.com/new", dead=None)
    assert r.applied is None and review_fields(r) == ["facebook"]
    r = apply_policy(dict(CMOD_RECORD, facebook="https://facebook.com/old"),
                     Proposal([fp("facebook", "https://facebook.com/new")]), flags=[])
    assert review_fields(r) == ["facebook"]


def test_dead_flag_accepted_as_dict():
    fl = [{"kind": "social_dead", "severity": "medium", "field": "facebook", "dead": True}]
    r = apply_policy(dict(CMOD_RECORD, facebook="https://facebook.com/old"),
                     Proposal([fp("facebook", "https://facebook.com/new")]), flags=fl)
    assert r.applied["facebook"] == "https://facebook.com/new"
