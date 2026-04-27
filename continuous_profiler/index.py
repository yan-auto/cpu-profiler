"""JSONL index storage."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IndexStore:
    """Append-only JSONL index for profiling segments."""

    def __init__(self, index_path: str | Path) -> None:
        self.index_path = Path(index_path)

    def append(self, record: dict[str, Any]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("a", encoding="utf-8") as file:
            json.dump(record, file, ensure_ascii=False)
            file.write("\n")

    def query(self, timestamp: str | datetime) -> dict[str, Any] | None:
        target = _parse_iso8601(timestamp)
        if not self.index_path.exists():
            return None

        with self.index_path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    record = json.loads(line)
                    start_time = _parse_iso8601(record["start_time"])
                    end_time = _parse_iso8601(record["end_time"])
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue

                if start_time <= target < end_time:
                    return record

        return None


def _parse_iso8601(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
