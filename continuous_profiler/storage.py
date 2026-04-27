"""Storage helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from continuous_profiler.index import IndexStore


class StorageManager:
    """Manage perf data paths and retention cleanup."""

    def __init__(self, root_dir: str | Path, index_store: IndexStore) -> None:
        self.root_dir = Path(root_dir)
        self.index_store = index_store

    def generate_path(self, start_time: str | datetime, duration: int) -> Path:
        start = _parse_iso8601(start_time)
        filename = f"{start.strftime('%Y%m%dT%H%M%SZ')}_{duration}s.perf.data"
        return self.root_dir / "profiles" / filename

    def cleanup(self, retention_hours: int, now: str | datetime | None = None) -> int:
        cutoff = _parse_iso8601(now or datetime.now(timezone.utc)) - timedelta(
            hours=retention_hours
        )
        index_path = self.index_store.index_path
        if not index_path.exists():
            return 0

        kept_records: list[dict[str, Any]] = []
        deleted_count = 0
        for record in _read_valid_records(index_path):
            end_time = _parse_iso8601(record["end_time"])
            if end_time < cutoff:
                perf_path = Path(record["perf_data_path"])
                if not perf_path.is_absolute():
                    perf_path = self.root_dir / perf_path
                if perf_path.exists():
                    perf_path.unlink()
                    deleted_count += 1
                continue

            kept_records.append(record)

        with index_path.open("w", encoding="utf-8") as file:
            for record in kept_records:
                json.dump(record, file, ensure_ascii=False)
                file.write("\n")

        return deleted_count


def _read_valid_records(index_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with index_path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                record = json.loads(line)
                _parse_iso8601(record["end_time"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            records.append(record)
    return records


def _parse_iso8601(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
