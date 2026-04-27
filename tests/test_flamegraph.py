import pytest
from pathlib import Path

from continuous_profiler.flamegraph import FlameGraphRenderer, FlameGraphRenderError


def test_render_runs_three_steps_in_order(tmp_path):
    executor = RecordingExecutor()
    perf_data = tmp_path / "profiles" / "sample.perf.data"
    output_svg = tmp_path / "profiles" / "sample.svg"
    perf_data.parent.mkdir()
    perf_data.write_bytes(b"perf")

    FlameGraphRenderer(executor=executor).render(perf_data, output_svg)

    assert executor.calls == [
        (["perf", "script", "-i", str(perf_data)], tmp_path / "profiles" / "sample.perf.script"),
        (["stackcollapse-perf.pl", str(tmp_path / "profiles" / "sample.perf.script")], tmp_path / "profiles" / "sample.perf.folded"),
        (["flamegraph.pl", str(tmp_path / "profiles" / "sample.perf.folded")], output_svg),
    ]
    assert (tmp_path / "profiles" / "sample.perf.script").exists()
    assert (tmp_path / "profiles" / "sample.perf.folded").exists()
    assert output_svg.exists()


def test_render_error_includes_step_name(tmp_path):
    executor = FailingOnSecondStep()
    perf_data = tmp_path / "sample.perf.data"
    perf_data.write_bytes(b"perf")

    with pytest.raises(FlameGraphRenderError, match="stackcollapse-perf failed"):
        FlameGraphRenderer(executor=executor).render(perf_data, tmp_path / "sample.svg")


class RecordingExecutor:
    def __init__(self):
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, Path(kwargs["stdout"].name)))
        kwargs["stdout"].write("ok\n")


class FailingOnSecondStep:
    def __init__(self):
        self.calls = 0

    def __call__(self, command, **kwargs):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("boom")
        kwargs["stdout"].write("ok\n")
