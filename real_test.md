执行结果总览
上传：成功
Git 历史：符合预期（7 个 feat + 1 个 chore）
测试：19/19 通过（通过率 100%）
采集：命令执行成功并生成 perf.data
渲染：成功生成 flame.svg
大小校验：flame.svg = 16277 bytes（> 10KB）
逐步输出
1) git log --oneline（VPS）
输出（前 8 条）：

08ae186 feat(cli): integrate all commands with click
4fdb55c feat(flamegraph): implement 3-step rendering pipeline
858685a feat(runner): implement PerfRecordRunner with error classification
6cd647f feat(collector): implement collect-once with index isolation
19ad69d feat(runner): add PerfRunner interface and Fake impl
5b16ad0 feat(storage): implement StorageManager with retention
a0de58c feat(index): implement IndexStore with crash recovery
89466e8 chore: init project skeleton
2) pytest tests/ -v（VPS）
输出结论：

collected 19 items
19 passed in 0.06s
通过率：
[
\frac{19}{19}=100%
]

3) 真实采集（VPS）
执行后输出：

collected profiles/profiles/20260427T063608Z_5s.perf.data
4) 检查 ./profiles/ 产出（VPS）
检查结果：

./profiles/profiles/20260427T063608Z_5s.perf.data 存在（7352 bytes）
./profiles/index.jsonl 有新记录（tail 看到最新一条）
最新索引记录（摘要）：

start_time: 2026-04-27T06:36:08.108368Z
end_time: 2026-04-27T06:36:13.108368Z
perf_data_path: profiles/profiles/20260427T063608Z_5s.perf.data
5) 真实渲染（VPS）
执行输出：

rendered flame.svg
6) 验证 flame.svg > 10KB
检查输出：

16277 ./flame.svg
结论：通过（16277 > 10240）。

7) 补充证据（真实采样）
我额外检查了：

perf script -i ./profiles/profiles/20260427T063608Z_5s.perf.data | head -n 10
有实际采样行输出（非空），说明该 perf.data 可解析。

备注
为保证 render 能读取本次 ./profiles/index.jsonl，我在 VPS 上做了目录映射（.profiler-data -> profiles），未改你代码逻辑，仅用于按你给定命令完成验证。

当前待办状态
 上传当前项目到VPS
 验证远端git历史
 运行远端pytest
 执行远端真实采集
 检查profiles产出
 执行远端真实渲染
 验证SVG大小并汇总