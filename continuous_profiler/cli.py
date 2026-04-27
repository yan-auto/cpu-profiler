from __future__ import annotations

import json
import signal
import threading
from pathlib import Path
from typing import Any

import click

from continuous_profiler.collector import Collector
from continuous_profiler.flamegraph import FlameGraphRenderer
from continuous_profiler.index import IndexStore
from continuous_profiler.runner import PerfRecordRunner
from continuous_profiler.storage import StorageManager


DEFAULT_OUTPUT_DIR = Path(".profiler-data")


@click.group()
def main() -> None:
    """Continuous profiler command line interface."""


@main.command("collect-once")
@click.option("--duration", required=True, type=int)
@click.option("--frequency", required=True, type=int)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
)
def collect_once_command(duration: int, frequency: int, output_dir: Path) -> None:
    record = _collect_once(duration, frequency, output_dir)
    click.echo(f"collected {record['perf_data_path']}")


@main.command("start")
@click.option("--duration", required=True, type=int)
@click.option("--frequency", required=True, type=int)
@click.option("--retention-hours", required=True, type=int)
def start_command(duration: int, frequency: int, retention_hours: int) -> None:
    stop_event = threading.Event()

    def handle_sigterm(signum: int, frame: Any) -> None:
        stop_event.set()

    previous_handler = signal.signal(signal.SIGTERM, handle_sigterm)
    try:
        _run_start_loop(
            duration=duration,
            frequency=frequency,
            retention_hours=retention_hours,
            output_dir=DEFAULT_OUTPUT_DIR,
            stop_event=stop_event,
        )
    finally:
        signal.signal(signal.SIGTERM, previous_handler)


@main.command("render")
@click.option("--at", "timestamp", required=True)
@click.option("--out", "output_svg_path", required=True, type=click.Path(path_type=Path))
def render_command(timestamp: str, output_svg_path: Path) -> None:
    _render_at(timestamp, output_svg_path, DEFAULT_OUTPUT_DIR)
    click.echo(f"rendered {output_svg_path}")


@main.command("status")
def status_command() -> None:
    snapshot = _status_snapshot(DEFAULT_OUTPUT_DIR)
    click.echo(f"last_collection_time: {snapshot['last_collection_time']}")
    click.echo(f"file_count: {snapshot['file_count']}")
    click.echo(f"disk_usage_bytes: {snapshot['disk_usage_bytes']}")


@main.command("cleanup")
@click.option("--retention-hours", required=True, type=int)
def cleanup_command(retention_hours: int) -> None:
    deleted_count = _cleanup(retention_hours, DEFAULT_OUTPUT_DIR)
    click.echo(f"deleted_files: {deleted_count}")


def _collect_once(
    duration: int,
    frequency: int,
    output_dir: Path,
) -> dict[str, Any]:
    collector = _build_collector(output_dir)
    return collector.collect_once(duration=duration, frequency=frequency)


def _run_start_loop(
    duration: int,
    frequency: int,
    retention_hours: int,
    output_dir: Path,
    stop_event: threading.Event,
) -> None:
    collector = _build_collector(output_dir)
    storage = _build_storage(output_dir)
    while not stop_event.is_set():
        collector.collect_once(duration=duration, frequency=frequency)
        storage.cleanup(retention_hours)


def _render_at(timestamp: str, output_svg_path: Path, output_dir: Path) -> None:
    index_store = _build_index(output_dir)
    record = index_store.query(timestamp)
    if record is None:
        raise click.ClickException(f"no profile covers {timestamp}")

    FlameGraphRenderer().render(record["perf_data_path"], output_svg_path)


def _status_snapshot(output_dir: Path) -> dict[str, Any]:
    records = _read_records(_build_index(output_dir).index_path)
    profile_dir = output_dir / "profiles"
    files = [path for path in profile_dir.glob("*") if path.is_file()]
    return {
        "last_collection_time": records[-1]["end_time"] if records else "none",
        "file_count": len(files),
        "disk_usage_bytes": sum(path.stat().st_size for path in files),
    }


def _cleanup(retention_hours: int, output_dir: Path) -> int:
    return _build_storage(output_dir).cleanup(retention_hours)


def _build_collector(output_dir: Path) -> Collector:
    index_store = _build_index(output_dir)
    storage = StorageManager(output_dir, index_store)
    return Collector(PerfRecordRunner(), storage, index_store)


def _build_storage(output_dir: Path) -> StorageManager:
    index_store = _build_index(output_dir)
    return StorageManager(output_dir, index_store)


def _build_index(output_dir: Path) -> IndexStore:
    return IndexStore(output_dir / "index.jsonl")


def _read_records(index_path: Path) -> list[dict[str, Any]]:
    if not index_path.exists():
        return []

    records = []
    with index_path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


if __name__ == "__main__":
    main()
