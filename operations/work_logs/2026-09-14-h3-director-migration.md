# H3 Director 迁移：通信硬阻塞，停止切换

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-migration
- Timestamp (UTC): 2026-09-14T10:34:32Z
- Owner: project owner
- Route: direct-execute
- Source of truth: operations/planning/2026-09-14-h3-director-migration.md

## Goal / Summary

**未交付 Director 多卡迁移。** 在模型加载前的两卡 NCCL 初始化探针中，两进程均段错误；父 session 允许的一次禁 P2P 诊断也同样失败。遵守任务包停止条件，保留旧路线，交 fresh reviewer 复核，建议 `return_to_planning`。这不证明硬件永久不支持多卡，也不证明故障根因已定位。

## Scope / Changes

- 新增一页 [ADR](../../docs/adr/0002-director-single-service-multigpu.md)，记录单服务与四卡验收门槛，不改变默认运行形态。
- 本轮仅新增 ADR 与本文；现有业务代码、配置、工作流、README、治理文件均未修改。未安装依赖、下载或转换模型，未改系统或 conda 环境。
- `.venv-h3` 实际 Python 3.12.9、Torch 2.11.0+cu130、NCCL 2.28.9、comfy-kitchen 0.2.31；与旧 runtime-lock 声明的 Torch 2.14.0 不同，未擅自升级或切换栈。加载的 Torch/NCCL/CUDA runtime 库来自该项目环境；没有 LD_LIBRARY_PATH、LD_PRELOAD、PYTHONPATH 覆盖。不能仅据此判定 ABI 正确。
- 因硬阻塞，`.venv-h3` → `.venv` 及启动引用修复未执行，旧入口保留；两种环境名已被现有 `.gitignore` 覆盖。
- 静态参考版本：ComfyUI `169fcf35a2fc163fec31338b816503ddac0d3fcf`；Director `52f8fb7b8d8eb6bebf33ebb534827efa8f95484c`；buqi `bce083929c135bdabd41679da3ddf6f409336ed3`。后两者只读缓存，未部署。
- buqi `minimax_sp/sp_group.py:129` 与 `sp_worker.py:33` 使用 NCCL `init_process_group`，与失败探针同一关键初始化路径；子进程继承环境，可传禁 P2P 参数，但此次实测该参数不能消除失败。其原始初始化超时为 40 分钟，因此没有直接启动插件等候。
- 静态风险仍在：每卡完整 DiT，INT8 ConvRot 的 QKV 分片兼容及 Qwen 真实推理未验证；现有 Qwen 文件确实存在，不能报告成缺失。未因停止而改用 RH 权重假冒原生布局。

## Validation

### 有界探针

探针在 ignored `var/h3-director-validation-20260914/communication_probe.py`，每 rank 只看一张卡，以本机回环 TCP 建 NCCL 组，原定进行 3 轮 all-reduce/all-gather 并断言值。初始化自身 25 秒超时，父监控 75 秒，外层 100 秒并额外 10 秒 kill 宽限。父进程最终 terminate/kill 必要子进程并 wait；本次四个 rank 均自行以信号 11 退出并已回收。无 ComfyUI 服务、权重加载或采样。

```bash
timeout -k 10s 100s .venv-h3/bin/python var/h3-director-validation-20260914/communication_probe.py --world 2
PYTHONFAULTHANDLER=1 timeout -k 10s 100s .venv-h3/bin/python var/h3-director-validation-20260914/communication_probe.py --world 2 --p2p-disable
```

两命令均 exit 1；每个命令内两 rank returncode 均为 -11。第一次失败后立即暂停，经父 session 明确允许仅一次诊断才执行第二条；第二次后停止全部迁移操作。faulthandler 栈停于 `torch/distributed/distributed_c10d.py:2253` 的 `_new_process_group_helper`，尚未打印 initialized，未进入 collective。

| 验证 | 结果 | 墙钟 | 主机已用 RAM 采样最大值 | GPU 0–4 显存采样最大值（MiB） |
|---|---|---:|---:|---|
| CUDA peer capability | 全部非对角 True；不是通信成功证明 | 未计时 | 未测 | 未测 |
| 两卡默认 P2P | NCCL 初始化双 rank SIGSEGV | 4.559 s | 12.586 GiB | 295 / 295 / 1 / 1 / 1 |
| 两卡禁 P2P，仅一次获准诊断 | 同样 SIGSEGV | 5.063 s | 12.723 GiB | 295 / 295 / 1 / 1 / 1 |
| 单卡生成基线与重复 | 未测，前置通信硬阻塞 | — | — | — |
| 两卡/四卡同任务生成及加速比 | 未测，不声称收益 | — | — | — |
| T2V、I2V/首尾帧音画；Qwen/VAE真实推理 | 未测 | — | — | — |
| Director 浏览器与服务启停 | 未部署，未测；没有新增访问入口 | — | — | — |
| 第五卡编码/解码 | 未接入 | — | — | — |

RAM 为整机 `MemTotal - MemAvailable`，不是进程 RSS；每次只有 4 个约一秒间隔样本，显存也是整卡采样值，可能漏过瞬时峰值。无生成端到端/阶段耗时、视频媒体或性能比较。两卡前置通信探针不替代计划要求的单卡→两卡→四卡生成顺序。

### 回归与清理

- `python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py`：exit 0。
- `python3 -m unittest -v`：exit 0，17 tests，15.260 s，OK；这是旧 Studio 回归，不覆盖新多卡路线。
- `git diff --check`：exit 0；`git diff --cached --name-only` 为空；未暂存、提交或 push。
- `ps` 确认四个探针 PID 均不存在；`nvidia-smi` 无 compute apps，各卡恢复 1 MiB；`ss` 确认旧 Studio/worker 端口及 ComfyUI 默认端口无监听。没有启动五 worker；本轮未新增外网监听服务，清理快照仍包含其他既有监听，不在本轮处理。

### 本机证据

全部大日志及机器信息仅在 ignored `var/h3-director-validation-20260914/`：

- `communication_probe.py`：可重跑探针（目前预期失败；再次实测需先解决阻塞）。
- `communication-2-p2p-True/`：默认 P2P 的 rank 日志与 result.json。
- `communication-2-p2p-False/`：禁 P2P 的 rank 日志、faulthandler 栈与 result.json。目录布尔值表示 P2P 是否启用，以 JSON 中 `p2p_disable` 为准。
- `stack.txt`：实际版本、库来源与内存映射。
- `py-compile.txt`、`unittest.txt`、`cleanup.txt`：回归与清理证据。
- `candidate.diff`、`review-summary.json`：仅本轮候选内容与独立 review 摘要；排除既有治理与机器配置。

## Decision / Next Steps

停止迁移，旧方案保持原样而非改回五套服务。需要新的有界运行时通信修复任务才能恢复验证；不在本轮换 Torch、改驱动或研发替代通信引擎。fresh reviewer 已给出 `return_to_planning`；文档候选通过 ponytail 最小性准入，产品迁移未通过完成准入。P2 清理措辞已按意见收窄；详见 [review 及处置](../reviews/2026-09-14-h3-director-migration.md)。

Ponytail 自查：硬阻塞前只写必要 ADR 与本机探针；未建设无法验收的启动平台、调度框架或工作流胶水，未添加产品代码，因此无新增 tracked 单元测试。探针自身含数值断言，但通信初始化失败使其尚未执行。
