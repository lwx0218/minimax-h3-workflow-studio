# Work Log：R1 H3 本地真实 T2VA 可行性

- Date：2026-08-21
- Round：R1
- Route：`plan`
- Status：`blocked`（single-card valid；4-GPU route decision required）
- Scope：仅验证本地 MiniMax-H3 FL2VA variant 的真实 T2VA；未开发 backend/frontend
- Matrix：`operations/planning/r1-h3-feasibility-matrix.md`
- Full report：`operations/reviews/2026-08-21-r1-feasibility-report.md`
- Attempt manifest：`operations/reviews/r1-attempt-manifest.json`

## Definition of Ready

依赖安装前完成：

- HEAD `aa2c2b13e776107cbb57ccfc519ec3859a34e9cb`，包含 baseline `aa2c2b1`
- 初始工作树 clean；`.env.local`、env 和 `var/` runtime paths ignored
- 外部 snapshot root、repository-level `model_index.json`、`FL2VA/`、`Ref2VA/` valid；未复制权重
- 5 × RTX A5000，24564 MiB/card，driver `580.173.02`，初始无 GPU process
- Host RAM 251 GiB，hard safety line 235 GiB used
- 初始约 1.1 TiB free；R1 disk delta budget 100 GiB
- 安装前已列出 A1/A2/B1/B2/C1/C2 和验证方式

## Implement / Experiment

- `scripts/run_r1_h3_attempt.py`
  - load/generation 3600 s timeout
  - 1 秒 GPU/host/process RSS sampling
  - fixed prompt/request、health/models/OpenAPI/video/content/ffprobe/decode gates
  - first review 后新增 230 GiB abort threshold（低于 235 GiB hard line）
  - exact server PATH ffprobe/ffmpeg preflight
  - mandatory server output boundary under `var/outputs/r1-feasibility/`
  - failed terminal payload/status/elapsed 持久化
- 两组且仅两组 lock：
  - lock 1：SGLang 0.5.17 + Torch 2.11.0+cu130
  - lock 2：official unmodified SGLang `44806dc507835746b67abebad041726c422030ea` + Torch 2.13.0+cu130
- 模型 alias 是 ignored symlink；未复制模型
- project-local static ffprobe/ffmpeg 7.0.2；未安装系统包

## Attempt Summary

| Execution | Configuration | Result |
|---|---|---|
| A1 | 4 GPU、TP4、U1、lossless、memory、resident4、lock1 | root routing fallback + NCCL plugin segfault；no request |
| A2 | A1 NCCL/routing correction | NCCL fixed；routing still unsupported；no request |
| B1 | 2 GPU、TP2、U1、lossless、auto encoder、resident0、lock1 | native load；host used 236.91 GiB，actual safety-line breach then abort |
| B2 | B1 + official `encoder_parallel=fold`、lock2 | fold accepted；NCCL 2.29.7 init stalled；3600 s service-load timeout；no request |
| C1 | 1 GPU、BF16、offload、lock1 | health passed；request accepted；GPU OOM；terminal failed |
| C2 lock1 preflight | C + kitchen_int8 on lock1 | invalid quant method before health；not a profile slot/generation |
| C2 | 1 GPU、official kitchen_int8/FA、lock2 | 49-step denoise + mux 1851.55 s；server lacked ffprobe PATH；terminal failed/media cleaned |
| C3 Owner exception | C2 exact model/probe + corrected PATH/output、hardened runner | terminal completed；retained 1344×768 MP4；video/audio ffprobe + decode pass |

Original slots：A 2/2、B 2/2、C 2/2；Owner exception C3 1/1。Actual generation submissions：3（C1/C2/C3）。Prompt SHA-256：`98f36b879692095e099ae824c18d9e93e7006a490e082fd474a5f531769dcf06`。

## Portability Deviation And Fix

C1/C2 server default wrote/declared output under project-root `outputs/` rather than fixed `var/outputs/r1-feasibility/`。失败媒体被清理且路径 ignored，无 Git 泄漏，但 execution 不符合 canonical `var/` boundary。

First-review fix 已加入 runner，B2 command 显式使用 `--output-path ./var/outputs/r1-feasibility/B2/server` 并通过 boundary preflight。任何后续 Owner-authorized run 不能回退到 root `outputs/`。

## Automated Verify

Command：`python3 scripts/verify_r1.py --runtime-evidence`

Verifier 现在：

- discover all runtime metadata directories and reject unknown/missing IDs
- consume `r1-attempt-manifest.json`
- validate profile slots、lock IDs、command tokens、visible GPUs、submissions、timeouts、prompt hash、status/errors
- validate B1 breach disposition and B2 early-abort configuration
- validate output deviations/fix、C2 terminal ffprobe failure、C3 authorization/success/media gates、disk/ignore/candidate policy

Current artifact：`operations/reviews/2026-08-21-r1-verification.md`。

## Independent Review / Fix

First spawned review：`operations/reviews/2026-08-21-r1-independent-review-1.md`，Decision `changes_required`，P1×4。

Disposition：

- P1-1 B1 crossed 235 GiB：acknowledged；runner fixed with 230 GiB abort margin
- P1-2 untested B2 fold：B2 executed；timed out at NCCL init
- P1-3 output outside `var/`：deviation disclosed；runner/B2 fixed
- P1-4 verifier too weak：manifest/discovery/full matrix checks added
- P2 server ffprobe preflight、failed metadata、candidate deny list：implemented

Regression verify 已通过。Final spawned review：`operations/reviews/2026-08-21-r1-independent-review-final.md`，P0=0、P1=0、P2=2、Decision `blocked`。

## Historical Stop Decision

原 bounded matrix Decision：`blocked`。C2 是真实本地权重执行，但 terminal `failed` 且缺少 content/checksum/ffprobe stream gates；原 A/B/C profile slots 与 dependency locks 已耗尽。Blocked safety gate 已通过，未创建 acceptance commit；HEAD 保持 `aa2c2b13e776107cbb57ccfc519ec3859a34e9cb`。

## Owner Reopen And Current Plan

Owner 已明确选择原 option 1，并追加 4-GPU rate/quality requirement：

1. 先执行一次 corrected single-card C3 exception
2. C3 valid 后执行合法 4-GPU topology，不使用非法 5-way sharding
3. 评估 4 个 external repositories 并更新 development plan

矩阵 change control：`operations/planning/r1-h3-feasibility-matrix.md`。External assessment：`operations/planning/r1-external-reference-assessment.md`。

Generation 前 hardening 已实现：

- manifest duplicate execution ID 显式拒绝
- command requirement 改为 exact argv sequence，不再 substring match
- verifier 从 `request.json` prompt 内容重新计算 SHA-256
- resource monitor 在 sampling/nvidia-smi failure 时 kill process 并 fail closed
- verifier 拒绝 `monitor_error` / `resource_monitor_failed`
- `scripts/test_r1_hardening.py` 覆盖 argv exactness 和 monitor synthetic failure

Preflight review final：`operations/reviews/2026-08-21-r1-c3-preflight-review-final.md`，P0=0、P1=0、P2=0、Decision `safe_to_execute`。

## C3 Result

C3 于 07:09:47Z–07:44:54Z 执行成功：

- lock 2、1×A5000、official `kitchen_int8`、requested FA；head-size 72 incompatible component fallback 后实际为 `torch_sdpa, fa` mix；固定 768p/5s/50-step probe
- load 265.110 s；generation polling 1841.575 s；API inference 1836.096 s
- terminal `completed`；content HTTP 200；1097858-byte MP4
- SHA-256 `bc7e0ad866d69fac5edc595fe7cb744007f278bff4816ddb18fc417739a26d27`
- H.264 1344×768/24fps/124 frames + AAC LC stereo 32kHz；full decode exit 0
- no black segment / no ≥0.5s silence；contact-sheet sampled frames coherent
- peak GPU 23881 MiB；host used 181.88 GiB；process RSS 173.78 GiB；72°C
- monitor/safety/tool/output/Git boundaries pass；cleanup 后无 GPU process

Feasibility decision 更新为 `feasible_with_constraints`。C3 result review：`operations/reviews/2026-08-21-r1-c3-result-review.md`，P0=0、P1=0、P2=3、Decision `valid_probe`。P2 已 disposition：补充 reproducible media command artifact、post-stop GPU snapshot，并澄清 component-level attention fallback。

## Four-GPU Preflight

Lock-2 Torch/NCCL bounded smoke：

- default NCCL 2.29.7：2-rank communicator initialized，但 first all-reduce 120 s timeout
- `NCCL_CUMEM_ENABLE=0` correction：仍在 first all-reduce timeout
- `NCCL_P2P_DISABLE=1`：2-rank all-reduce sum=3 和 4-rank sum=10 均在约 1.5 s 内完成
- 结论：当前 A5000/lock-2 的 NCCL P2P transport 不可用；4-GPU 必须显式走 P2P-disabled fallback，可能降低 scale efficiency

G4 initial launch contract `G4-TP4Q`：4×A5000、TP4×U1、encoder fold、official kitchen_int8、相同 fixed probe、230/235 GiB controls。Final preflight review：`operations/reviews/2026-08-21-r1-g4-preflight-review-final.md`，P0=0、P1=0、P2=0、Decision `safe_to_execute`。

G4 initial result：NCCL P2P-disabled init passed；4 ranks loaded TP-sharded text encoder，then duplicated full transformer CPU staging rapidly drove host used to 235.87 GiB。230 GiB abort triggered but 1-second observation lag allowed an actual 0.87 GiB hard-line breach。No health/request/generation；GPU peak only 459 MiB/card。Initial post-stop snapshot caught four transient workers；session-wide cleanup hardening and delayed snapshot confirm all GPUs back to 1 MiB with no process。

Proposed same-topology correction `G4-TP4Q-adaln` was rejected before launch。Independent review `operations/reviews/2026-08-21-r1-g4-adaln-preflight-review.md` found installed `MiniMaxH3DiTModel` explicitly rejects AdaLN weight-file rebuild with non-null runtime quantization；CLI requires unquantized weights。Manifest state is `preflight_rejected`；no known-invalid generation was run and no further correction is auto-created。

Comparison metric：first-output rate = media duration / submit-to-terminal elapsed；service load 单独报告；G4/C3 speedup = C3 generation elapsed / G4 generation elapsed。该结果仅称 cold single-probe comparison，不称 warm throughput、稳定性或 sustained scaling。

R1 当前为 `blocked`。Single-card feasibility remains `feasible_with_constraints`；4-GPU requirement needs Owner to choose unquantized AdaLN-online SGLang、new ComfyUI/DiffSynth backend/weights、defer to R7，or add host RAM。Owner-gate final review：`operations/reviews/2026-08-21-r1-owner-gate-review.md`，P0=0、P1=0、P2=3、Decision `blocked_owner_decision`；P2 documentation wording 已修复。Owner decision 前不进入 R2。

## Current Closeout Gate

- Automated regression：pass（9 runtime records；3 generation submissions；known-invalid correction has no runtime）
- Final Independent Review：P0=0、P1=0、P2=3，`blocked_owner_decision`
- Single-card local feasibility：`feasible_with_constraints`
- 4-GPU acceptance：blocked；no valid 4-GPU output/rate/quality media
- Ledger：`blocked`，not accepted candidate
- Acceptance commit：not created；HEAD remains `aa2c2b13e776107cbb57ccfc519ec3859a34e9cb`
- Post-commit verify：not applicable until Owner selects a supported route
