from pathlib import Path

import pytest

from continuous_profiler.collector import Collector
from continuous_profiler.index import IndexStore
from continuous_profiler.runner import FakePerfRunner, PerfRunner
from continuous_profiler.storage import StorageManager


def test_collect_once_writes_perf_data_and_index_record(tmp_path):
    index_store = IndexStore(tmp_path / "index.jsonl")
    storage = StorageManager(tmp_path, index_store)
    collector = Collector(FakePerfRunner(), storage, index_store)

    record = collector.collect_once(
        duration=60,
        frequency=99,
        start_time="2026-04-27T13:00:00Z",
    )

    output_path = Path(record["perf_data_path"])
    assert output_path.exists()
    assert output_path == storage.generate_path("2026-04-27T13:00:00Z", 60)
    assert index_store.query("2026-04-27T13:00:30Z") == record


def test_collect_once_does_not_write_index_when_runner_fails(tmp_path):
    index_store = IndexStore(tmp_path / "index.jsonl")
    storage = StorageManager(tmp_path, index_store)
    collector = Collector(FailingRunner(), storage, index_store)

    with pytest.raises(RuntimeError, match="runner failed"):
        collector.collect_once(
            duration=60,
            frequency=99,
            start_time="2026-04-27T13:00:00Z",
        )

    assert not (tmp_path / "index.jsonl").exists()


class FailingRunner(PerfRunner):
    def run(self, output_path, duration, frequency):
        raise RuntimeError("runner failed")
