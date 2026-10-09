"""Tests for partner_scrape.logs and the logs logs-store privacy."""

import json
from unittest.mock import MagicMock

from partner_scrape import config, logs
from partner_scrape.storage import LocalStore, S3Store


def _upload(store, tmp_path, text, job="scrape", exit_code=0):
    f = tmp_path / "out.log"
    f.write_text(text)
    return logs.upload_log(
        store,
        job=job,
        log_file=f,
        start="2026-10-08T03:00:00Z",
        end="2026-10-08T03:05:00Z",
        exit_code=exit_code,
        duration=300,
    )


def test_upload_writes_log_and_index(tmp_path):
    store = LocalStore(tmp_path / "bucket")
    key = _upload(store, tmp_path, "hello\npartner-scrape: wrote 12 opportunities.\n")
    assert key == "scrape/20261008T030000Z-scrape.log"
    assert "hello" in store.read_text(key)
    line = json.loads(store.read_text("index.jsonl").splitlines()[0])
    assert line["job"] == "scrape" and line["exit_code"] == 0
    assert line["duration_s"] == 300
    assert line["log"] == f"logs/{key}"
    assert line["events_written"] == 12 and line["errors"] == 0


def test_index_appends(tmp_path):
    store = LocalStore(tmp_path / "bucket")
    _upload(store, tmp_path, "a", job="teams", exit_code=1)
    _upload(store, tmp_path, "b", job="directory")
    lines = store.read_text("index.jsonl").splitlines()
    assert [json.loads(x)["job"] for x in lines] == ["teams", "directory"]
    assert store.exists("teams/20261008T030000Z-teams.log")


def test_errors_counted(tmp_path):
    store = LocalStore(tmp_path / "bucket")
    _upload(store, tmp_path, "ERROR x\nTraceback (most recent call last):\n", exit_code=1)
    assert json.loads(store.read_text("index.jsonl"))["errors"] == 2


def test_secret_values_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sentinel-secret-12345")
    store = LocalStore(tmp_path / "bucket")
    key = _upload(store, tmp_path, "using sentinel-secret-12345 here\n")
    blob = store.read_text(key) + store.read_text("index.jsonl")
    assert "sentinel-secret-12345" not in blob
    assert "***" in blob


def test_s3_writes_are_private(tmp_path):
    client = MagicMock()
    client.get_object.side_effect = _no_such_key()
    store = S3Store("b", "logs", client, public_read=False)
    _upload(store, tmp_path, "x")
    assert client.put_object.call_count == 2
    for call in client.put_object.call_args_list:
        assert "ACL" not in call.kwargs
        assert call.kwargs["Key"].startswith("logs/")


def _no_such_key():
    from botocore.exceptions import ClientError

    return ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")


def test_logs_store_is_private_s3(monkeypatch):
    assert config.DEFAULT_LOGS_LOCATION.endswith("/logs")
    monkeypatch.setenv(config.PARTNER_SCRAPE_LOGS_DIR_ENV_VAR, "s3://fake-bucket/logs")
    monkeypatch.setenv(config.PARTNER_SCRAPE_DATA_DIR_ENV_VAR, "s3://fake-bucket/data")
    monkeypatch.setattr(config, "_get_s3_client", lambda: MagicMock())
    store = config.get_logs_store()
    assert isinstance(store, S3Store)
    assert store.public_read is False
    assert store.prefix == "logs"
    assert config.get_data_store().public_read is True


def test_cli_logs_upload(tmp_path, monkeypatch):
    from partner_scrape import cli

    monkeypatch.setenv(config.PARTNER_SCRAPE_LOGS_DIR_ENV_VAR, str(tmp_path / "L"))
    f = tmp_path / "o.log"
    f.write_text("hi\n")
    rc = cli.main(
        ["logs", "upload", "--job", "directory", "--file", str(f), "--start",
         "2026-10-08T03:00:00Z", "--end", "2026-10-08T03:00:09Z",
         "--exit-code", "0", "--duration", "9"]
    )
    assert rc == 0
    assert (tmp_path / "L" / "index.jsonl").exists()
