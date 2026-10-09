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

def run(*fields, **kw):
    return apply_policy(CMOD_RECORD, Proposal(list(fields)), **kw)


def test_applies_allowlisted_high_confidence_and_is_pure():
    before = json.dumps(CMOD_RECORD, sort_keys=True)
    r = run(fp("website", "https://visitcmod.org"), fp("phone", "760-233-7755"),
            fp("facebook", "https://facebook.com/childrensmuseumofdiscovery"),
            fp("description", "A hands-on museum."))
    assert r.applied_fields == ["website", "phone", "facebook", "description"]
    assert r.applied["website"] == "https://visitcmod.org" and r.applied["slug"] == "cmod"
    assert r.rejected == []
    assert json.dumps(CMOD_RECORD, sort_keys=True) == before


def test_confidence_threshold_configurable():
    p = fp("phone", "760-233-7755", conf=0.79)
    assert run(p).applied is None and "confidence" in run(p).rejected[0][1]
    assert run(p, min_confidence=0.7).applied_fields == ["phone"]
    assert run(fp("phone", "760-233-7755", conf=0.8)).applied_fields == ["phone"]


@pytest.mark.parametrize("name", ["slug", "id", "latitude", "longitude", "organization_type", "logo_src", "bogus"])
def test_protected_fields_never_change(name):
    r = run(fp(name, "https://x.org/logo.png" if name == "logo_src" else "5", conf=1.0))
    assert r.applied is None and r.rejected[0][0] == name


@pytest.mark.parametrize("name", ["name", "phone", "email", "location", "website", "twitter", "description"])
def test_never_blank(name):
    r = run(fp(name, "  "))
    assert r.applied is None and r.applied_fields == []
    assert r.rejected[0][0] == name


def test_social_never_removed_but_dead_link_replaced():
    r = run(fp("twitter", ""))
    assert r.applied is None and "report-only" in r.rejected[0][1]
    r = run(fp("twitter", "https://x.com/cmod"))
    assert r.applied["twitter"] == "https://x.com/cmod"
    # wrong network host is rejected
    r = run(fp("twitter", "https://facebook.com/cmod"))
    assert r.applied is None and "not a twitter domain" in r.rejected[0][1]


def test_shape_checks():
    for f, v in (("email", "nope"), ("website", "visitcmod.org"), ("phone", "123")):
        assert run(fp(f, v)).applied is None


def test_partial_apply_and_unchanged_value_skipped():
    r = run(fp("phone", "760-233-7755"), fp("email", "info@visitcmod.org", conf=0.5),
            fp("name", CMOD_RECORD["name"]))
    assert r.applied_fields == ["phone"]
    assert [f for f, _ in r.rejected] == ["email"]


def test_record_validator_gate():
    bad = dict(CMOD_RECORD, latitude=1.0, longitude=2.0)
    r = apply_policy(bad, Proposal([fp("phone", "760-233-7755")]))
    assert r.applied is None and "validation" in r.rejected[0][1]


def test_cmod_end_to_end_with_fake(cache):
    snap = snapshot_with_pages(cache)
    fake = FakeProposer(default=Proposal([
        fp("website", "https://visitcmod.org/", 0.95),
        fp("name", "Children's Museum of Discovery", 0.9),
        fp("twitter", "", 0.99),
        fp("logo_src", "https://visitcmod.org/l.png", 0.99),
    ]))
    prop, _ = propose_for_partner(CMOD_RECORD, flags(), snap, cache, fake)
    r = apply_policy(CMOD_RECORD, prop)
    assert r.applied_fields == ["website", "name"]
    assert {f for f, _ in r.rejected} == {"twitter", "logo_src"}
