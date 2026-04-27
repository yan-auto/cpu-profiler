from pathlib import Path

from click.testing import CliRunner

from continuous_profiler import cli


def test_collect_once_passes_options(monkeypatch, tmp_path):
    calls = []

    def fake_collect_once(duration, frequency, output_dir):
        calls.append((duration, frequency, output_dir))
        return {"perf_data_path": "profiles/sample.perf.data"}

    monkeypatch.setattr(cli, "_collect_once", fake_collect_once)

    result = CliRunner().invoke(
        cli.main,
        [
            "collect-once",
            "--duration",
            "60",
            "--frequency",
            "99",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert calls == [(60, 99, tmp_path)]


def test_start_passes_options_and_stop_event(monkeypatch):
    calls = []

    def fake_start_loop(duration, frequency, retention_hours, output_dir, stop_event):
        calls.append((duration, frequency, retention_hours, output_dir, stop_event.is_set()))

    monkeypatch.setattr(cli, "_run_start_loop", fake_start_loop)

    result = CliRunner().invoke(
        cli.main,
        [
            "start",
            "--duration",
            "30",
            "--frequency",
            "49",
            "--retention-hours",
            "24",
        ],
    )

    assert result.exit_code == 0
    assert calls == [(30, 49, 24, cli.DEFAULT_OUTPUT_DIR, False)]


def test_render_passes_options(monkeypatch, tmp_path):
    calls = []
    output_svg = tmp_path / "out.svg"

    def fake_render_at(timestamp, output_svg_path, output_dir):
        calls.append((timestamp, output_svg_path, output_dir))

    monkeypatch.setattr(cli, "_render_at", fake_render_at)

    result = CliRunner().invoke(
        cli.main,
        [
            "render",
            "--at",
            "2026-04-27T13:00:00Z",
            "--out",
            str(output_svg),
        ],
    )

    assert result.exit_code == 0
    assert calls == [("2026-04-27T13:00:00Z", output_svg, cli.DEFAULT_OUTPUT_DIR)]


def test_status_prints_snapshot(monkeypatch):
    calls = []

    def fake_status_snapshot(output_dir):
        calls.append(output_dir)
        return {
            "last_collection_time": "2026-04-27T13:01:00Z",
            "file_count": 2,
            "disk_usage_bytes": 128,
        }

    monkeypatch.setattr(cli, "_status_snapshot", fake_status_snapshot)

    result = CliRunner().invoke(cli.main, ["status"])

    assert result.exit_code == 0
    assert calls == [cli.DEFAULT_OUTPUT_DIR]
    assert "last_collection_time: 2026-04-27T13:01:00Z" in result.output
    assert "file_count: 2" in result.output
    assert "disk_usage_bytes: 128" in result.output


def test_cleanup_passes_retention_hours(monkeypatch):
    calls = []

    def fake_cleanup(retention_hours, output_dir):
        calls.append((retention_hours, output_dir))
        return 3

    monkeypatch.setattr(cli, "_cleanup", fake_cleanup)

    result = CliRunner().invoke(
        cli.main,
        [
            "cleanup",
            "--retention-hours",
            "12",
        ],
    )

    assert result.exit_code == 0
    assert calls == [(12, cli.DEFAULT_OUTPUT_DIR)]
    assert "deleted_files: 3" in result.output
