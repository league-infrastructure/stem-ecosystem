"""Resolve (type, slug) to an entity from the published data store.

Data sources (all in the data store, i.e. ``data/`` in the bucket):

* partner      -> ``partners/<slug>/partner.json``
* opportunity  -> ``opportunities.json`` (list, matched on ``slug``)
* team         -> ``teams.json``  ``{teams: [...]}`` matched on ``team_id``
* club         -> ``clubs.json``  ``{clubs: [...]}`` matched on ``club_id``
* place        -> ``places.json`` ``{places: [...]}`` matched on ``place_id``

Only partners and opportunities (via ``partner_id`` -> ``partners.json``) and
places (``related_partner_id``) can name a ``partner_slug``; teams and clubs
have none. An unknown entity is `None` (the API answers ``not_found``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from partner_scrape.hints.validate import domains_of
from partner_scrape.partners.records import read_record
from partner_scrape.storage import Store

ENTITY_TYPES = ("partner", "opportunity", "team", "club", "place")

# type -> (file, list key or None for a bare list, id field, name field)
_FILES = {
    "opportunity": ("opportunities.json", None, "slug", "title"),
    "team": ("teams.json", "teams", "team_id", "name"),
    "club": ("clubs.json", "clubs", "club_id", "name"),
    "place": ("places.json", "places", "place_id", "name"),
}


@dataclass(frozen=True)
class Entity:
    type: str
    slug: str
    name: str
    partner_slug: str | None
    website: str | None
    domains: list[str] = field(default_factory=list)
    record: dict[str, Any] = field(default_factory=dict, compare=False)

    def public(self) -> dict[str, Any]:
        return {
            "type": self.type, "slug": self.slug, "name": self.name,
            "partner_slug": self.partner_slug,
        }


class EntityResolver:
    def __init__(self, data_store: Store):
        self.data = data_store

    def resolve(self, type_: str, slug: str) -> Entity | None:
        if type_ not in ENTITY_TYPES or not isinstance(slug, str) or not slug:
            return None
        try:
            if type_ == "partner":
                return self._partner(slug)
            return self._listed(type_, slug)
        except ValueError:  # unsafe slug or unreadable JSON: treat as absent
            return None

    # -- partner -----------------------------------------------------------
    def _partner(self, slug: str) -> Entity | None:
        rec = read_record(self.data, slug)
        if not isinstance(rec, dict):
            return None
        site = rec.get("website") or None
        return Entity(
            "partner", slug, str(rec.get("name") or slug), slug, site,
            domains_of(site), rec,
        )

    def _partner_slug_for_id(self, partner_id: Any) -> str | None:
        if partner_id in (None, ""):
            return None
        doc = self.data.read_json("partners.json")
        for p in (doc or {}).get("partners", []) if isinstance(doc, dict) else []:
            if p.get("id") == partner_id:
                return p.get("slug") or None
        return None

    # -- listed entities ---------------------------------------------------
    def _listed(self, type_: str, slug: str) -> Entity | None:
        fname, list_key, id_field, name_field = _FILES[type_]
        doc = self.data.read_json(fname)
        rows = doc.get(list_key) if (list_key and isinstance(doc, dict)) else doc
        rec = next(
            (r for r in rows or [] if isinstance(r, dict) and r.get(id_field) == slug),
            None,
        )
        if rec is None:
            return None
        if type_ == "opportunity":
            partner_slug = self._partner_slug_for_id(rec.get("partner_id"))
            link = rec.get("link") or ""
            site = link if link.startswith(("http://", "https://")) else None
            partner_site = None
            if partner_slug:
                prec = read_record(self.data, partner_slug) or {}
                partner_site = prec.get("website") or None
            domains = domains_of(site, partner_site)
        else:
            partner_slug = (
                self._partner_slug_for_id(rec.get("related_partner_id"))
                if type_ == "place" else None
            )
            site = rec.get("website") or None
            domains = domains_of(site, rec.get("organization_website"))
        return Entity(
            type_, slug, str(rec.get(name_field) or slug), partner_slug, site,
            domains, rec,
        )
