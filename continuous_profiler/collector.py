"""Collection orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from continuous_profiler.index import IndexStore
from continuous_profiler.runner import PerfRunner
from continuous_profiler.storage import StorageManager


class Collector:
    """Collect one perf segment and append a successful index record."""

    def __init__(
        self,
        runner: PerfRunner,
        storage: StorageManager,
        index_store: IndexStore,
    ) -> None:
        self.runner = runner
        self.storage = storage
        self.index_store = index_store

    def collect_once(
        self,
        duration: int,
        frequency: int,
        start_time: str | datetime | None = None,
    ) -> dict[str, Any]:
        start = _parse_iso8601(start_time or datetime.now(timezone.utc))
        end = start + timedelta(seconds=duration)
        output_path = self.storage.generate_path(start, duration)

        self.runner.run(output_path, duration, frequency)

        record = {
            "start_time": _format_iso8601(start),
            "end_time": _format_iso8601(end),
            "perf_data_path": str(output_path),
            "frequency": frequency,
            "status": "success",
            "mode": "fake",
        }
        self.index_store.append(record)
        return record


def _parse_iso8601(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_iso8601(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
