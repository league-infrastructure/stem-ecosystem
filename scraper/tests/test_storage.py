"""Tests for `partner_scrape.storage`: LocalStore and S3Store (moto, offline)."""

import boto3
import pytest
from moto import mock_aws

from partner_scrape.storage import LocalStore, S3Store, store_from_location

BUCKET = "test-bucket"


@pytest.fixture(params=["local", "s3"])
def store(request, tmp_path):
    if request.param == "local":
        yield LocalStore(tmp_path / "root")
    else:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=BUCKET)
            yield S3Store(BUCKET, "pfx", client)


def test_missing_key_reads_none(store):
    assert store.read_bytes("a/b.json") is None
    assert store.read_text("a/b.json") is None
    assert store.read_json("a/b.json") is None
    assert store.exists("a/b.json") is False


def test_bytes_round_trip(store):
    store.write_bytes("img/x.png", b"\x89PNG\x00", "image/png")
    assert store.read_bytes("img/x.png") == b"\x89PNG\x00"
    assert store.exists("img/x.png") is True


def test_text_and_json_round_trip(store):
    store.write_text("n/t.txt", "héllo")
    assert store.read_text("n/t.txt") == "héllo"
    store.write_json("n/j.json", {"a": [1, 2], "b": "é"})
    assert store.read_json("n/j.json") == {"a": [1, 2], "b": "é"}
    assert store.read_text("n/j.json").startswith('{\n  "a"')  # indent=2


def test_overwrite(store):
    store.write_text("k", "one")
    store.write_text("k", "two")
    assert store.read_text("k") == "two"


def test_list_by_prefix(store):
    for k in ("hosts/a.json", "hosts/b.json", "programs/c.json"):
        store.write_json(k, {})
    assert store.list("hosts/") == ["hosts/a.json", "hosts/b.json"]
    assert store.list() == ["hosts/a.json", "hosts/b.json", "programs/c.json"]
    assert store.list("nope/") == []


def test_local_creates_parent_dirs_and_leaves_no_tmp(tmp_path):
    s = LocalStore(tmp_path / "r")
    s.write_text("deep/er/f.txt", "x")
    assert (tmp_path / "r" / "deep" / "er" / "f.txt").read_text() == "x"
    assert not list((tmp_path / "r").rglob("*.tmp"))


def test_local_write_failure_cleans_tmp_and_raises(tmp_path):
    s = LocalStore(tmp_path)
    (tmp_path / "blocker").write_text("file, not dir")
    with pytest.raises(RuntimeError):
        s.write_text("blocker/f.txt", "x")
    assert not list(tmp_path.rglob("*.tmp"))


@mock_aws
def test_s3_applies_prefix_and_content_type():
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=BUCKET)
    s = S3Store(BUCKET, "cache/", client)
    s.write_json("hosts/a.json", {"x": 1})
    s.write_bytes("i.png", b"1", "image/png")
    head = client.head_object(Bucket=BUCKET, Key="cache/hosts/a.json")
    assert head["ContentType"] == "application/json"
    assert client.head_object(Bucket=BUCKET, Key="cache/i.png")["ContentType"] == "image/png"
    assert s.list("hosts/") == ["hosts/a.json"]


@mock_aws
def test_s3_empty_prefix():
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=BUCKET)
    s = S3Store(BUCKET, "", client)
    s.write_text("a.txt", "x")
    assert client.get_object(Bucket=BUCKET, Key="a.txt")["Body"].read() == b"x"
    assert s.list() == ["a.txt"]


@mock_aws
def test_s3_other_errors_propagate():
    from botocore.exceptions import ClientError

    client = boto3.client("s3", region_name="us-east-1")  # no bucket created
    with pytest.raises(ClientError):
        S3Store("missing-bucket", "p", client).read_bytes("k")


@mock_aws
def test_store_from_location():
    client = boto3.client("s3", region_name="us-east-1")
    s3 = store_from_location("s3://bkt/some/prefix/", client)
    assert isinstance(s3, S3Store)
    assert (s3.bucket, s3.prefix) == ("bkt", "some/prefix")
    assert isinstance(store_from_location("/tmp/x"), LocalStore)
    from pathlib import Path

    assert isinstance(store_from_location(Path("rel/dir")), LocalStore)


def test_storage_does_not_import_config():
    import partner_scrape.storage as m

    assert "config" not in vars(m)


def test_delete_removes_key_and_missing_key_is_not_an_error(store):
    store.write_bytes("d/x.bin", b"1")
    store.delete("d/x.bin")
    assert store.exists("d/x.bin") is False
    store.delete("d/x.bin")  # already gone: no error


def _acl_store(prefix, public_read):
    from unittest.mock import MagicMock

    client = MagicMock()
    return S3Store(BUCKET, prefix, client, public_read=public_read), client


def test_public_read_store_sets_acl_on_writes():
    s, client = _acl_store("data", True)
    s.write_bytes("partners/x/events.json", b"{}", "application/json")
    s.write_json("scrape-meta.json", {})
    for call in client.put_object.call_args_list:
        assert call.kwargs["ACL"] == "public-read"
        assert call.kwargs["Key"].startswith("data/")


def test_private_store_has_no_acl():
    s, client = _acl_store("cache", False)
    s.write_bytes("hosts/a.json", b"{}")
    assert "ACL" not in client.put_object.call_args.kwargs


def test_store_from_location_public_read_flag():
    from unittest.mock import MagicMock

    assert store_from_location("s3://b/data", MagicMock(), public_read=True).public_read
    assert not store_from_location("s3://b/cache", MagicMock()).public_read


def test_get_data_store_public_cache_private(monkeypatch):
    from partner_scrape import config

    monkeypatch.setenv("DO_SPACES_ENDPOINT", "https://sfo3.digitaloceanspaces.com")
    monkeypatch.setenv("DO_SPACES_ACCESS_KEY", "a")
    monkeypatch.setenv("DO_SPACES_SECRET_KEY", "b")
    monkeypatch.setenv("PARTNER_SCRAPE_DATA_DIR", "s3://bkt/data")
    monkeypatch.setenv("SCRAPE_CACHE_DIR", "s3://bkt/cache")
    with mock_aws():
        assert config.get_data_store().public_read is True
        assert config.get_scrape_cache_store().public_read is False


def test_backfill_sets_acl_on_data_keys_only():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "backfill", Path(__file__).parent.parent / "scripts" / "backfill_public_read.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    s, client = _acl_store("data", True)
    client.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": "data/a.json"}, {"Key": "data/images/b.png"}]}
    ]
    assert mod.backfill(s, dry_run=True) == 2
    client.put_object_acl.assert_not_called()
    assert mod.backfill(s) == 2
    keys = [c.kwargs["Key"] for c in client.put_object_acl.call_args_list]
    assert keys == ["data/a.json", "data/images/b.png"]
    assert all(
        c.kwargs["ACL"] == "public-read" for c in client.put_object_acl.call_args_list
    )
