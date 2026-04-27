import json

from continuous_profiler.index import IndexStore
from continuous_profiler.storage import StorageManager


def test_generate_path_uses_utc_timestamp_and_duration(tmp_path):
    store = StorageManager(tmp_path, IndexStore(tmp_path / "index.jsonl"))

    result = store.generate_path("2026-04-27T13:00:00Z", 60)

    assert result == tmp_path / "profiles" / "20260427T130000Z_60s.perf.data"


def test_cleanup_deletes_expired_files_and_rewrites_index(tmp_path):
    index_store = IndexStore(tmp_path / "index.jsonl")
    storage = StorageManager(tmp_path, index_store)
    expired_path = storage.generate_path("2026-04-27T10:00:00Z", 60)
    current_path = storage.generate_path("2026-04-27T12:30:00Z", 60)
    expired_path.parent.mkdir(parents=True)
    expired_path.write_bytes(b"old")
    current_path.write_bytes(b"new")
    expired_record = {
        "start_time": "2026-04-27T10:00:00Z",
        "end_time": "2026-04-27T10:01:00Z",
        "perf_data_path": str(expired_path),
        "frequency": 99,
        "status": "success",
        "mode": "fake",
    }
    current_record = {
        "start_time": "2026-04-27T12:30:00Z",
        "end_time": "2026-04-27T12:31:00Z",
        "perf_data_path": str(current_path),
        "frequency": 99,
        "status": "success",
        "mode": "fake",
    }
    index_store.append(expired_record)
    index_store.append(current_record)

    deleted_count = storage.cleanup(retention_hours=2, now="2026-04-27T13:00:00Z")

    assert deleted_count == 1
    assert not expired_path.exists()
    assert current_path.exists()
    remaining_records = [
        json.loads(line)
        for line in (tmp_path / "index.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert remaining_records == [current_record]
