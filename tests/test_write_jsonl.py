import json

import pytest

import server


@pytest.fixture
def jsonl_path(tmp_path, monkeypatch):
    path = tmp_path / "out" / "socketio.log"  # nested dir to test creation
    monkeypatch.setattr(server, "JSONL_LOG", path)
    return path


def read_lines(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def test_writes_single_line_with_keys(jsonl_path):
    server.write_jsonl({"data": {"foo": 1}})
    records = read_lines(jsonl_path)
    assert len(records) == 1
    assert "log_ts" in records[0]
    assert isinstance(records[0]["log_ts"], str)
    assert "data" in records[0]


def test_appends_on_multiple_calls(jsonl_path):
    server.write_jsonl({"data": {"a": 1}})
    server.write_jsonl({"data": {"b": 2}})
    records = read_lines(jsonl_path)
    assert len(records) == 2


def test_creates_parent_directory(jsonl_path):
    assert not jsonl_path.parent.exists()
    server.write_jsonl({"data": {"x": 1}})
    assert jsonl_path.parent.exists()


def test_unwraps_inner_data(jsonl_path):
    server.write_jsonl({"data": {"foo": 1}})
    record = read_lines(jsonl_path)[0]
    assert record["data"] == {"foo": 1}


def test_dict_without_data_key_stored_whole(jsonl_path):
    server.write_jsonl({"foo": 1})
    record = read_lines(jsonl_path)[0]
    assert record["data"] == {"foo": 1}


def test_non_dict_input_stored_as_is(jsonl_path):
    server.write_jsonl([1, 2, 3])
    record = read_lines(jsonl_path)[0]
    assert record["data"] == [1, 2, 3]
