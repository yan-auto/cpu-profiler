# continuous_profiler

这是一个用于 Linux 持续 CPU Profiling 的 Python CLI 工具，基于 `perf`、JSONL 时间索引和 FlameGraph 渲染，适合 7x24 保存采样数据，并在故障后按时间点回溯生成火焰图。

## 使用前提

- 运行环境需要是 Linux，并安装 `perf`。
- 生成火焰图需要安装 FlameGraph 工具链，确保 `stackcollapse-perf.pl` 和 `flamegraph.pl` 在 `PATH` 中。
- 当前用户需要有采样权限；如果遇到权限错误，需要使用 `sudo` 或调整 `perf_event_paranoid`。
- 测试默认使用 `FakePerfRunner` 或 fake executor，不依赖真实 `perf`。

## 安装

开发模式安装：

```bash
pip install -e .[dev]
```

安装后会暴露 `continuous-profiler` CLI entry point。

## 使用说明

### 单次采集

执行一次 60 秒、99Hz 的 CPU 采样，并把采样文件和 `index.jsonl` 写到 `.profiler-data`：

```bash
continuous-profiler collect-once --duration 60 --frequency 99 --output-dir .profiler-data
```

### 持续运行

持续按固定窗口采集，并按保留时间清理历史文件。收到 `SIGTERM` 后会优雅退出：当前采集结束后停止下一轮。

```bash
continuous-profiler start --duration 60 --frequency 99 --retention-hours 24
```

### 按时间点生成火焰图

根据 `index.jsonl` 查询覆盖指定时间点的 `perf.data`，再生成 SVG 火焰图：

```bash
continuous-profiler render --at "2026-04-27T13:00:00Z" --out flame.svg
```

### 查看状态

输出最近一次采集时间、文件数和磁盘占用：

```bash
continuous-profiler status
```

### 手动清理

按保留时间删除超期采样文件，并同步清理 `index.jsonl` 中对应记录：

```bash
continuous-profiler cleanup --retention-hours 24
```

## 数据目录

默认数据目录是 `.profiler-data`，核心结构如下：

```text
.profiler-data/
  index.jsonl
  profiles/
    20260427T130000Z_60s.perf.data
    20260427T130000Z_60s.perf.script
    20260427T130000Z_60s.perf.folded
```

`index.jsonl` 每行是一条 JSON 记录，包含：

```json
{
  "start_time": "2026-04-27T13:00:00Z",
  "end_time": "2026-04-27T13:01:00Z",
  "perf_data_path": ".profiler-data/profiles/20260427T130000Z_60s.perf.data",
  "frequency": 99,
  "status": "success",
  "mode": "fake"
}
```

## 复用

查看 [SKILL.md](SKILL.md)，里面沉淀了可复用的中文 workflow，包括阶段化实现步骤、关键设计决策、当前局限和生产化扩展方向。

## 设计说明

### IndexStore

`IndexStore` 负责维护 `index.jsonl`。写入采用 append-only JSONL；查询采用半开区间规则：

```text
start_time <= target_time < end_time
```

读取时会跳过坏行，避免进程崩溃或写入中断后整个索引不可用。

### StorageManager

`StorageManager` 负责生成采样文件路径和执行 retention cleanup。路径格式固定为：

```text
profiles/YYYYMMDDTHHMMSSZ_<duration>s.perf.data
```

清理时会同时删除超期 `perf.data` 文件，并重写 `index.jsonl`，保证文件系统和时间索引对账一致。

### PerfRunner

`PerfRunner` 是 runner 抽象，用来隔离系统依赖。

- `FakePerfRunner` 用于测试和本地闭环验证，只写占位文件。
- `PerfRecordRunner` 调用真实命令：`perf record -F <frequency> -g -o <output_path> -- sleep <duration>`。
- `PerfRecordRunner` 会分类抛出 `PerfNotInstalledError`、`PerfPermissionError`、`PerfTimeoutError`。

### Collector

`Collector` 通过依赖注入组合 `PerfRunner`、`StorageManager` 和 `IndexStore`。

关键约束是：runner 成功后才写 `index.jsonl`；如果采集失败，不写 index，避免后续按时间点查询命中无效记录。

### FlameGraphRenderer

`FlameGraphRenderer` 将 `perf.data` 渲染为 SVG，内部三步：

```bash
perf script -i <perf_data> > <script_output>
stackcollapse-perf.pl <script_output> > <folded_output>
flamegraph.pl <folded_output> > <output_svg>
```

`.script` 和 `.folded` 中间文件会保留在同目录，方便线上 debug。任一步失败都会抛出带步骤名的明确错误。

### CLI

CLI 使用 `click` 实现，命令层只负责参数解析和模块编排。测试通过 `click.testing.CliRunner` 验证入参和调用，不直接依赖真实 `perf`。

## 局限

- 当前是单机工具，不包含分布式归档和集中查询。
- `start` 当前使用默认 `.profiler-data` 目录，没有暴露 `--output-dir`。
- 采样窗口之间没有复杂调度补偿，长时间运行建议交给 `systemd` 托管。
- 默认示例使用 99Hz，极短暂 CPU 峰值可能无法完整采样。

## 测试

```bash
pytest tests/ -v
```

## 完整 commit 历史

```text
08ae186 feat(cli): integrate all commands with click
4fdb55c feat(flamegraph): implement 3-step rendering pipeline
858685a feat(runner): implement PerfRecordRunner with error classification
6cd647f feat(collector): implement collect-once with index isolation
19ad69d feat(runner): add PerfRunner interface and Fake impl
5b16ad0 feat(storage): implement StorageManager with retention
a0de58c feat(index): implement IndexStore with crash recovery
89466e8 chore: init project skeleton
```
