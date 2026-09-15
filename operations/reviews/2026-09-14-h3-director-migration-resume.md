# H3 Director 续作复核：候选未准入

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-migration-resume
- Timestamp (UTC): 2026-09-14T11:31:59Z
- Owner: project owner
- Route: review-only
- Source of truth: operations/planning/2026-09-14-h3-director-migration.md

## Decision

项目 fresh 只读 reviewer：**`return_to_planning`**。Ponytail：**最小性通过，产品代码准入不通过**。父 session 接受 findings，保留未提交候选及环境，不继续部署、模型下载或推理引擎修补。保留候选不等于验收或建议运行。

## Findings / Disposition

- **P1：buqi 现成组合不兼容。** `sp_forward.py:30–40` 导入当前原生 ComfyUI 不存在的 `time_shift_slope`；`head_sharded_qkv` 切分 INT8 权重却没有切逐行 scale。原函数隔离探针两卡、四卡均失败，真实 FL2VA header 对应逐行 scale；当前 buqi HEAD 未更新。停止当前组合，不断言所有历史版本或其他插件都失败，不以改名、消除导入错误或自行修改数学替代验收。
- **P1：准备→启动脱节，新增代码不可准入。** `scripts/start.py` 改用项目 `.venv`，`scripts/prepare_runtime.py` 仍准备 `runtime/venv`；旧锁另有历史漂移。新测试仅验证子进程隔离，没有证明可复建或隔离后的真实 RH 采样可用。此 finding 尚未修复。父 session 不恢复 dsbi 混包来掩盖问题，也不在多卡路线已阻塞时继续扩大安装/真机变更；将明确需要统一准备/启动、验证真实依赖集合和旧路线回归的事项交回 orchestration。**现有候选不得作为已可用版本交付。**
- **P1：核心产品证据缺失。** 单卡→两卡→四卡同条件视频、收益、单服务四卡同任务、T2V/I2V音画、Director浏览器及启停均未验证。停止符合计划，但不能批准产品完成。第五卡未接入。
- **P2：torchcodec 导入仍失败。** 报告缺 FFmpeg 共享库，不能据 pip check 判定完整 ABI 正确。后续先确认实际工作流是否需要该扩展；未授权安装系统组件。

## Verified Progress / Limits

Reviewer 已读取候选、源文件及原始证据，认可：项目 `.venv` 隔离迁移；未见 dsbi 第三方注入；Torch/CUDA集合未替换；阿里源补缺；迁移后及补包后4/2/4卡通信断言通过；原生 Qwen INT8 文本编码两次 finite。Qwen只有内存键前缀归一化，无持久化转换；析构 ignored TypeError 已保留。上述证据均不等于视频生成成功或提速。

父 session 另行核对：

- `python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py`：exit 0。
- `python3 -m unittest -v`：exit 0，18 tests，15.293 s，OK；日志 `var/h3-director-resume-20260914/parent-unittest.txt`。
- `git diff --check` 通过，无暂存、提交或 push；只保留待处理候选。
- 审查候选 SHA256：`1b718cc9df2efa5ce2e7e3cfbda4bdf46f29c7db8248cdc8e358c0726b67a72f`；审后仅新增本文，不覆写候选快照。
- 最终 GPU compute-app 列表为空，旧 Studio/worker 和 ComfyUI 默认端口无监听。没有新产品服务入口；不声称整机无其他服务。

## Artifact References

- Workflow：`9463bb09-7259-4cff-99cf-ed186ebc8176`。
- 恢复 builder：`6969f4a3-45c8-4c63-bc3e-3e578699eb43`。
- Fresh reviewer：`2d178406-2cb2-4d3a-aed0-a3bdfab69f46`。
- Runtime 绑定输出：`h3-director-resume/builder.md`、`h3-director-resume/reviewer.md`；准确宿主位置以该 workflow receipt 输出引用为准。
- 原始证据与候选：ignored `var/h3-director-resume-20260914/`。
- [续作记录](../work_logs/2026-09-14-h3-director-migration-resume.md)；[历史首轮复核](2026-09-14-h3-director-migration.md)。

两 child 执行完成，不等于任务验收通过。原失败记录、主会话诊断与批准修订保留各自历史归属。
