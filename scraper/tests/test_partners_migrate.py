"""Tests for partners.migrate (plan, migrate, verify) against LocalStores."""

import json
from pathlib import Path

import pytest

from partner_scrape import cli, config
from partner_scrape.partners import migrate as mig
from partner_scrape.partners.consolidate import consolidate
from partner_scrape.partners.records import list_slugs, read_record
from partner_scrape.storage import LocalStore


def roster():
    return [
        {"id": 2, "name": "Beta Org", "logo_src": "beta_org.png", "phone": "1"},
        {"id": 1, "name": "Alpha Lab", "logo_src": "", "website": "https://a.org"},
        {"id": 3, "name": "Gamma", "logo_src": "gamma.svg"},
    ]


@pytest.fixture
def env(tmp_path):
    site = tmp_path / "site"
    (site / "src/data").mkdir(parents=True)
    logos = site / "public/images/logos"
    logos.mkdir(parents=True)
    (site / "src/data/partners.json").write_text(json.dumps(roster()))
    (logos / "beta_org.png").write_bytes(b"PNG")
    (logos / "gamma.svg").write_bytes(b"<svg/>")
    (logos / "orphan.png").write_bytes(b"x")
    cache = LocalStore(tmp_path / "cache")
    cache.write_text("partner_log/beta_org/partner.json", '{"n":1}')
    cache.write_text("partner_log/beta_org/opportunities.jsonl", '{"slug":"e1","content_hash":"h1"}\n')
    return {
        "site": site,
        "data": LocalStore(tmp_path / "data"),
        "history": LocalStore(tmp_path / "history"),
        "cache": cache,
        "tmp": tmp_path,
    }


def run(env, **kw):
    return mig.migrate(env["site"], env["data"], env["history"], env["cache"], **kw)


def snapshot(store):
    return {k: store.read_bytes(k) for k in store.list("")}


def test_migrate_writes_records_logos_and_history(env):
    report = run(env)
    assert report.records_new == 3 and report.logos_new == 2
    assert list_slugs(env["data"]) == ["alpha_lab", "beta_org", "gamma"]
    beta = read_record(env["data"], "beta_org")
    assert beta["slug"] == "beta_org"
    assert beta["logo_src"] == "partners/beta_org/logo.png"
    assert read_record(env["data"], "alpha_lab")["logo_src"] == ""
    assert env["data"].read_bytes("partners/gamma/logo.svg") == b"<svg/>"
    assert report.plan.orphan_logos == ["orphan.png"]
    changes = [
        json.loads(x)
        for x in env["history"].read_text("partners/changes.jsonl").splitlines()
    ]
    assert {c["actor"] for c in changes} == {"migration"}
    assert len(changes) == 5  # 3 records + 2 logos


def test_dry_run_writes_nothing_and_reports(env):
    report = run(env, dry_run=True)
    assert env["data"].list("") == [] and env["history"].list("") == []
    assert report.records_new == 3 and report.log_copied == 2
    assert any("DRY RUN" in x for x in report.lines())


def test_rerun_is_idempotent(env):
    run(env)
    before = (snapshot(env["data"]), snapshot(env["history"]))
    report = run(env)
    assert report.records_unchanged == 3 and report.logos_unchanged == 2
    assert report.records_new == report.records_updated == 0
    assert report.log_identical == 2 and report.log_copied == 0
    assert (snapshot(env["data"]), snapshot(env["history"])) == before


def test_partner_log_is_copied_never_modified_or_deleted(env):
    before = snapshot(env["cache"])
    run(env)
    assert snapshot(env["cache"]) == before
    for key, content in before.items():
        assert env["history"].read_bytes(key) == content
    run(env)
    assert snapshot(env["cache"]) == before


def test_partner_log_rerun_picks_up_new_source_lines_without_losing_dest(env):
    run(env)
    key = "partner_log/beta_org/opportunities.jsonl"
    env["cache"].write_text(key, '{"slug":"e1","content_hash":"h1"}\n{"slug":"e2","content_hash":"h2"}\n')
    # destination got a newer line from the new image in the meantime
    env["history"].write_text(key, '{"slug":"e1","content_hash":"h1"}\n{"slug":"e3","content_hash":"h3"}\n')
    report = run(env)
    assert report.log_merged == 1
    lines = env["history"].read_text(key).splitlines()
    assert [json.loads(x)["slug"] for x in lines] == ["e1", "e3", "e2"]


def test_slug_collision_fails_before_writing(env):
    (env["site"] / "src/data/partners.json").write_text(
        json.dumps([{"id": 1, "name": "A B"}, {"id": 2, "name": "a-b"}])
    )
    with pytest.raises(mig.MigrationError, match="slug collision 'a_b'"):
        run(env)
    assert env["data"].list("") == [] and env["history"].list("") == []


def test_unusable_name_fails(env):
    (env["site"] / "src/data/partners.json").write_text(json.dumps([{"id": 1, "name": "!!!"}]))
    with pytest.raises(mig.MigrationError, match="unusable slug"):
        run(env)
    assert env["data"].list("") == []


@pytest.mark.parametrize(
    "logo_src,msg",
    [
        ("missing.png", "no file"),
        ("https://x.org/a.png", "not a bare filename"),
        ("sub/a.png", "not a bare filename"),
    ],
)
def test_bad_logo_src_is_flagged_and_blocks(env, logo_src, msg):
    (env["site"] / "src/data/partners.json").write_text(
        json.dumps([{"id": 1, "name": "A", "logo_src": logo_src}])
    )
    with pytest.raises(mig.MigrationError, match=msg):
        run(env, dry_run=True)
    assert env["data"].list("") == []


def test_verify_passes_after_migration_and_ignores_logo_src(env):
    run(env)
    diffs, notes = mig.verify_migration(env["data"], roster())
    assert diffs == []
    assert notes  # roster() is not id-ordered


def test_verify_fails_on_any_other_difference(env):
    run(env)
    rec = read_record(env["data"], "beta_org")
    rec["phone"] = "999"
    env["data"].write_json("partners/beta_org/partner.json", rec)
    diffs, _ = mig.verify_migration(env["data"], roster())
    assert len(diffs) == 1 and "phone" in diffs[0] and "Beta Org" in diffs[0]


def test_verify_fails_on_missing_partner_and_logo_loss(env):
    run(env)
    env["data"].delete("partners/gamma/logo.svg")
    env["data"].delete("partners/alpha_lab/partner.json")
    diffs, _ = mig.verify_migration(env["data"], roster())
    text = "\n".join(diffs)
    assert "missing from consolidated" in text or "partner count" in text
    assert "no logo object" in text


def test_cli_migrate_and_verify_exit_codes(env, monkeypatch, capsys):
    monkeypatch.setenv("PARTNER_SCRAPE_DATA_DIR", str(env["tmp"] / "data"))
    monkeypatch.setenv("PARTNER_SCRAPE_HISTORY_DIR", str(env["tmp"] / "history"))
    monkeypatch.setenv("SCRAPE_CACHE_DIR", str(env["tmp"] / "cache"))
    base = env["site"] / "src/data/partners.json"
    assert cli.main(["partners", "migrate", "--site-dir", str(env["site"]), "--dry-run"]) == 0
    assert env["data"].list("") == []
    assert cli.main(["partners", "migrate", "--site-dir", str(env["site"])]) == 0
    assert cli.main(["partners", "verify-migration", "--baseline", str(base)]) == 0
    rec = read_record(env["data"], "beta_org")
    rec["name"] = "Changed"
    env["data"].write_json("partners/beta_org/partner.json", rec)
    assert cli.main(["partners", "verify-migration", "--baseline", str(base)]) == 1
    assert "DIFF" in capsys.readouterr().err
