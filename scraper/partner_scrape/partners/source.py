"""Where the scraper reads the curated partner roster from.

Every scraper reader of the roster (``pipeline``, ``normalize``,
``export.partner_log``, ``export.publish``, ``directory.pipeline``) goes
through :func:`resolve_partners`, so none of them knows where the roster
lives. The source of truth is the per-partner records in the data store
(``partners/<slug>/partner.json``, see ``records.py``).

``source`` may be:

- ``None`` -- the configured data store (``PARTNER_SCRAPE_DATA_DIR``: a
  local directory for offline/dev runs, or ``s3://``).
- a ``Store`` -- that store.
- a ``list`` of partner dicts -- used as-is (tests).
- a path to a JSON file holding a list or the consolidated
  ``{"partners": [...]}`` envelope -- an explicit offline override.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from partner_scrape.storage import Store

PartnerSource = "list[dict] | str | Path | Store | None"


def _from_file(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Cannot read partners file at {path}: {exc}") from exc
    if isinstance(data, dict):
        data = data.get("partners")
    if not isinstance(data, list):
        raise RuntimeError(f"{path} is not a partner list or a partners.json envelope")
    return data


def _from_store(store: Store) -> list[dict[str, Any]]:
    # Imported here: records -> registry.validate_roster -> normalize.partners,
    # which itself calls resolve_partners.
    from partner_scrape.partners.records import load_roster

    partners = load_roster(store, validate=False).as_list()
    if not partners:
        raise RuntimeError(
            "No partner records found in the data store "
            "(partners/<slug>/partner.json). Point PARTNER_SCRAPE_DATA_DIR at a "
            "location holding the roster; see scraper/README.md "
            "('Running locally')."
        )
    return partners


def resolve_partners(source: Any = None) -> list[dict[str, Any]]:
    """Return the roster as a list of partner dicts (see module docstring)."""
    if source is None:
        from partner_scrape import config

        return _from_store(config.get_data_store())
    if isinstance(source, list):
        return source
    if isinstance(source, (str, Path)):
        return _from_file(Path(source))
    return _from_store(source)
