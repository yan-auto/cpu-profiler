"""Flamegraph rendering pipeline."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable


class FlameGraphRenderError(RuntimeError):
    """Raised when a flamegraph rendering step fails."""


class FlameGraphRenderer:
    """Render perf data into an SVG flamegraph."""

    def __init__(self, executor: Callable[..., Any] = subprocess.run) -> None:
        self.executor = executor

    def render(self, perf_data_path: str | Path, output_svg_path: str | Path) -> None:
        perf_data = Path(perf_data_path)
        output_svg = Path(output_svg_path)
        script_output = perf_data.with_suffix(".script")
        folded_output = perf_data.with_suffix(".folded")

        output_svg.parent.mkdir(parents=True, exist_ok=True)
        script_output.parent.mkdir(parents=True, exist_ok=True)

        self._run_step(
            "perf script",
            ["perf", "script", "-i", str(perf_data)],
            script_output,
        )
        self._run_step(
            "stackcollapse-perf",
            ["stackcollapse-perf.pl", str(script_output)],
            folded_output,
        )
        self._run_step(
            "flamegraph",
            ["flamegraph.pl", str(folded_output)],
            output_svg,
        )

    def _run_step(self, step_name: str, command: list[str], output_path: Path) -> None:
        try:
            with output_path.open("w", encoding="utf-8") as output_file:
                self.executor(
                    command,
                    check=True,
                    stdout=output_file,
                    text=True,
                )
        except Exception as exc:
            raise FlameGraphRenderError(f"{step_name} failed") from exc
