import subprocess

import pytest

from continuous_profiler.errors import (
    PerfNotInstalledError,
    PerfPermissionError,
    PerfTimeoutError,
)
from continuous_profiler.runner import PerfRecordRunner


def test_perf_record_runner_builds_expected_command(tmp_path):
    executor = RecordingExecutor()
    output_path = tmp_path / "profiles" / "sample.perf.data"

    PerfRecordRunner(executor=executor).run(output_path, duration=60, frequency=99)

    assert executor.calls == [
        (
            [
                "perf",
                "record",
                "-F",
                "99",
                "-g",
                "-o",
                str(output_path),
                "--",
                "sleep",
                "60",
            ],
            {
                "check": True,
                "capture_output": True,
                "text": True,
                "timeout": 65,
            },
        )
    ]


def test_perf_record_runner_classifies_missing_perf(tmp_path):
    executor = FailingExecutor(FileNotFoundError())

    with pytest.raises(PerfNotInstalledError):
        PerfRecordRunner(executor=executor).run(tmp_path / "out.perf.data", 60, 99)


def test_perf_record_runner_classifies_permission_error(tmp_path):
    executor = FailingExecutor(
        subprocess.CalledProcessError(
            returncode=255,
            cmd=["perf"],
            stderr="Permission denied: check perf_event_paranoid",
        )
    )

    with pytest.raises(PerfPermissionError, match="sudo|perf_event_paranoid"):
        PerfRecordRunner(executor=executor).run(tmp_path / "out.perf.data", 60, 99)


def test_perf_record_runner_classifies_timeout(tmp_path):
    executor = FailingExecutor(
        subprocess.TimeoutExpired(
            cmd=["perf"],
            timeout=65,
        )
    )

    with pytest.raises(PerfTimeoutError):
        PerfRecordRunner(executor=executor).run(tmp_path / "out.perf.data", 60, 99)


class RecordingExecutor:
    def __init__(self):
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))


class FailingExecutor:
    def __init__(self, error):
        self.error = error

    def __call__(self, command, **kwargs):
        raise self.error
