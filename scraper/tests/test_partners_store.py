"""Tests for partner_scrape.partners (records, Roster, archiving writer)."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from partner_scrape import config
from partner_scrape.partners.records import list_slugs, load_roster, read_record
from partner_scrape.partners.writer import CHANGES_KEY, PartnerWriter
from partner_scrape.registry.validate_roster import RosterValidationError
from partner_scrape.storage import LocalStore, S3Store


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


def rec(slug="acme", id=1, **kw):
    return {"id": id, "slug": slug, "name": kw.pop("name", "Acme"), **kw}


@pytest.fixture
def w(tmp_path):
    return PartnerWriter(
        LocalStore(tmp_path / "data"), LocalStore(tmp_path / "history"), clock=Clock()
    )


def changes(w):
    text = w.history.read_text(CHANGES_KEY) or ""
    return [json.loads(x) for x in text.splitlines()]


def test_first_write_archives_nothing(w):
    entry = w.put_record("acme", rec(), "me")
    assert read_record(w.data, "acme") == rec()
    assert entry["archived"] is None
    assert entry["changed"] == ["id", "name", "slug"]
    assert w.history.list("partners/acme/") == []
    assert changes(w) == [entry]


def test_update_archives_old_and_logs_diff(w):
    w.put_record("acme", rec(), "me")
    entry = w.put_record("acme", rec(name="Acme Inc", city="SD"), "haiku")
    assert entry["changed"] == ["city", "name"]
    assert entry["actor"] == "haiku"
    key = entry["archived"].removeprefix("history/")
    assert key.endswith("-partner.json")
    assert json.loads(w.history.read_text(key)) == rec()
    assert read_record(w.data, "acme")["name"] == "Acme Inc"
    assert len(changes(w)) == 2


def test_noop_put_writes_and_logs_nothing(w):
    w.put_record("acme", rec(), "me")
    assert w.put_record("acme", rec(), "me") is None
    assert len(changes(w)) == 1
    assert w.history.list("partners/acme/") == []


def test_slug_must_match_record(w):
    with pytest.raises(ValueError):
        w.put_record("acme", rec(slug="other"), "me")
    with pytest.raises(ValueError):
        w.put_record("../x", rec(slug="../x"), "me")


def test_same_second_archives_do_not_collide(tmp_path):
    fixed = lambda: datetime(2026, 10, 8, tzinfo=timezone.utc)
    w = PartnerWriter(LocalStore(tmp_path / "d"), LocalStore(tmp_path / "h"), clock=fixed)
    for i in range(3):
        w.put_record("acme", rec(city=str(i)), "me")
    assert len(w.history.list("partners/acme/")) == 2


def test_logo_write_archive_and_noop(w):
    first = w.put_logo("acme", "PNG", b"one", "me")
    assert first["kind"] == "logo" and first["archived"] is None
    assert w.data.read_bytes("partners/acme/logo.png") == b"one"
    assert w.put_logo("acme", "png", b"one", "me") is None
    second = w.put_logo("acme", "png", b"two", "me")
    assert second["archived"].endswith("-logo.png")
    assert w.history.read_bytes(second["archived"].removeprefix("history/")) == b"one"
    assert len(changes(w)) == 2


def test_logo_extension_change_leaves_one_logo(w):
    w.put_logo("acme", "png", b"one", "me")
    entry = w.put_logo("acme", "jpg", b"two", "me")
    assert entry["archived"].endswith("-logo.png")
    assert w.data.list("partners/acme/") == ["partners/acme/logo.jpg"]


def test_roster_loader_keyed_by_stored_slug(w):
    w.put_record("acme", rec(), "me")
    w.put_record("zed_co", rec(slug="zed_co", id=2, name="Zed"), "me")
    w.put_logo("acme", "png", b"x", "me")
    assert list_slugs(w.data) == ["acme", "zed_co"]
    roster = load_roster(w.data)
    assert set(roster.by_slug) == {"acme", "zed_co"}
    assert [r["id"] for r in roster.as_list()] == [1, 2]
    assert len(roster) == 2


def test_stored_slug_not_rederived_from_name(w):
    w.put_record("custom_slug", rec(slug="custom_slug", name="Totally Different"), "me")
    assert load_roster(w.data).get("custom_slug")["name"] == "Totally Different"


def test_roster_rejects_slug_mismatch(w):
    w.data.write_json("partners/acme/partner.json", rec(slug="other"))
    with pytest.raises(RosterValidationError, match="does not match"):
        load_roster(w.data)


def test_roster_runs_content_validation(w):
    w.put_record("a", rec(slug="a", id=1, latitude=10.0, longitude=10.0), "me")
    with pytest.raises(RosterValidationError, match="outside"):
        load_roster(w.data)


def test_duplicate_stored_slug_flagged():
    from partner_scrape.registry.validate_roster import validate_roster

    with pytest.raises(RosterValidationError, match="shared by 2"):
        validate_roster([rec(id=1), rec(id=2, name="Other")])


def _s3_writer():
    from botocore.exceptions import ClientError

    client = MagicMock()
    client.get_object.side_effect = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
    client.head_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")
    paginator = MagicMock()
    paginator.paginate.return_value = [{}]
    client.get_paginator.return_value = paginator
    return client, PartnerWriter(
        S3Store("b", "data", client, public_read=True),
        S3Store("b", "history", client, public_read=False),
        clock=Clock(),
    )


def test_s3_acls_data_public_history_private():
    client, w = _s3_writer()
    w.put_record("acme", rec(), "me")
    w.put_logo("acme", "png", b"x", "me")
    calls = client.put_object.call_args_list
    assert calls
    for c in calls:
        key = c.kwargs["Key"]
        if key.startswith("data/"):
            assert c.kwargs["ACL"] == "public-read", key
        else:
            assert key.startswith("history/"), key
            assert "ACL" not in c.kwargs, key
    keys = {c.kwargs["Key"] for c in calls}
    assert "data/partners/acme/partner.json" in keys
    assert "data/partners/acme/logo.png" in keys
    assert "history/partners/changes.jsonl" in keys


def test_history_store_is_private_s3(monkeypatch):
    assert config.DEFAULT_HISTORY_LOCATION.endswith("/history")
    monkeypatch.setenv(config.PARTNER_SCRAPE_HISTORY_DIR_ENV_VAR, "s3://fake/history")
    monkeypatch.setattr(config, "_get_s3_client", lambda: MagicMock())
    store = config.get_history_store()
    assert isinstance(store, S3Store)
    assert store.public_read is False and store.prefix == "history"


# -- consolidation and CLI (ticket 042-003) ---------------------------------

from partner_scrape import cli  # noqa: E402
from partner_scrape.partners.consolidate import consolidate  # noqa: E402


def test_consolidate_envelope_shape(w):
    w.put_record("b_co", rec("b_co", id=2, name="B Co"), "t")
    w.put_record("acme", rec("acme", id=1, city="SD"), "t")
    env = consolidate(w.data, generated_at="2026-10-08T00:00:00Z")
    assert list(env) == ["generated_at", "partner_count", "partners"]
    assert env["partner_count"] == 2
    assert [p["slug"] for p in env["partners"]] == ["acme", "b_co"]
    first = env["partners"][0]
    assert list(first) == ["id", "name", "city", "slug", "events_url", "past_events_url"]
    assert first["events_url"] == "partners/acme/events.json"
    assert first["past_events_url"] == "partners/acme/past-events.json"
    assert json.loads(w.data.read_text("partners.json")) == env


def test_consolidate_matches_publish_entry():
    from partner_scrape.partners.consolidate import published_entry

    e = published_entry({"id": 1, "name": "X"}, "x")
    assert list(e) == ["id", "name", "slug", "events_url", "past_events_url"]


def test_consolidate_bad_record_names_slug_and_keeps_old_file(w):
    w.put_record("acme", rec("acme"), "t")
    w.put_record("bad", rec("bad", id=2, name="Bad", latitude=999, longitude=0), "t")
    w.data.write_text("partners.json", "OLD")
    with pytest.raises(RosterValidationError, match="bad"):
        consolidate(w.data)
    assert w.data.read_text("partners.json") == "OLD"


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    data, hist = LocalStore(tmp_path / "data"), LocalStore(tmp_path / "history")
    monkeypatch.setattr(config, "get_data_store", lambda: data)
    monkeypatch.setattr(config, "get_history_store", lambda: hist)
    monkeypatch.setenv("USER", "tester")
    return data, hist, tmp_path


def test_cli_add_get_put_consolidate(cli_env, capsys):
    data, hist, tmp = cli_env
    assert cli.main(["partners", "add", "--name", "Acme Robotics"]) == 0
    assert cli.main(["partners", "add", "--name", "Beta Labs", "--by", "haiku"]) == 0
    a = read_record(data, "acme_robotics")
    assert a["id"] == 1 and a["slug"] == "acme_robotics"
    assert read_record(data, "beta_labs")["id"] == 2
    assert cli.main(["partners", "add", "--name", "Acme Robotics"]) == 1  # duplicate
    log = [json.loads(x) for x in hist.read_text(CHANGES_KEY).splitlines()]
    assert [e["actor"] for e in log] == ["person:tester", "haiku"]

    capsys.readouterr()
    assert cli.main(["partners", "get", "acme_robotics"]) == 0
    assert json.loads(capsys.readouterr().out)["name"] == "Acme Robotics"
    assert cli.main(["partners", "get", "nope"]) == 1

    f = tmp / "r.json"
    f.write_text(json.dumps({**a, "city": "San Diego"}))
    assert cli.main(["partners", "put", "acme_robotics", str(f), "--by", "me"]) == 0
    assert read_record(data, "acme_robotics")["city"] == "San Diego"

    assert cli.main(["partners", "consolidate"]) == 0
    assert json.loads(data.read_text("partners.json"))["partner_count"] == 2


def test_cli_put_validates_before_writing(cli_env, capsys):
    data, hist, tmp = cli_env
    f = tmp / "r.json"
    f.write_text(json.dumps({"id": 1, "name": "X", "latitude": 999, "longitude": 0}))
    assert cli.main(["partners", "put", "x", str(f)]) == 1
    assert read_record(data, "x") is None
    f.write_text(json.dumps({"id": 1, "slug": "other", "name": "X"}))
    assert cli.main(["partners", "put", "x", str(f)]) == 1
    assert read_record(data, "x") is None


def test_cli_consolidate_failure_exits_nonzero_naming_slug(cli_env, capsys):
    data, hist, tmp = cli_env
    data.write_json("partners/bad/partner.json", {"id": 1, "slug": "bad", "name": "B", "latitude": 999, "longitude": 0})
    data.write_text("partners.json", "OLD")
    assert cli.main(["partners", "consolidate"]) == 1
    assert "bad" in capsys.readouterr().err
    assert data.read_text("partners.json") == "OLD"
