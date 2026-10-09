"""Test helper: seed the partner roster as per-partner records in a data dir.

Since sprint 042 the scraper reads the roster from
``partners/<slug>/partner.json`` in the data store, not from
``src/data/partners.json``. Tests that used to write that file call
``seed_roster`` instead.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from partner_scrape.model import slugify


def seed_roster(partners: list[dict[str, Any]], data_dir: str | Path | None = None) -> Path:
    """Write each partner as ``<data_dir>/partners/<slug>/partner.json``.

    ``data_dir`` defaults to ``$PARTNER_SCRAPE_DATA_DIR`` (the data store
    the code under test will read). The slug is the partner's own ``slug``
    or ``slugify(name)``; it is stored in the record.
    """
    root = Path(data_dir if data_dir is not None else os.environ["PARTNER_SCRAPE_DATA_DIR"])
    for partner in partners:
        slug = partner.get("slug") or slugify(partner.get("name", ""))
        record = {**partner, "slug": slug}
        path = root / "partners" / slug / "partner.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    return root


def seed_roster_file(path: str | Path, data_dir: str | Path | None = None) -> Path:
    """``seed_roster`` from a roster JSON file (a list, or an envelope)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data["partners"]
    return seed_roster(data, data_dir)
