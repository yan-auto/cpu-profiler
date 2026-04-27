"""Profiler runners."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class PerfRunner(ABC):
    """Interface for producing perf data files."""

    @abstractmethod
    def run(self, output_path: str | Path, duration: int, frequency: int) -> None:
        """Write perf data to output_path."""


class FakePerfRunner(PerfRunner):
    """Deterministic runner for tests and local development."""

    def run(self, output_path: str | Path, duration: int, frequency: int) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"fake perf data {duration}s {frequency}hz\n".encode("utf-8"))
