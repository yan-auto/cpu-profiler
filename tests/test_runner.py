from continuous_profiler.runner import FakePerfRunner


def test_fake_perf_runner_writes_output_file(tmp_path):
    output_path = tmp_path / "profiles" / "sample.perf.data"

    FakePerfRunner().run(output_path, duration=60, frequency=99)

    assert output_path.read_bytes() == b"fake perf data 60s 99hz\n"
