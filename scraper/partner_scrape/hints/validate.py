"""Server-side validation: the authority on what a hint may contain.

Model output is never trusted; every hint list passes through
`validate_hints`, which returns normalized hints or raises `HintError`.
Redirect fetching is injected (`fetcher`) so this module does no HTTP.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

from partner_scrape.hints import model as m

#: ``fetcher(url) -> final_url`` after following redirects.
Fetcher = Callable[[str], str]
#: ``resolver(host) -> list of IP strings``.
Resolver = Callable[[str], list[str]]


class HintError(ValueError):
    """A hint failed validation. The message is safe to show the user."""


def host_of(url: str) -> str:
    """Lowercased hostname of `url` (no port, no leading ``www.`` stripping)."""
    return (urlparse(url).hostname or "").lower().rstrip(".")


def _bare(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def on_domain(host: str, domains: Iterable[str]) -> bool:
    """True if `host` equals or is a subdomain of any of `domains`."""
    host = _bare(host.lower())
    for d in domains:
        d = _bare((d or "").lower().strip("."))
        if d and (host == d or host.endswith("." + d)):
            return True
    return False


def domains_of(*urls_or_hosts: str | None) -> list[str]:
    """Hostnames for website URLs (or bare hosts), blanks dropped."""
    out = []
    for u in urls_or_hosts:
        if not u:
            continue
        h = host_of(u if "//" in u else "//" + u)
        if h and h not in out:
            out.append(h)
    return out


def _default_resolver(host: str) -> list[str]:
    try:
        return sorted({i[4][0] for i in socket.getaddrinfo(host, None)})
    except OSError:
        return []


def _is_private_ip(text: str) -> bool:
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return False
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        or ip.is_multicast or ip.is_unspecified
    )


def is_private_host(host: str, resolver: Resolver | None = None) -> bool:
    """True if `host` is a private/loopback literal, a local name, or
    resolves to any private address."""
    if not host or host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        return True
    if _is_private_ip(host.strip("[]")):
        return True
    for addr in (resolver or _default_resolver)(host):
        if _is_private_ip(addr):
            return True
    return False


def _text(h: dict, field: str, limit: int, required: bool = True) -> str | None:
    v = h.get(field)
    if v is None or (isinstance(v, str) and not v.strip()):
        if required:
            raise HintError(f"{h.get('kind')} hint needs '{field}'")
        return None
    if not isinstance(v, str):
        raise HintError(f"{h.get('kind')} hint '{field}' must be text")
    v = v.strip()
    if len(v) > limit:
        raise HintError(f"{h.get('kind')} hint '{field}' is longer than {limit} characters")
    return v


def _check_extra(h: dict, allowed: set[str]) -> None:
    extra = set(h) - allowed - {"kind"}
    if extra:
        raise HintError(f"{h.get('kind')} hint has unknown field(s): {', '.join(sorted(extra))}")


def _validate_page(h: dict, domains: list[str]) -> dict:
    _check_extra(h, {"role", "url", "focus"})
    role = h.get("role")
    if role not in m.PAGE_ROLES:
        raise HintError(f"page hint role must be one of {', '.join(m.PAGE_ROLES)}")
    url = _text(h, "url", m.MAX_URL_CHARS)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HintError("page hint url must be an http(s) URL")
    if not on_domain(parsed.hostname, domains):
        raise HintError(
            f"page hint url {parsed.hostname} is not on the organization's website domain"
        )
    out = {"kind": "page", "role": role, "url": url}
    focus = _text(h, "focus", m.MAX_FOCUS_CHARS, required=False)
    if focus:
        out["focus"] = focus
    return out


def _validate_exclude(h: dict) -> dict:
    _check_extra(h, {"match", "reason"})
    match = _text(h, "match", m.MAX_REGEX_CHARS + len(m.REGEX_PREFIX))
    reason = _text(h, "reason", m.MAX_REASON_CHARS, required=False) or ""
    if match.startswith(m.REGEX_PREFIX):
        pattern = match[len(m.REGEX_PREFIX):]
        if not pattern:
            raise HintError("exclude hint regex is empty")
        if len(pattern) > m.MAX_REGEX_CHARS:
            raise HintError(f"exclude hint regex is longer than {m.MAX_REGEX_CHARS} characters")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise HintError(f"exclude hint regex does not compile: {exc}") from exc
    elif len(match) > m.MAX_MATCH_CHARS:
        raise HintError(f"exclude hint match is longer than {m.MAX_MATCH_CHARS} characters")
    return {"kind": "exclude", "match": match, "reason": reason}


def _validate_note(h: dict) -> dict:
    _check_extra(h, {"text"})
    return {"kind": "note", "text": _text(h, "text", m.MAX_TEXT_CHARS)}


def _validate_identity(
    h: dict,
    current_website: str | None,
    fetcher: Fetcher | None,
    resolver: Resolver | None,
) -> dict:
    _check_extra(h, {"name", "website"})
    name = _text(h, "name", m.MAX_NAME_CHARS, required=False)
    website = _text(h, "website", m.MAX_URL_CHARS, required=False)
    if not name and not website:
        raise HintError("identity hint needs a name or a website")
    out: dict[str, Any] = {"kind": "identity"}
    if name:
        out["name"] = name
    if website:
        parsed = urlparse(website if "//" in website else "//" + website)
        new_host = (parsed.hostname or "").lower().rstrip(".")
        if not new_host or parsed.scheme not in ("", "http", "https"):
            raise HintError("identity hint website must be an http(s) URL")
        if not current_website:
            raise HintError("cannot verify identity website: no current website on record")
        cur_host = host_of(current_website if "//" in current_website else "//" + current_website)
        if is_private_host(cur_host, resolver) or is_private_host(new_host, resolver):
            raise HintError("identity website must be a public host")
        if fetcher is None:
            raise HintError("identity website cannot be verified right now")
        cur_url = current_website if "//" in current_website else "https://" + current_website
        try:
            final = fetcher(cur_url)
        except Exception as exc:  # noqa: BLE001 - any fetch failure means unverified
            raise HintError("could not verify identity website redirect") from exc
        final_host = host_of(final or "")
        if _bare(final_host) != _bare(new_host):
            raise HintError(
                "identity website not accepted: the current website does not redirect to it"
            )
        out["website"] = f"https://{new_host}" + (parsed.path.rstrip("/") if parsed.path else "")
    return out


def validate_hint(
    h: Any,
    *,
    domains: list[str],
    current_website: str | None = None,
    fetcher: Fetcher | None = None,
    resolver: Resolver | None = None,
) -> dict:
    """Validate one hint; return its normalized form or raise `HintError`."""
    if not isinstance(h, dict):
        raise HintError("a hint must be an object")
    kind = h.get("kind")
    if kind == "page":
        return _validate_page(h, domains)
    if kind == "exclude":
        return _validate_exclude(h)
    if kind == "note":
        return _validate_note(h)
    if kind == "identity":
        return _validate_identity(h, current_website, fetcher, resolver)
    raise HintError(f"unknown hint kind {kind!r}; expected one of {', '.join(m.KINDS)}")


def validate_hints(
    hints: Any,
    *,
    domains: list[str],
    current_website: str | None = None,
    fetcher: Fetcher | None = None,
    resolver: Resolver | None = None,
) -> list[dict]:
    """Validate a whole hint list (all or nothing). Duplicates are dropped."""
    if not isinstance(hints, list):
        raise HintError("hints must be a list")
    if len(hints) > m.MAX_TOTAL_HINTS:
        raise HintError(f"too many hints (max {m.MAX_TOTAL_HINTS})")
    out: list[dict] = []
    counts: dict[str, int] = {}
    for raw in hints:
        h = validate_hint(
            raw, domains=domains, current_website=current_website,
            fetcher=fetcher, resolver=resolver,
        )
        if h in out:
            continue
        counts[h["kind"]] = counts.get(h["kind"], 0) + 1
        if counts[h["kind"]] > m.MAX_HINTS_PER_KIND[h["kind"]]:
            raise HintError(
                f"too many {h['kind']} hints (max {m.MAX_HINTS_PER_KIND[h['kind']]})"
            )
        out.append(h)
    return out
