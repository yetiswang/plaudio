import json, pathlib, pytest
from plaudio.plaud.cloud import PlaudClient, TokenStore


def test_token_store_reads_existing(tmp_path):
    f = tmp_path / "tokens.json"
    f.write_text(json.dumps({"access_token": "abc", "refresh_token": "xyz", "expires_at": 9999999999}))
    store = TokenStore(f)
    assert store.access_token() == "abc"


def test_token_store_missing_raises(tmp_path):
    store = TokenStore(tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError):
        store.access_token()


def test_client_list_recordings_returns_empty_v0(tmp_path):
    f = tmp_path / "tokens.json"
    f.write_text(json.dumps({"access_token": "abc"}))
    store = TokenStore(f)
    client = PlaudClient(token_store=store)
    assert client.list_recordings() == []


def test_client_presigned_url_not_implemented_v0(tmp_path):
    f = tmp_path / "tokens.json"
    f.write_text(json.dumps({"access_token": "abc"}))
    store = TokenStore(f)
    client = PlaudClient(token_store=store)
    with pytest.raises(NotImplementedError):
        client.presigned_url("any-id")
