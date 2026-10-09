"""Redirect detection on every fetch (sprint 043 ticket 001)."""

from __future__ import annotations

import http.server
import threading
import urllib.error
from dataclasses import dataclass, field

import pytest

from partner_scrape.fetch import PoliteFetcher
from partner_scrape.fetch.cache import (
    entry_to_response,
    read_cache_entry,
    write_cache_entry,
)
from partner_scrape.fetch.fetcher import (
    FetchResponse,
    UrllibFetcher,
    _redirect_state,
    is_notable_redirect,
)
from partner_scrape.fetch.headless import PlaywrightFetcher
from partner_scrape.fetch.redirects import RedirectLog
from partner_scrape.storage import LocalStore


@pytest.mark.parametrize(
    "requested,final,expected",
    [
        ("http://sdcdm.org", "https://visitcmod.org/", True),
        ("http://example.org/a", "https://example.org/a", False),
        ("https://example.org/", "https://www.example.org/", False),
        ("https://www.example.org/", "https://example.org/x", False),
        ("https://example.org/", "https://example.org/", False),
        ("https://example.org/", "https://other.example.com/", True),
    ],
)
def test_is_notable_redirect(requested, final, expected):
    assert is_notable_redirect(requested, final) is expected


def test_fetch_response_defaults_final_url_to_url():
    r = FetchResponse(url="https://a.org/", status=200, headers={}, body="")
    assert r.final_url == "https://a.org/"
    assert r.redirect_chain == []


class _Resp:
    status = 200
    headers = {"Content-Type": "text/html"}

    def __init__(self, final):
        self._final = final

    def read(self):
        return b"<html></html>"

    def geturl(self):
        return self._final

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_urllib_fetcher_records_redirect_chain(monkeypatch):
    def fake_urlopen(request, timeout=None, context=None):
        # What the recording handler does for a 301 hop.
        _redirect_state.chain.append([301, "https://visitcmod.org/"])
        return _Resp("https://visitcmod.org/")

    monkeypatch.setattr("partner_scrape.fetch.fetcher._urlopen", fake_urlopen)
    r = UrllibFetcher().get("http://sdcdm.org")
    assert r.url == "http://sdcdm.org"
    assert r.final_url == "https://visitcmod.org/"
    assert r.redirect_chain == [[301, "https://visitcmod.org/"]]
    assert _redirect_state.chain is None


def test_urllib_fetcher_no_redirect(monkeypatch):
    monkeypatch.setattr(
        "partner_scrape.fetch.fetcher._urlopen",
        lambda request, timeout=None, context=None: _Resp("http://x.org/"),
    )
    r = UrllibFetcher().get("http://x.org/")
    assert r.final_url == "http://x.org/"
    assert r.redirect_chain == []


def test_real_redirect_handler_records_hops_over_loopback():
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/old":
                self.send_response(301)
                self.send_header("Location", "/new")
                self.end_headers()
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html>ok</html>")

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), H)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        r = UrllibFetcher().get(base + "/old")
    finally:
        server.shutdown()
        server.server_close()
    assert r.status == 200
    assert r.final_url == base + "/new"
    assert r.redirect_chain == [[301, base + "/new"]]


# --- headless ---


@dataclass
class _Req:
    url: str
    redirected_from: "_Req | None" = None


@dataclass
class _Nav:
    status: int
    url: str
    request: _Req
    headers: dict = field(default_factory=dict)


class _Page:
    def __init__(self, nav):
        self.nav = nav

    def goto(self, url, timeout=None, wait_until=None):
        return self.nav

    def content(self):
        return "<html></html>"


def test_headless_fills_final_url_and_chain():
    first = _Req("http://sdcdm.org/")
    nav = _Nav(200, "https://visitcmod.org/", _Req("https://visitcmod.org/", first))
    r = PlaywrightFetcher(page_factory=lambda: _Page(nav)).get("http://sdcdm.org/")
    assert r.final_url == "https://visitcmod.org/"
    assert r.redirect_chain == [[None, "https://visitcmod.org/"]]


def test_headless_without_url_attribute_defaults():
    class Bare:
        status = 200

    r = PlaywrightFetcher(page_factory=lambda: _Page(Bare())).get("http://a.org/")
    assert r.final_url == "http://a.org/"
    assert r.redirect_chain == []


# --- cache ---


def test_cache_round_trip_and_legacy_entry(tmp_path):
    store = LocalStore(tmp_path)
    resp = FetchResponse(
        url="http://sdcdm.org",
        status=200,
        headers={},
        body="b",
        final_url="https://visitcmod.org/",
        redirect_chain=[[301, "https://visitcmod.org/"]],
    )
    write_cache_entry(store, resp.url, resp)
    back = entry_to_response(read_cache_entry(store, resp.url))
    assert back.final_url == "https://visitcmod.org/"
    assert back.redirect_chain == [[301, "https://visitcmod.org/"]]

    legacy = read_cache_entry(store, resp.url)
    del legacy["final_url"], legacy["redirect_chain"]
    old = entry_to_response(legacy)
    assert old.final_url == "http://sdcdm.org"
    assert old.redirect_chain == []


# --- RedirectLog + PoliteFetcher ---


class _FakeFetcher:
    def __init__(self, responses):
        self.responses = responses

    def get(self, url, headers=None):
        return self.responses[url]


def test_polite_fetcher_reports_only_notable_redirects(tmp_path):
    log = RedirectLog()
    moved = FetchResponse(
        "http://sdcdm.org", 200, {}, "x", final_url="https://visitcmod.org/",
        redirect_chain=[[301, "https://visitcmod.org/"]],
    )
    upgraded = FetchResponse(
        "http://a.org/", 200, {}, "x", final_url="https://a.org/",
        redirect_chain=[[301, "https://a.org/"]],
    )
    fetcher = PoliteFetcher(
        cache_dir=tmp_path,
        fetcher=_FakeFetcher({"http://sdcdm.org": moved, "http://a.org/": upgraded}),
        redirect_log=log,
    )
    fetcher.get("http://sdcdm.org", respect_robots=False, rate_limit_seconds=0, label="cmod")
    fetcher.get("http://a.org/", respect_robots=False, rate_limit_seconds=0)
    assert [(r.source, r.requested, r.final, r.status) for r in log.items] == [
        ("cmod", "http://sdcdm.org", "https://visitcmod.org/", 301)
    ]
    assert log.lines() == ["REDIRECT cmod: http://sdcdm.org -> https://visitcmod.org/ (301)"]


def test_polite_fetcher_without_log_still_works(tmp_path):
    ok = FetchResponse("http://a.org/", 200, {}, "x")
    f = PoliteFetcher(cache_dir=tmp_path, fetcher=_FakeFetcher({"http://a.org/": ok}))
    assert f.get("http://a.org/", respect_robots=False, rate_limit_seconds=0).status == 200
