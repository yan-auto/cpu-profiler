# continuous_profiler

Python CLI for Linux continuous CPU profiling with `perf`, JSONL time indexes, and FlameGraph rendering.

## Commands

```bash
continuous-profiler collect-once --duration 60 --frequency 99 --output-dir .profiler-data
continuous-profiler start --duration 60 --frequency 99 --retention-hours 24
continuous-profiler render --at "2026-04-27T13:00:00Z" --out flame.svg
continuous-profiler status
continuous-profiler cleanup --retention-hours 24
```

## Reuse

See [SKILL.md](SKILL.md) for the reusable Chinese workflow covering the staged implementation, design decisions, limits, and production extensions.

## Test

```bash
pytest tests/ -v
```
