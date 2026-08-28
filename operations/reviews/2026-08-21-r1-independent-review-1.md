# R1 Independent Review Report

- Round：R1
- Review mode=spawned_pi_process
- Review type：独立、只读
- Decision：`changes_required`

## Files reviewed

### Required contract and evidence

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
- `operations/reviews/2026-08-21-r1-verification.md`
- `operations/reviews/r1-verification-output.txt`
- `operations/reviews/r1-dependency-lock-1.txt`
- `operations/reviews/r1-dependency-lock-2.txt`
- `operations/work_logs/2026-08-21-r1-h3-feasibility.md`
- `scripts/run_r1_h3_attempt.py`
- `scripts/verify_r1.py`

### Runtime and boundary evidence

- `.gitignore`
- `.env.example`
- `var/README.md`
- `var/logs/r1-feasibility/dor.txt`
- A1/A2/B1/C1/C2/C2-lock1-preflight metadata and server logs
- C1/C2 `request.json`、`submit-response.json`、`status.ndjson`
- C1/C2 model capability responses
- Exact lock-2 SGLang checkout relevant to `encoder_parallel=fold`

## Evidence checked

### Scope

- 变更限于 R1 feasibility 文档、runner、verifier 和依赖快照。
- 未发现 backend/frontend、Workflow contract、UI 或后续 round 实现。
- 未执行 ComfyUI、在线 API、GGUF 模型、LoRA、Ref2VA 或不同模型分支。
- Lock 中出现 `gguf` Python distribution 属于 SGLang 依赖快照，不构成 GGUF inference branch。

### Dependency/profile/attempt accounting

- Dependency locks：2/2。
- 已触达 Profile A、B、C。
- 已知 profile slots：A 2/2、B 1/2、C 2/2，共 5/6。
- 实际 T2VA submissions：C1、C2，共 2。
- C2 lock-1 qualification 未提交 generation，可合理作为 dependency preflight 单列。
- **再次修正 PATH 后重跑 C2 会是 Profile C 第三次 generation attempt，明确超过 C 的 2 次上限。未经 Owner 例外授权不得执行。**
- B2 仍未执行；其 disposition 存在 P1，见 Findings。

### Execution/resource consistency

| Execution | Evidence result | Resource consistency |
|---|---|---|
| A1 | native routing/NCCL startup failure；无提交 | 295 MiB/GPU、14.31 GiB host、7.61 GiB RSS，与 metadata 一致 |
| A2 | NCCL 修正有效；routing 仍失败；无提交 | 3605 MiB/GPU、14.50 GiB host、7.57 GiB RSS，一致 |
| B1 | H3 routing 成功，加载期间 host-memory abort | 6863 MiB/GPU、236.91 GiB host、228.29 GiB RSS，一致，但越过 235 GiB safety line |
| C1 | health/capability 通过；提交后 CUDA OOM；terminal `failed` | load 325.235 s、23893 MiB GPU、185.11 GiB host，一致 |
| C2 lock-1 | `kitchen_int8` 在 lock 1 被拒绝；无提交 | 9053 MiB GPU、95.29 GiB host，一致 |
| C2 lock-2 | 49-step denoise、decode/mux 完成，API 最终 `failed` | load 255.151 s、generation log 1851.55 s、23881 MiB GPU、181.71 GiB host，一致 |

- 所有已知 load/generation 时长均未超过 60 分钟。
- Disk delta 约 15.14 GiB，低于 100 GiB。
- 未发现 Xid 或残留 GPU process 的相反证据。

### C2 success gate

C2 **不是 valid probe**：

- `status.ndjson` 最终状态为 `failed`。
- API error：`ffprobe is required to validate final MiniMax H3 output`。
- content endpoint 未返回并保留非空 MP4。
- 无 checksum。
- 无独立 ffprobe video/audio stream evidence。
- 无独立 decode 或人工媒体抽检。

SGLang 的 `Pixel data generated successfully in 1851.55 seconds`、mux 日志和 stereo input 提示均不能替代 API `completed/succeeded` 与独立 ffprobe gate。

### Portability/Git

- 已提交合同、报告和脚本未发现 secret 或宿主机绝对路径。
- `.env.local`、`var/`、虚拟环境、根目录 `outputs/`、常见权重和媒体路径均有 ignore 规则。
- 未发现权重、secret 或 retained runtime media 已进入 candidate Git 内容的证据。
- 但实际 server output 不在 `var/`，且 verifier 的候选文件策略不完整，见 Findings。

## Findings

### P0

None.

### P1

#### P1-1 — B1 越过了 235 GiB 主存安全线

**Evidence**

- Matrix：接近 235 GiB 且持续增长时应中止。
- `B1/metadata.json`：
  - `peak_host_used_bytes=254379134976`，即 236.91 GiB。
  - `memory_safety_exceeded=true`。
- `ResourceMonitor` 每秒采样，只有在 `used >= limit_bytes` 后才发送 SIGTERM，没有提前余量或增长趋势保护。

**Impact**

B1 的结果可以证明该配置不安全，但不能表述为完全符合主存预算。当前 runner 允许高速分配越过 safety line 后才中止。

**Required change**

- 报告明确记录 B1 为 safety-line breach，而不只是普通 “safety abort”。
- 在任何 B2/授权 rerun 前增加安全余量或趋势中止，使 kill threshold 明显低于 235 GiB。

#### P1-2 — B2 存在未 disposition 的矩阵内明确 correction，当前 `blocked` 结论过早

**Evidence**

- Profile B 仅使用 1/2 slot。
- B1 根因是两个 worker 各自 staging 完整 text encoder/transformer，导致 host-memory duplication。
- 已锁定的 lock-2 SGLang source 明确支持：
  - `encoder_parallel: auto | fold | dp | replicate`
  - `fold shards the weights at load time`
  - 显式 `fold` 可用于 pure-TP multi-rank replica。
- Profile B 允许 2 GPU、TP2、Ulysses1、lossless；`encoder_parallel=fold` 不引入量化、不同 backend 或不同模型。
- Lock 2 已属于现有 2/2 dependency budget，不需要第三组 lock。

**Impact**

报告中“没有符合矩阵且能明确消除 duplication 的 B2 correction”缺乏依据。至少存在一个针对已知根因、仍位于矩阵内的官方配置 correction。因而尚不能认定所有矩阵内路径均已合理终止，也不应先把后续全部转成 Owner 例外选择。

**Required change**

二选一：

1. 在修复安全与 output/preflight 问题后，使用现有 lock 2 执行 B2：
   - Profile B、TP2、Ulysses1、非量化；
   - `--encoder-parallel fold`；
   - 同一固定 probe；
2. 提供可复核证据证明 lock-2 H3 对该 fold 配置不支持或仍必然越过 safety line。

在此 disposition 完成前，R1 应保持 `in_progress`/`changes_required`，而不是 final `blocked`。

#### P1-3 — C1/C2 server media 实际写入根目录 `outputs/`，违反固定 output 和项目内 `var/` 边界

**Evidence**

- Matrix 固定 output：`var/outputs/r1-feasibility/`。
- C1/C2 submit/status evidence 的 `file_path` 指向项目根目录 `outputs/<job>.mp4`。
- C2 server args：`output_path: "outputs/"`。
- C2 server log：`Output saved to outputs/<job>.mp4`。

**Impact**

媒体最终被失败清理，且 `/outputs/` 被 Git ignore，因此未形成 Git 泄漏；但实际 execution 仍违反 MVP 所有 runtime data 位于 `var/` 的 portability contract。

**Required change**

- 报告明确披露本次 output-path deviation。
- Runner 在启动前验证 server command 的 output path 位于 `var/outputs/r1-feasibility/`。
- B2 或任何 Owner 授权 rerun 必须显式设置合规 output path。

#### P1-4 — Verifier 无法证明其声称的矩阵与安全结论

**Evidence**

`scripts/verify_r1.py`：

- 使用硬编码的六个目录名，不发现或拒绝额外 attempt 目录。
- 不验证 A/B/C command 的 GPU count、TP、Ulysses、offload、resident layers、quantization 或 backend。
- 不验证每 profile slot 数量和 lock-to-attempt 映射。
- 不验证 load/generation timeout 配置及实际时长。
- 不验证 server output 位于 `var/`。
- 对 B1 只要求 `memory_safety_exceeded=true`，没有因 236.91 GiB 越线而失败。

因此当前 `RESULT PASS` 只能证明预先选定字段符合预期，不能机械证明实验未出现隐藏 execution、配置越界或 safety breach。

**Required change**

- 使用完整 attempt manifest 或发现所有 evidence directories。
- 验证 profile、lock、command、submission、timeout、memory、output path 和 attempt counts。
- 未知/重复 attempt ID 必须失败。
- 修复后重新运行自动验证；无需因此自动新增 generation。

### P2

#### P2-1 — 已知 server-side ffprobe prerequisite 未在 C2 提交前检查

**Evidence**

- DoR 明确记录 `ffprobe=not_on_PATH`。
- Runner 接收 `--ffprobe`，但仅在 content 下载后用于独立检查；未加入 server `PATH`，也未做 server-side prerequisite preflight。
- C2 因这一已知环境条件在 mux 后失败。

**Disposition**

任何后续 attempt 前，应对启动 server 的精确环境执行 ffmpeg/ffprobe prerequisite check。此项不能被用于把当前 C2 改判成功。

#### P2-2 — Failed metadata 未直接保存 terminal API payload 和 generation elapsed

**Evidence**

Runner 在遇到 `failed` 时立即抛异常，因此 C1/C2 metadata 缺少 `terminal_status`、terminal error payload 和 `generation_elapsed_seconds`；这些事实只能从 `status.ndjson` 与 server log 拼接。

**Disposition**

在抛出失败前将 terminal payload、状态和 elapsed 写入 metadata，提高 durable evidence 的自包含性。

#### P2-3 — Git candidate policy 未覆盖全部常见权重和媒体类型

**Evidence**

`FORBIDDEN_CANDIDATE_RE` 覆盖 MP4 和部分权重扩展，但未覆盖常见模型 `.bin` 以及 MOV/WebM/WAV 等 runtime media；无法解码的 binary candidate 会被直接跳过内容检查。

**Disposition**

扩展 candidate policy，并对未知大 binary 使用 deny/allowlist 策略。当前未发现实际权重或媒体已入库。

## Required changes summary

1. 将 B1 标记为实际越过 safety line，并修复 runner 的提前中止策略。
2. 执行或正式排除 lock-2 `encoder_parallel=fold` 的 B2。
3. 强制 server output 位于 `var/outputs/r1-feasibility/`。
4. 加强 verifier，使其真正验证完整矩阵、attempt 数、资源和路径。
5. 增加 server-side ffprobe preflight，并完善失败 metadata。
6. 完成自动复验和新的 independent review。
7. 不得未经 Owner 授权执行 corrected C2；该执行将是 Profile C 第三次 attempt。

## Decision

`changes_required`

当前 C2 的无效判定是诚实的，且 corrected C2 rerun 确实需要 Owner 对第三次 Profile C attempt 授权；但 B2 尚有矩阵内 correction 未合理 disposition，同时存在主存安全线、runtime output path 和 verifier 可信度 P1。因此当前 R1 还不能以 final `blocked` control-gate conclusion 收线。
