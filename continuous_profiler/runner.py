"""Profiler runners."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

from continuous_profiler.errors import (
    PerfNotInstalledError,
    PerfPermissionError,
    PerfRunnerError,
    PerfTimeoutError,
)


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


class PerfRecordRunner(PerfRunner):
    """Run Linux perf record for a bounded sleep workload."""

    def __init__(
        self,
        executor: Callable[..., Any] = subprocess.run,
        timeout_padding: int = 5,
    ) -> None:
        self.executor = executor
        self.timeout_padding = timeout_padding

    def run(self, output_path: str | Path, duration: int, frequency: int) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "perf",
            "record",
            "-F",
            str(frequency),
            "-g",
            "-o",
            str(path),
            "--",
            "sleep",
            str(duration),
        ]

        try:
            self.executor(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=duration + self.timeout_padding,
            )
        except FileNotFoundError as exc:
            raise PerfNotInstalledError("perf is not installed or not on PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise PerfTimeoutError("perf record timed out") from exc
        except subprocess.CalledProcessError as exc:
            message = _process_error_message(exc)
            if _is_permission_error(message):
                raise PerfPermissionError(
                    "perf permission denied; try sudo or adjust perf_event_paranoid"
                ) from exc
            raise PerfRunnerError(message or "perf record failed") from exc


def _process_error_message(error: subprocess.CalledProcessError) -> str:
    return "\n".join(
        part for part in [str(error.stderr or ""), str(error.stdout or "")] if part
    )


def _is_permission_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in [
            "permission denied",
            "operation not permitted",
            "perf_event_paranoid",
        ]
    )
