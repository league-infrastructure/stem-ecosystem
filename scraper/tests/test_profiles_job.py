"""profiles job and private snapshots (sprint 043 ticket 003)."""

from __future__ import annotations

import json

import pytest

from partner_scrape import cli
from partner_scrape.fetch import PoliteFetcher
from partner_scrape.fetch.fetcher import FetchResponse
from partner_scrape.fetch.redirects import RedirectLog
from partner_scrape.fetch.throttle import Throttle
from partner_scrape.profiles.job import run_profiles
from partner_scrape.profiles.snapshot import read_snapshot, snapshot_key
from partner_scrape.storage import LocalStore

HOME = (
    '<html><head><title>Alpha</title></head><body>'
    '<a href="/about">About</a><a href="/contact">Contact</a>'
    '<a href="mailto:hi@alpha.org">mail</a></body></html>'
)


class FakeFetcher:
    """Serves a URL -> (status, body, final_url) table; others 404."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, headers=None):
        self.calls.append(url)
        if url in self.pages:
            v = self.pages[url]
            if isinstance(v, Exception):
                raise v
            status, body, final = v
            return FetchResponse(url=url, status=status, headers={}, body=body,
                                 final_url=final or url,
                                 redirect_chain=[[301, final]] if final else [])
        return FetchResponse(url=url, status=404, headers={}, body="")

    def post(self, *a, **k):  # pragma: no cover
        raise NotImplementedError


def _polite(tmp_path, pages, log=None):
    return PoliteFetcher(
        cache_dir=tmp_path / "cache", fetcher=FakeFetcher(pages),
        throttle=Throttle(sleep=lambda s: None), redirect_log=log,
    )


ROSTER = [
    {"slug": "alpha", "name": "Alpha", "website": "https://alpha.org/"},
    {"slug": "beta", "name": "Beta", "website": "https://beta.org/"},
    {"slug": "gamma", "name": "Gamma", "website": ""},
]
PAGES = {
    "https://alpha.org/": (200, HOME, None),
    "https://alpha.org/about": (200, "<title>About Alpha</title>", None),
    "https://alpha.org/contact": (200, '<a href="tel:6195551212">x</a>', None),
    "https://beta.org/": (200, "<html><title>Beta</title></html>", "https://newbeta.org/"),
}


def test_job_snapshot_skip_redirect_and_failure_isolation(tmp_path):
    hist = LocalStore(tmp_path / "hist")
    log = RedirectLog()
    pages = dict(PAGES)
    pages["https://alpha.org/contact"] = RuntimeError("boom")
    rep = run_profiles(ROSTER, _polite(tmp_path, pages, log), hist, redirect_log=log)
    assert rep.partners == 3 and rep.skipped == ["gamma"]
    assert rep.fetched == 2 and rep.failed == 1 and rep.redirects == 1
    text = "\n".join(rep.lines())
    assert "REDIRECT beta:home: https://beta.org/ -> https://newbeta.org/" in text
    assert "SKIPPED gamma" in text and "profiles: partners=3 fetched=2 failed=1 redirects=1 skipped=1" in text

    snap = read_snapshot(hist, "alpha")
    assert snap["status"] == "partial"
    assert snap["pages"]["about"]["sha256"] and snap["pages"]["contact"]["error"]
    assert snap["facts"]["home"]["emails"] == ["hi@alpha.org"]
    beta = read_snapshot(hist, "beta")
    assert beta["pages"]["home"]["final_url"] == "https://newbeta.org/"
    assert beta["pages"]["home"]["redirect_chain"] == [[301, "https://newbeta.org/"]]
    assert beta["redirects"][0]["final"] == "https://newbeta.org/"
    assert read_snapshot(hist, "gamma") is None
    assert (tmp_path / "hist" / snapshot_key("alpha")).exists()


def test_total_failure_does_not_abort(tmp_path):
    hist = LocalStore(tmp_path / "hist")
    pages = {"https://alpha.org/": RuntimeError("down"), **{
        k: v for k, v in PAGES.items() if "beta" in k}}
    rep = run_profiles(ROSTER[:2], _polite(tmp_path, pages), hist)
    assert rep.fetched == 1 and rep.failed == 1
    assert read_snapshot(hist, "alpha")["status"] == "failed"
    assert read_snapshot(hist, "beta")["status"] == "ok"


def test_unchanged_pages_identical_hashes_and_no_rewrite(tmp_path):
    hist = LocalStore(tmp_path / "hist")
    r1 = run_profiles(ROSTER[:1], _polite(tmp_path, PAGES), hist)
    path = tmp_path / "hist" / snapshot_key("alpha")
    first = json.loads(path.read_text())
    mtime = path.stat().st_mtime_ns
    r2 = run_profiles(ROSTER[:1], _polite(tmp_path / "c2", PAGES), hist)
    assert r1.written == 1 and r2.written == 0 and r2.unchanged == 1
    assert path.stat().st_mtime_ns == mtime
    assert json.loads(path.read_text()) == first

    changed = dict(PAGES)
    changed["https://alpha.org/about"] = (200, "<title>New About</title>", None)
    r3 = run_profiles(ROSTER[:1], _polite(tmp_path / "c3", changed), hist)
    assert r3.written == 1
    new = read_snapshot(hist, "alpha")
    assert new["pages"]["home"]["sha256"] == first["pages"]["home"]["sha256"]
    assert new["pages"]["about"]["sha256"] != first["pages"]["about"]["sha256"]


def test_slug_and_limit_filters(tmp_path):
    hist = LocalStore(tmp_path / "hist")
    rep = run_profiles(ROSTER, _polite(tmp_path, PAGES), hist, slug="beta")
    assert rep.partners == 1 and read_snapshot(hist, "alpha") is None
    rep = run_profiles(ROSTER, _polite(tmp_path / "c", PAGES), hist, limit=1)
    assert rep.partners == 1 and read_snapshot(hist, "alpha") is not None


def test_refuses_public_read_store(tmp_path):
    class Public(LocalStore):
        public_read = True

    with pytest.raises(ValueError, match="private"):
        run_profiles(ROSTER, _polite(tmp_path, PAGES), Public(tmp_path / "h"))


def test_cli_profiles_uses_history_store_only(tmp_path, monkeypatch, capsys):
    data = LocalStore(tmp_path / "data")
    for r in ROSTER[:1]:
        data.write_json(f"partners/{r['slug']}/partner.json", r)
    monkeypatch.setenv("PARTNER_SCRAPE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PARTNER_SCRAPE_HISTORY_DIR", str(tmp_path / "hist"))
    monkeypatch.setenv("SCRAPE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(
        cli, "PoliteFetcher",
        lambda redirect_log=None: _polite(tmp_path, PAGES, redirect_log),
    )
    assert cli.main(["profiles", "--slug", "alpha"]) == 0
    assert "profiles: partners=1 fetched=1" in capsys.readouterr().out
    assert (tmp_path / "hist" / "profiles" / "alpha" / "profile.json").exists()
    assert not list((tmp_path / "data").rglob("profile.json"))
