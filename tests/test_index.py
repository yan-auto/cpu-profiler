from continuous_profiler.index import IndexStore


def test_append_and_query_hit(tmp_path):
    store = IndexStore(tmp_path / "index.jsonl")
    record = {
        "start_time": "2026-04-27T01:00:00Z",
        "end_time": "2026-04-27T01:01:00Z",
        "perf_data_path": "segments/perf.data",
        "frequency": 99,
        "status": "success",
        "mode": "fake",
    }

    store.append(record)

    assert store.query("2026-04-27T01:00:30Z") == record


def test_query_miss_returns_none(tmp_path):
    store = IndexStore(tmp_path / "index.jsonl")
    store.append(
        {
            "start_time": "2026-04-27T01:00:00Z",
            "end_time": "2026-04-27T01:01:00Z",
            "perf_data_path": "segments/perf.data",
            "frequency": 99,
            "status": "success",
            "mode": "fake",
        }
    )

    assert store.query("2026-04-27T01:01:00Z") is None


def test_query_skips_bad_lines(tmp_path):
    index_path = tmp_path / "index.jsonl"
    index_path.write_text(
        "\n".join(
            [
                "{bad json",
                '{"start_time": "not-a-date", "end_time": "2026-04-27T01:01:00Z"}',
                '{"start_time": "2026-04-27T01:00:00Z", "end_time": "2026-04-27T01:01:00Z", "perf_data_path": "segments/perf.data", "frequency": 99, "status": "success", "mode": "fake"}',
            ]
        ),
        encoding="utf-8",
    )

    result = IndexStore(index_path).query("2026-04-27T01:00:30Z")

    assert result == {
        "start_time": "2026-04-27T01:00:00Z",
        "end_time": "2026-04-27T01:01:00Z",
        "perf_data_path": "segments/perf.data",
        "frequency": 99,
        "status": "success",
        "mode": "fake",
    }
