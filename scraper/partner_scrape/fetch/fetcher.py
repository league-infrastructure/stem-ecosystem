"""The ``Fetcher`` protocol and its real, stdlib-based implementation.

Every other piece of this package (``robots.py``, ``cache.py``) talks to
remote resources exclusively through a ``Fetcher`` -- never directly
through ``urllib``. That is the injectable seam sprint.md's Design
Rationale calls for: production code uses ``UrllibFetcher`` (stdlib
``urllib.request``, zero new dependencies, matching
``dev/fetch_tec_api.py``'s proven approach), while tests substitute a
fixture-backed fake that returns canned responses with no real socket
ever opened.
"""

from __future__ import annotations

import functools
import http.client
import json
import logging
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

import certifi

logger = logging.getLogger(__name__)

#: Polite default User-Agent, matching dev/fetch_tec_api.py's
#: already-proven value for these sites.
DEFAULT_USER_AGENT = "STEM-Calendar-Bot/1.0 (educational research)"

#: Synthetic ``FetchResponse.status`` for a request that never produced
#: an HTTP response at all -- DNS failure, TLS failure, timeout, reset
#: connection, malformed URL. Callers already branch on "not 2xx" (the
#: adapters skip the page, ``cache.py`` declines to cache it), so a
#: sentinel status routes transport failures down the same
#: already-tested path a 404 takes instead of raising.
TRANSPORT_ERROR_STATUS = 0

#: Characters left alone when percent-encoding a URL's path/query. ``%``
#: is safe so an already-encoded URL is not double-encoded.
_PATH_SAFE = "/%:@&=+$,;~()!*'"
_QUERY_SAFE = _PATH_SAFE + "?"


@functools.lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext:
    """Return a shared TLS context trusting certifi's CA bundle.

    The interpreter's default trust store is whatever the platform
    happens to provide, and a uv-managed CPython on macOS resolves it to
    an ``/etc/ssl`` bundle that rejects some partners' certificate
    chains outright (observed as ``CERTIFICATE_VERIFY_FAILED: unable to
    get local issuer certificate`` against awissd.org and
    calendar.ucsd.edu, both of which verify fine against certifi).
    Pinning certifi makes verification reproducible across machines
    without weakening it -- certificates are still fully verified.
    """
    return ssl.create_default_context(cafile=certifi.where())


def sanitize_url(url: str) -> str:
    """Percent-encode characters that would make ``url`` unrequestable.

    Partner sitemaps link documents whose paths contain raw spaces (and
    other control characters), which ``http.client`` rejects with
    ``InvalidURL`` before a socket is ever opened. Encoding the path and
    query -- while leaving ``%`` safe, so an already-encoded URL is not
    double-encoded -- makes those URLs fetchable instead of fatal.
    """
    try:
        split = urllib.parse.urlsplit(url)
    except ValueError:
        return url
    return urllib.parse.urlunsplit(
        (
            split.scheme,
            split.netloc,
            urllib.parse.quote(split.path, safe=_PATH_SAFE),
            urllib.parse.quote(split.query, safe=_QUERY_SAFE),
            split.fragment,
        )
    )


def is_notable_redirect(requested: str, final: str) -> bool:
    """True when ``final`` is on a different site than ``requested``.

    "Different site" means the host differs after ignoring a leading
    ``www.`` (and case). An http->https upgrade, a www-only change, a
    path change, or no redirect at all are routine and not notable.
    """

    def host(url: str) -> str:
        try:
            name = (urllib.parse.urlsplit(url).hostname or "").lower()
        except ValueError:
            return ""
        return name[4:] if name.startswith("www.") else name

    requested_host, final_host = host(requested), host(final)
    if not requested_host or not final_host:
        return False
    return requested_host != final_host


#: Per-thread list the redirect handler appends ``[status, url]`` hops to
#: while a fetch is in flight (``None`` when no fetch is recording).
_redirect_state = threading.local()


class _RecordingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows redirects exactly as the default handler does, additionally
    recording each hop as ``[status, target_url]`` on the active fetch."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        chain = getattr(_redirect_state, "chain", None)
        if chain is not None:
            chain.append([code, newurl])
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _urlopen(request, timeout=None, context=None):
    """``urlopen`` equivalent whose redirects are recorded (see above).

    A module-level seam (tests substitute it) so no socket is opened.
    """
    opener = urllib.request.build_opener(
        _RecordingRedirectHandler, urllib.request.HTTPSHandler(context=context)
    )
    return opener.open(request, timeout=timeout)


@dataclass
class FetchResponse:
    """One raw HTTP response, exactly as retrieved (or replayed from cache).

    ``status`` is whatever actually came back over the wire -- including
    ``304`` for a conditional-GET "not modified" reply. Turning a 304
    into a reused cached body is the cache layer's job (``cache.py``),
    not this dataclass's.
    """

    url: str
    status: int
    headers: dict[str, str]
    body: str
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    #: URL the body actually came from after following redirects; ``""``
    #: (the default) means "same as ``url``" -- resolved in ``__post_init__``.
    final_url: str = ""
    #: Each redirect hop followed, as ``[status, url]`` (target of the hop).
    redirect_chain: list[list] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.final_url:
            self.final_url = self.url


class Fetcher(Protocol):
    """Injectable seam for retrieving one URL.

    Implementations must not raise on a 304 or other non-2xx status --
    return a ``FetchResponse`` describing it instead, so callers (the
    robots check, the cache layer) can inspect ``status`` uniformly
    without a try/except around every call.
    """

    def get(self, url: str, headers: dict[str, str] | None = None) -> FetchResponse:
        """Issue a GET request to ``url`` with optional extra ``headers``."""
        ...

    def post(
        self, url: str, body: dict[str, Any], headers: dict[str, str] | None = None
    ) -> FetchResponse:
        """Issue a POST request to ``url`` with a JSON ``body`` and optional extra ``headers``.

        (Sprint 031) Added for Workday's ``POST /wday/cxs/{tenant}/
        {site}/jobs`` search endpoint -- this codebase's first non-GET
        network call. Additive: every ``Fetcher`` implementation before
        sprint 031 had only ``get()``, and structural typing means an
        existing test double that never calls ``post()`` remains a
        perfectly valid ``Fetcher`` without implementing this method.
        """
        ...


class UrllibFetcher:
    """The real ``Fetcher``: stdlib ``urllib.request``, no new dependency."""

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout: float = 30.0):
        self.user_agent = user_agent
        self.timeout = timeout

    def get(self, url: str, headers: dict[str, str] | None = None) -> FetchResponse:
        request_headers = {"User-Agent": self.user_agent, **(headers or {})}
        request = urllib.request.Request(sanitize_url(url), headers=request_headers)
        return self._execute(url, request)

    def post(
        self, url: str, body: dict[str, Any], headers: dict[str, str] | None = None
    ) -> FetchResponse:
        """(Sprint 031) POST ``body`` JSON-encoded to ``url``.

        Reuses ``get()``'s exact transport-error handling (``_execute``)
        -- an ``HTTPError`` normalizes into a ``FetchResponse`` with that
        status; a connection-level failure returns
        ``TRANSPORT_ERROR_STATUS`` rather than raising.
        """
        request_headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            **(headers or {}),
        }
        request = urllib.request.Request(
            sanitize_url(url),
            data=json.dumps(body).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        return self._execute(url, request)

    def _execute(self, url: str, request: urllib.request.Request) -> FetchResponse:
        """Shared transport-error handling for both ``get()`` and ``post()``.

        ``url`` is the caller's original (unsanitized) URL -- recorded on
        the returned ``FetchResponse`` regardless of any percent-encoding
        applied to ``request``'s own target, matching ``get()``'s
        pre-existing behavior.
        """
        chain: list[list] = []
        _redirect_state.chain = chain
        try:
            with _urlopen(
                request, timeout=self.timeout, context=_ssl_context()
            ) as response:
                body = response.read().decode("utf-8", errors="replace")
                geturl = getattr(response, "geturl", None)
                final_url = url
                if chain:
                    final_url = (geturl() if callable(geturl) else None) or chain[-1][1]
                return FetchResponse(
                    url=url,
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=body,
                    final_url=final_url,
                    redirect_chain=chain,
                )
        except urllib.error.HTTPError as exc:
            # A 304 (and other non-2xx) arrive as HTTPError from
            # urlopen -- normalize them into the same FetchResponse
            # shape a 2xx gets, so callers never need a try/except.
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            headers = dict(exc.headers.items()) if exc.headers else {}
            return FetchResponse(
                url=url,
                status=exc.code,
                headers=headers,
                body=body,
                final_url=chain[-1][1] if chain else url,
                redirect_chain=chain,
            )
        except (OSError, http.client.HTTPException, UnicodeError) as exc:
            # No HTTP response ever arrived: DNS failure, TLS failure,
            # read timeout, reset connection, malformed URL. Raising
            # here would abort the *whole source* -- the pipeline's
            # per-source guard is the only handler above us -- so one
            # unreachable page out of hundreds would discard every event
            # the source had already yielded. Report it as a non-2xx
            # response instead, which callers already know how to skip.
            #
            # OSError covers URLError and its socket/TLS/timeout
            # subclasses; HTTPException covers InvalidURL; UnicodeError
            # covers hostnames that fail IDNA encoding.
            logger.warning(
                "Fetch of %s failed at the transport layer (%s: %s); "
                "reporting status %s so the caller can skip just this URL",
                url,
                type(exc).__name__,
                exc,
                TRANSPORT_ERROR_STATUS,
            )
            return FetchResponse(
                url=url, status=TRANSPORT_ERROR_STATUS, headers={}, body=""
            )
        finally:
            _redirect_state.chain = None
