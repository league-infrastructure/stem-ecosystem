"""resolve_partners: where the scraper reads the roster (sprint 042 ticket 004)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from partner_scrape.normalize.partners import find_partner, load_partners
from partner_scrape.partners.source import resolve_partners
from partner_scrape.storage import LocalStore
from tests.roster_seed import seed_roster

PKG = Path(__file__).resolve().parents[1] / "partner_scrape"


def test_none_reads_records_from_the_configured_data_store(tmp_path):
    seed_roster([{"id": 2, "name": "B Org"}, {"id": 1, "name": "A Org"}])
    assert [p["name"] for p in resolve_partners()] == ["A Org", "B Org"]


def test_store_argument_is_read_directly(tmp_path):
    seed_roster([{"id": 1, "name": "A Org"}], tmp_path / "elsewhere")
    got = resolve_partners(LocalStore(tmp_path / "elsewhere"))
    assert got[0]["slug"] == "a_org"


def test_list_is_used_as_is():
    partners = [{"id": 1, "name": "A"}]
    assert resolve_partners(partners) is partners


@pytest.mark.parametrize("wrap", [False, True])
def test_file_accepts_list_or_consolidated_envelope(tmp_path, wrap):
    partners = [{"id": 1, "name": "A"}]
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"partners": partners} if wrap else partners))
    assert resolve_partners(path) == partners
    assert resolve_partners(str(path)) == partners


def test_empty_data_store_fails_loudly():
    with pytest.raises(RuntimeError, match="No partner records found"):
        resolve_partners()


def test_missing_file_fails_loudly(tmp_path):
    with pytest.raises(RuntimeError, match="Cannot read partners file"):
        resolve_partners(tmp_path / "nope.json")


def test_load_partners_joins_by_normalized_name_from_the_store():
    seed_roster([{"id": 7, "name": "The Living Coast Discovery Center"}])
    by_norm = load_partners()
    assert find_partner("Living Coast Discovery Center", by_norm)["id"] == 7


def test_site_dir_roster_file_is_ignored(tmp_path, monkeypatch):
    """A src/data/partners.json under SITE_DIR is no longer read."""
    site = tmp_path / "site"
    (site / "src" / "data").mkdir(parents=True)
    (site / "src" / "data" / "partners.json").write_text(json.dumps([{"id": 1, "name": "X"}]))
    monkeypatch.setenv("SITE_DIR", str(site))
    with pytest.raises(RuntimeError, match="No partner records found"):
        resolve_partners()


def test_no_code_path_builds_the_site_roster_path():
    """Grep guard: nothing in the package derives src/data/partners.json."""
    offenders = []
    for path in PKG.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r'"src"\s*/\s*"data"\s*/\s*"partners\.json"', text):
            offenders.append(str(path.relative_to(PKG)))
    assert offenders == []
