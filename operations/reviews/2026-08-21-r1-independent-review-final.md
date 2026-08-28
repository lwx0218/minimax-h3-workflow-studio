# R1 Independent Review Report

- Round：R1
- Review mode=spawned_pi_process
- Review type：独立、只读
- Findings：P0=0，P1=0，P2=2
- Decision：`blocked`

## Files reviewed

### Required files

- `AGENTS.md`
- `Harness_manual.md`
- `README.md`
- `docs/project-intake/minimax-h3-workflow.md`
- `docs/specs/mvp-v0.md`
- `docs/architecture/architecture-v0.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/planning/r1-h3-feasibility-matrix.md`
- `operations/reviews/review-checklist.md`
- `operations/reviews/2026-08-21-r1-feasibility-report.md`
- `operations/reviews/2026-08-21-r1-independent-review-1.md`
- `operations/reviews/2026-08-21-r1-verification.md`
- `operations/reviews/r1-verification-output.txt`
- `operations/reviews/r1-dependency-lock-1.txt`
- `operations/reviews/r1-dependency-lock-2.txt`
- `operations/reviews/r1-attempt-manifest.json`
- `operations/work_logs/2026-08-21-r1-h3-feasibility.md`
- `scripts/run_r1_h3_attempt.py`
- `scripts/verify_r1.py`

### Runtime and boundary evidence

- A1/A2/B1/B2/C1/C2/C2-lock1-preflight metadata、requests、status、server logs 和 resource traces
- `var/logs/r1-feasibility/dor.txt`
- `.gitignore`
- `.env.example`
- `var/README.md`

## Evidence checked

### Scope and forbidden branches

- 变更限于 R1 feasibility、runner、verifier、报告和依赖证据。
- 未开发 backend、frontend、Workflow/DAG contract 或后续 round 功能。
- 未执行 ComfyUI backend、在线 API、GGUF inference、LoRA、Ref2VA 或不同模型。
- Lock 中的 `gguf` distribution 只是 SGLang 依赖，不构成 GGUF inference branch。

### Matrix and budget accounting

- Dependency locks：2/2。
- Profiles：A、B、C，共 3/3。
- Profile slots：A 2/2、B 2/2、C 2/2。
- Runtime execution records：7，其中 6 个 profile slots，另有 1 个无 health/request 的 dependency qualification。
- API generation submissions：A=0、B=0、C=2，总计 2/6。
- C2 lock-1 qualification 未提交 generation；单列为 dependency preflight 是可接受的。
- Disk delta：`16258101248` bytes，约 15.14 GiB，低于 100 GiB。
- Load/generation 均配置 3600 秒上限。B2 wall timestamp 为约 3601 秒，报告已披露为轮询和终止 bookkeeping；没有形成未限界运行。
- B1 实际达到 236.91 GiB，越过 235 GiB safety line，不能表述为预算内；报告已明确标记 breach。B2 使用 230 GiB abort threshold，峰值 12.07 GiB，未再次越线。

### Execution consistency

| Execution | Configuration/result | Resource evidence |
|---|---|---|
| A1 | 4 GPU、TP4、U1、lock1；routing fallback + NCCL segfault；无请求 | 295 MiB/GPU；14.31 GiB host |
| A2 | A1 routing/NCCL correction；unsupported pipeline；无请求 | 3605 MiB/GPU；14.50 GiB host |
| B1 | 2 GPU、TP2、lossless；CPU staging duplication；safety breach 后中止 | 6863 MiB/GPU；236.91 GiB host |
| B2 | lock2、`encoder_parallel=fold`；fold 被接受；NCCL 2.29.7 init 停滞并超时 | 417 MiB/GPU；12.07 GiB host |
| C1 | 1 GPU BF16；health/capability 通过；generation CUDA OOM | 23893 MiB；185.11 GiB host |
| C2 lock1 | `kitchen_int8` 不受 lock1 支持；无 health/request | 9053 MiB；95.29 GiB host |
| C2 lock2 | 1 GPU `kitchen_int8`；denoise/mux 完成；API terminal `failed` | 23881 MiB；181.71 GiB host |

### C2 success gate

C2 不能算 valid probe：

- `status.ndjson` 最终为 `failed`，从未进入 `completed/succeeded`。
- API error 为 `ffprobe is required to validate final MiniMax H3 output`。
- 失败媒体已清理；无 content endpoint 成功响应。
- 无 retained MP4、checksum、独立 ffprobe video/audio stream 或独立 decode evidence。
- SGLang 的 `Pixel data generated successfully in 1851.55 seconds`、stereo input 和 mux 日志不能替代上述 gates。

Corrected C2 rerun 将在 C1、C2 两次 C-profile generation submissions 之后成为第三次 Profile C generation attempt；未经 Owner 明确授权不得执行。

### B2 disposition

第一次 review 指出的矩阵内 `encoder_parallel=fold` correction 已实际执行，而非隐藏或跳过：

- 使用现有第二组 lock；
- 保持 Profile B、TP2、U1、非量化；
- fold proposal 被 SGLang 接受；
- 最终在 NCCL distributed initialization 命中 service-load timeout；
- 未发生 generation submission。

因此不存在尚未 disposition 的 B-profile 矩阵内 retry。

### Portability and Git boundary

- C1/C2 历史 execution 的 server output 指向根目录 `outputs/`，确属 portability deviation；报告已披露。
- 当前 runner 强制 `--output-path` 位于 `var/outputs/r1-feasibility/`，并由 B2 preflight 验证。
- `.env.local`、`var/`、虚拟环境、根目录 runtime outputs、数据库、权重和媒体路径均受 ignore/candidate policy 保护。
- 未发现 secret、权重或 retained runtime media 进入 Git candidate。
- 已提交文件未发现宿主机绝对路径；runtime evidence 中的机器路径位于 ignored 文件内。

### First review disposition

- P1-1：B1 breach 已明确披露；230/235 GiB 双阈值已实现。
- P1-2：B2 fold 已执行并 bounded failure。
- P1-3：历史 output deviation 已披露；runner/B2 已修复路径约束。
- P1-4：manifest、runtime discovery、profile/lock/command/count/resource checks 已足以支撑当前 bounded conclusion。
- P2 ffprobe preflight、failed-terminal metadata 逻辑和 candidate deny list 已加入 runner/verifier。

## Findings

### P0

None.

### P1

None.

### P2

#### P2-1 — Verifier 的 fail-closed 声明仍有机械检查缺口

**Evidence**

- `entries = {entry["id"]: entry ...}` 会静默折叠 manifest 中的重复 ID，没有显式比较原始 execution 数与唯一 ID 数。
- Command requirements 使用字符串 substring，例如 `--num-gpus 20` 也可匹配 `--num-gpus 2`。
- Verifier 比较 metadata 中的 prompt hash，但没有从 `request.json["prompt"]` 重新计算 hash。

**Impact**

当前 manifest、commands 和 request 经本次人工交叉检查没有冲突，因此不推翻 R1 结论；但“duplicate IDs fail”和完整配置机械证明的表述略强于实际实现。

**Disposition**

下次修改 verifier 时应增加唯一 ID 棛查、argv 级 option parsing，以及 request prompt hash 重算。无需为此新增 generation。

#### P2-2 — Resource monitor 异常时不是 fail-closed

**Evidence**

`scripts/run_r1_h3_attempt.py` 的 `ResourceMonitor.run()` 捕获任意异常后仅写入 `monitor_error` 并继续；主线程不会因持续采样失败而停止 attempt。`scripts/verify_r1.py` 也不拒绝 resource trace 中的 `monitor_error`。

**Impact**

现有 executions 有连续资源记录和明确 peaks，未发现与 metadata 相反的证据，因此当前结论仍可信。若未来 monitor 持续故障，主存安全保护可能失效。

**Disposition**

任何 Owner 授权的新 generation 前，应让持续 monitor failure 触发 fail-closed，并让 verifier 拒绝 `monitor_error`。

## Required changes

1. Owner 必须从报告中的 bounded options 选择下一控制路径。
2. 未获 Owner 明确 matrix exception 前，不得 corrected-rerun C2。
3. 若 Owner 授权新本地 attempt，先修复两个 P2 hardening 项并重新运行 verifier。
4. Owner 决策前不得进入 R2，也不得创建 R1 acceptance commit。

## Decision

`blocked`

当前没有 P0/P1。`blocked` 结论诚实且 bounded：两组 dependency lock、A/B/C profile slots 均已 disposition，仍无满足全部 success gates 的 valid probe。该决定不是 acceptance pass；下一步需要 Owner control-gate decision。
