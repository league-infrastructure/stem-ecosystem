"""No-LLM change check (sprint 043-004). No network: liveness is faked."""

from partner_scrape.profiles.snapshot import page_entry, write_snapshot_if_changed
from partner_scrape.storage import LocalStore
from partner_scrape.updates.checks import (
    Severity,
    fetcher_link_checker,
    compare_partner,
    load_state,
    names_match,
    needs_llm,
    run_checks,
    save_state,
    snapshot_hash,
)

CMOD_RECORD = {
    "slug": "cmod",
    "name": "San Diego Children's Discovery Museum",
    "website": "http://sdcdm.org",
    "email": "Marketing@sdcdm.org",
    "phone": "(619) 233-5757",
    "twitter": "https://twitter.com/sdcdm320",
    "facebook": "https://www.facebook.com/sdcdm",
    "instagram": "http://instagram.com/sdcdm320",
}


def cmod_snapshot():
    home = page_entry(
        "http://sdcdm.org", status=200, body="x",
        final_url="https://visitcmod.org/",
        redirect_chain=[[301, "https://sdcdm.org/"], [301, "https://visitcmod.org/"]],
    )
    return {
        "version": 1, "slug": "cmod", "website": "http://sdcdm.org", "status": "ok",
        "pages": {"home": home},
        "facts": {"home": {
            "title": "Children's Museum of Discovery | Home",
            "og_site_name": "", "jsonld": [],
            "socials": {
                "facebook": "https://facebook.com/childrensmuseumofdiscovery",
                "instagram": "https://instagram.com/childrensmuseumofdiscovery",
            },
            "emails": [], "phones": ["760-233-7755"],
        }},
        "redirects": [{"kind": "home", "requested": "http://sdcdm.org",
                       "final": "https://visitcmod.org/"}],
    }


def dead_twitter(url):
    return "twitter.com" not in url


def by_kind(flags):
    return {(f.kind, f.field): f.severity for f in flags}


def test_cmod_flags_and_severities():
    flags = compare_partner(CMOD_RECORD, cmod_snapshot(), dead_twitter)
    got = by_kind(flags)
    assert got[("website_moved", "website")] == Severity.HIGH
    assert got[("name_mismatch", "name")] == Severity.MEDIUM
    assert got[("phone_mismatch", "phone")] == Severity.MEDIUM
    assert got[("email_domain_mismatch", "email")] == Severity.MEDIUM
    assert got[("social_dead", "twitter")] == Severity.MEDIUM
    assert got[("social_changed", "facebook")] == Severity.MEDIUM
    assert got[("social_changed", "instagram")] == Severity.MEDIUM
    assert flags[0].severity == Severity.HIGH  # most severe first
    assert needs_llm(flags)


def test_medium_alone_is_sent_to_llm_low_is_not():
    snap = cmod_snapshot()
    snap["redirects"] = []
    snap["pages"]["home"]["final_url"] = "http://sdcdm.org"
    rec = dict(CMOD_RECORD, name="Children's Museum of Discovery",
               email="a@sdcdm.org", phone="760 233 7755",
               twitter="", facebook="https://facebook.com/childrensmuseumofdiscovery",
               instagram="https://www.instagram.com/childrensmuseumofdiscovery/")
    assert compare_partner(rec, snap) == []
    medium = compare_partner(dict(rec, phone="619-000-1111"), snap)
    assert [f.severity for f in medium] == [Severity.MEDIUM] and needs_llm(medium)
    low = compare_partner(dict(rec, twitter="", facebook=""), snap)
    assert {f.kind for f in low} == {"social_new"} and not needs_llm(low)


def test_unchanged_partner_has_no_flags():
    snap = cmod_snapshot()
    snap["redirects"] = []
    home = snap["pages"]["home"]
    home["final_url"] = home["url"]
    rec = {
        "slug": "cmod", "name": "Children's Museum of Discovery",
        "website": "http://sdcdm.org", "email": "info@sdcdm.org",
        "phone": "7602337755",
        "facebook": "https://www.facebook.com/childrensmuseumofdiscovery/",
        "instagram": "https://instagram.com/childrensmuseumofdiscovery",
    }
    assert compare_partner(rec, snap, lambda u: True) == []


def test_live_but_differing_social_is_changed_not_dead():
    snap = cmod_snapshot()
    flags = compare_partner(CMOD_RECORD, snap, lambda u: True)
    assert ("social_dead", "twitter") not in by_kind(flags)
    assert ("social_changed", "facebook") in by_kind(flags)


def test_dead_record_social_marked_in_changed_message():
    flags = compare_partner(CMOD_RECORD, cmod_snapshot(), lambda u: False)
    fb = next(f for f in flags if f.field == "facebook")
    assert "dead" in fb.message


def test_name_normalization():
    assert names_match("The Fleet Science Center, Inc.", "Fleet Science Center")
    assert names_match("Reuben H. Fleet", "REUBEN H FLEET")
    assert names_match("Children’s Museum", "Childrens Museum")
    assert not names_match("San Diego Children's Discovery Museum",
                           "Children's Museum of Discovery")
    assert not names_match("", "x")


def test_name_matches_any_site_name_source():
    snap = cmod_snapshot()
    snap["facts"]["home"]["jsonld"] = [{"name": "San Diego Children's Discovery Museum"}]
    flags = compare_partner(CMOD_RECORD, snap, None)
    assert ("name_mismatch", "name") not in by_kind(flags)


def test_address_check():
    snap = cmod_snapshot()
    snap["facts"]["home"]["jsonld"] = [{"name": "x", "address": {
        "streetAddress": "200 W Island Ave", "postalCode": "92101"}}]
    ok = compare_partner(dict(CMOD_RECORD, location="200 W Island Ave, Escondido, CA"),
                         snap, None)
    assert ("address_mismatch", "location") not in by_kind(ok)
    bad = compare_partner(dict(CMOD_RECORD, location="1 Main St, Vista, CA 92081"),
                          snap, None)
    assert by_kind(bad)[("address_mismatch", "location")] == Severity.MEDIUM


def test_logo_low_report_only():
    snap = cmod_snapshot()
    snap["facts"]["home"]["jsonld"] = [{"name": "x", "logo": "https://v/new.png"}]
    flags = compare_partner(dict(CMOD_RECORD, logo_src="https://sdcdm.org/old.png"), snap)
    assert by_kind(flags)[("logo_changed", "logo_src")] == Severity.LOW


def test_failed_snapshot_is_low_only():
    snap = {"status": "failed", "pages": {"home": page_entry(
        "http://sdcdm.org", status=None, body=None, error="boom")}, "facts": {}}
    flags = compare_partner(CMOD_RECORD, snap)
    assert [f.kind for f in flags] == ["site_unreachable"]
    assert not needs_llm(flags)


def test_run_checks_selection_and_state(tmp_path):
    hist, cache = LocalStore(tmp_path / "h"), LocalStore(tmp_path / "c")
    quiet = cmod_snapshot()
    quiet.update(slug="quiet", redirects=[])
    quiet["pages"]["home"]["final_url"] = quiet["pages"]["home"]["url"]
    write_snapshot_if_changed(hist, "cmod", cmod_snapshot())
    write_snapshot_if_changed(hist, "quiet", quiet)
    roster = [CMOD_RECORD, {"slug": "quiet", "name": "Children's Museum of Discovery",
                            "website": "http://sdcdm.org"}, {"slug": "nosnap"}]

    first = run_checks(roster, hist, cache, link_checker=dead_twitter)
    assert first.examined == 2 and first.no_snapshot == ["nosnap"]
    assert [c.slug for c in first.flagged_for_llm] == ["cmod"]
    save_state(cache, first.new_state)
    assert load_state(cache)["cmod"] == snapshot_hash(cmod_snapshot())

    # quiet unchanged -> skipped; cmod has a notable redirect -> still examined
    second = run_checks(roster, hist, cache, link_checker=dead_twitter)
    assert second.examined == 1 and second.skipped_unchanged == 1
    assert second.checks[0].slug == "cmod"

    allr = run_checks(roster, hist, cache, all_partners=True)
    assert allr.examined == 2
    assert any(line.startswith("FLAG cmod high website_moved") for line in allr.lines())


def test_run_checks_changed_hash_reexamines(tmp_path):
    hist, cache = LocalStore(tmp_path / "h"), LocalStore(tmp_path / "c")
    snap = cmod_snapshot()
    snap["redirects"] = []
    write_snapshot_if_changed(hist, "cmod", snap)
    save_state(cache, run_checks([CMOD_RECORD], hist, cache).new_state)
    assert run_checks([CMOD_RECORD], hist, cache).examined == 0
    snap["pages"]["home"]["sha256"] = "changed"
    write_snapshot_if_changed(hist, "cmod", snap)
    assert run_checks([CMOD_RECORD], hist, cache).examined == 1


# ------------------------------------------- fetcher_link_checker (043-011 fix)

class _Resp:
    def __init__(self, status):
        self.status = status


class _Fetcher:
    def __init__(self, status=None, exc=None):
        self.status, self.exc, self.calls = status, exc, []

    def get(self, url, **kw):
        self.calls.append(url)
        if self.exc:
            raise self.exc
        return _Resp(self.status)


def test_checker_exception_is_unknown():
    assert fetcher_link_checker(_Fetcher(exc=RuntimeError("boom")))("https://x.org/a") is None


def test_checker_robots_disallowed_is_unknown():
    from partner_scrape.fetch.robots import RobotsDisallowed

    f = _Fetcher(exc=RobotsDisallowed("no"))
    assert fetcher_link_checker(f)("https://example.org/a") is None


def test_checker_timeout_and_transport_error_unknown():
    assert fetcher_link_checker(_Fetcher(exc=TimeoutError()))("https://example.org") is None
    assert fetcher_link_checker(_Fetcher(status=0))("https://example.org") is None
    assert fetcher_link_checker(_Fetcher(status=403))("https://example.org") is None


def test_checker_404_410_dead_on_non_social_host():
    for st in (404, 410):
        assert fetcher_link_checker(_Fetcher(status=st))("https://example.org/p") is False
    assert fetcher_link_checker(_Fetcher(status=200))("https://example.org/p") is True


def test_checker_social_hosts_unknown_and_not_fetched():
    f = _Fetcher(status=404)
    chk = fetcher_link_checker(f)
    for u in ("https://www.facebook.com/x", "https://instagram.com/x",
              "https://twitter.com/x", "https://x.com/x", "https://www.linkedin.com/company/x"):
        assert chk(u) is None
    assert f.calls == []


def test_unknown_result_never_flags_dead():
    rec = dict(CMOD_RECORD, facebook="https://www.facebook.com/old")
    flags = compare_partner(rec, cmod_snapshot(), lambda u: None)
    assert not any(f.dead or f.kind == "social_dead" or "is dead" in f.message for f in flags)
