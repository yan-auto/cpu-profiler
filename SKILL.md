---
name: linux-continuous-cpu-profiling
description: 用Python CLI + perf + JSONL时间索引 + FlameGraph,构建Linux 7x24持续CPU Profiling黑匣子工具。适用于线上CPU异常事后排查、按时间点回溯采样数据生成火焰图的场景。
version: 0.1.0
---

# Linux 持续 CPU Profiling Skill

## 何时使用

- 线上服务偶发 CPU 飙高，问题发生时无法及时手动执行 `perf`。
- 需要 7x24 低成本保存 CPU 采样数据，用于事后排查。
- 需要根据故障时间点回溯对应采样片段，并生成火焰图。
- 需要把 Linux `perf` 能力封装成团队可复用诊断工具。
- 需要用测试驱动方式构建不依赖真实机器环境的性能诊断 CLI。

## 工作流

### 1. 项目骨架 + IndexStore（时间索引先行）

做什么：先搭 Python 项目骨架，建立 `continuous_profiler` 包、`tests/`、`pyproject.toml`、README，再实现 `IndexStore` 维护 `index.jsonl`。

为什么：持续采样工具的核心不是先跑 `perf`，而是先保证采样片段能按时间点被可靠检索。JSONL 追加写简单，坏行可跳过，适合崩溃恢复。

关键命令：

```bash
pytest tests/test_index.py -v
git add .
git commit -m "feat(index): implement IndexStore with crash recovery"
```

纪律：测试通过后才能提交；如果失败，先修复，不许跳过。

### 2. StorageManager + FakePerfRunner + Collector（用 Fake 跑通闭环）

做什么：实现 `StorageManager.generate_path()` 生成 `profiles/20260427T130000Z_60s.perf.data` 这类路径；实现 `FakePerfRunner` 写占位文件；实现 `Collector.collect_once()` 串起 runner、storage、index。

为什么：先用 fake runner 跑通“采集文件落盘 -> index 写入 -> query 可查”的闭环，避免早期被 Linux 权限、`perf` 安装、环境差异卡住。

关键命令：

```bash
pytest tests/test_storage.py tests/test_runner.py tests/test_collector.py -v
git add .
git commit -m "feat(collector): implement collect-once with index isolation"
```

纪律：测试通过后才能提交；采集失败必须不写 index，避免污染时间索引。

### 3. PerfRecordRunner（替换为真实 perf，错误分类）

做什么：实现 `PerfRecordRunner`，通过 `subprocess` 构造命令：

```bash
perf record -F <frequency> -g -o <output_path> -- sleep <duration>
```

为什么：真实采样能力集中封装在 runner 层，业务逻辑仍然依赖 `PerfRunner` 抽象。测试用 fake executor 验证命令构造和错误分类，不依赖真实 `perf`。

关键命令：

```bash
pytest tests/test_real_runner.py -v
git add .
git commit -m "feat(runner): implement PerfRecordRunner with error classification"
```

纪律：测试通过后才能提交；`perf` 不存在、权限不足、超时要分别抛出明确错误。

### 4. FlameGraphRenderer（三步链路，中间文件保留）

做什么：实现火焰图渲染三步流水线：

```bash
perf script -i <perf_data> > <script_output>
stackcollapse-perf.pl <script_output> > <folded_output>
flamegraph.pl <folded_output> > <output_svg>
```

为什么：`.script` 和 `.folded` 中间文件保留在同目录，便于线上排查时判断失败发生在 `perf script`、折叠栈，还是最终 SVG 生成。

关键命令：

```bash
pytest tests/test_flamegraph.py -v
git add .
git commit -m "feat(flamegraph): implement 3-step rendering pipeline"
```

纪律：测试通过后才能提交；任一步失败都要抛出包含步骤名的错误。

### 5. CLI 整合（click + SIGTERM 优雅退出）

做什么：用 `click` 暴露 `collect-once`、`start`、`render`、`status`、`cleanup` 五个命令，并在 `pyproject.toml` 暴露 `continuous-profiler` entry point。

为什么：把底层模块组合成团队可执行工具；`start` 支持 SIGTERM 优雅退出，适合后续交给 systemd 或其他进程管理工具托管。

关键命令：

```bash
pytest tests/test_cli.py -v
git add .
git commit -m "feat(cli): integrate all commands with click"
```

纪律：测试通过后才能提交；CLI 测试用 `click.testing.CliRunner` 验证入参和调用，不直接触发真实 `perf`。

## 关键脚本/命令

单次采集：

```bash
continuous-profiler collect-once --duration 60 --frequency 99 --output-dir .profiler-data
```

持续运行：

```bash
continuous-profiler start --duration 60 --frequency 99 --retention-hours 24
```

按时间点生成火焰图：

```bash
continuous-profiler render --at "2026-04-27T13:00:00Z" --out flame.svg
```

状态查看：

```bash
continuous-profiler status
```

手动清理：

```bash
continuous-profiler cleanup --retention-hours 24
```

测试：

```bash
pytest tests/ -v
```

## 关键设计决策

- Runner 抽象隔离系统依赖，核心逻辑可单元测试，真实 `perf` 只在 `PerfRecordRunner` 内部出现。
- JSONL 格式做时间索引，轻量、追加写、可人工检查，坏行跳过后容易做崩溃恢复。
- 采集失败不写 index，避免按时间点查询时命中不存在或损坏的采样文件。
- 错误分类抛出，`perf` 不存在、权限不足、超时分别处理，便于 CLI 或运维脚本给出清晰提示。
- 中间文件 `.script` 和 `.folded` 保留，便于定位 FlameGraph 链路失败点。

## 局限

- 需要 Linux `perf` 和 FlameGraph 工具链（`stackcollapse-perf.pl`、`flamegraph.pl`）预装。
- 需要适当权限，例如调整 `perf_event_paranoid` 配置或用 `sudo` 运行。
- 当前是单机方案，不包含分布式归档、集中查询或跨机器聚合。
- 默认示例使用 99Hz 采样，极高频或极短时 CPU 事件可能采样不全。

## 生产化扩展点

- systemd 托管：自动重启、日志统一、开机自启。
- 多维度保留策略：按时间、磁盘占用、文件数综合清理。
- 进程级采样：增加 `--pid` 参数，支持针对某个服务进程采样。
- 健康检查指标：最近采集时间、失败次数、磁盘占用、最近一次错误。
- 远程归档：将 `perf.data`、`.script`、`.folded`、`.svg` 上传到对象存储。
- AI 热点分析：自动提取火焰图热点函数，生成排查建议和候选代码路径。

## 复用方式

- 直接克隆项目骨架，替换 `PerfRunner` 实现以适配其他采样工具，例如 eBPF。
- `IndexStore` 可独立复用到任何“按时间点回溯文件”的轻量索引场景。
- `FlameGraphRenderer` 可独立复用到已有 `perf.data` 的离线火焰图生成流程。
- 工作流中的“测试通过 -> git commit”纪律可迁移到任何 AI 辅助开发场景，确保每个阶段都有可回滚的稳定版本。
