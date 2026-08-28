> **Historical-only notice (2026-08-21):** This report preserves the execution-time R1 `blocked` control gate and its evidence. That historical gate is superseded by the ComfyUI-first Baseline Reset; current status is recorded in [`operations/planning/rebaseline-plan-v1.md`](../planning/rebaseline-plan-v1.md). Do not use the old Owner-option/R2 sequencing as a current instruction.\n\n# R1 MiniMax-H3 本地 T2VA 可行性报告

- Date：2026-08-21
- Round：R1
- Round Status：`blocked`（single-card valid；4-GPU route needs Owner decision）
- Feasibility Decision：`feasible_with_constraints`
- Prior bounded decision：`blocked`（superseded by Owner-authorized C3 evidence）
- Probe：本地 MiniMax-H3 `fl2va` / `t2va` / 768 short edge / 16:9 / 5 seconds / seed 0
- Model：外部已有 snapshot，通过 `.env.local` 引用；未复制或提交权重
- Prompt source：snapshot 内官方 `scripts/readme/reproducible-768p-t2va-request.sh`
- Prompt SHA-256：`98f36b879692095e099ae824c18d9e93e7006a490e082fd474a5f531769dcf06`
- Attempt manifest：`operations/reviews/r1-attempt-manifest.json`

## Executive Decision

原 bounded matrix 不能判为 `feasible` 或 `feasible_with_constraints`，并形成过 `blocked` decision。Owner 随后明确授权 corrected C3。C3 使用相同 official `kitchen_int8`、固定 768p/5s/50-step probe 成功通过 service、API、content、checksum、ffprobe video/audio 和 full decode gates，因此本地 T2VA 可行性现在为 `feasible_with_constraints`。4-GPU follow-up 随后因 host staging 与 quantized AdaLN incompatibility 阻塞，当前 R1 为 `blocked` Owner control gate。

- A1/A2：4-GPU profile 在两个 slots 内均未形成 native ready service。
- B1：2-GPU native loading 因 per-worker CPU staging 将 host used 推到 236.91 GiB，实际越过 235 GiB safety line 后中止。
- B2：按第一次 Independent Review 要求，使用第二组 lock 和官方 `encoder_parallel=fold` correction；在 NCCL 2.29.7 distributed initialization 停滞，命中 3600 秒 service-load timeout，未开始 model loading/request。
- C1：1-GPU BF16 service ready，但 generation CUDA OOM。
- C2：1-GPU official `kitchen_int8` 完成 denoise 与 mux，但 server-side final validation 因 `ffprobe` 不在其 `PATH` 而把 job 标为 `failed`；失败媒体被清理，content/checksum/independent ffprobe gates 缺失。

A/B/C 各两个 profile slots 和两组 SGLang/Torch locks 已用完，仍没有 valid probe，满足 matrix 的 bounded `blocked` stop decision。不得自动新增 R1D、第三个 C attempt 或其他 backend 分支。

## Definition of Ready Evidence

原始 DoR 位于 ignored `var/logs/r1-feasibility/dor.txt`：

- HEAD `aa2c2b13e776107cbb57ccfc519ec3859a34e9cb`，包含 baseline `aa2c2b1`；初始工作树 clean
- `.env.local`、env、cache、log、tmp、output 均命中 ignore
- 外部 snapshot 的 repository-level `model_index.json` 有效，`FL2VA/`、`Ref2VA/` 存在；snapshot 约 465 GiB
- 5 × RTX A5000，24564 MiB/card，driver `580.173.02`，初始 24112 MiB free/card；PCIe、无 NVLink
- Host RAM 251 GiB；hard safety line 235 GiB used
- 初始约 1.1 TiB disk free；R1 project baseline `942080` bytes
- 系统 CUDA toolkit 只读检查为 12.0；未修改 driver、toolkit 或 kernel

## Dependency Locks

只使用两组 SGLang/Torch lock：

1. `operations/reviews/r1-dependency-lock-1.txt`
   - SGLang `0.5.17`
   - Torch `2.11.0+cu130`
   - SGLang kernel `0.4.5`
   - C fallback 前加入官方 optional `comfy-kitchen==0.2.31`，未改变 SGLang/Torch
2. `operations/reviews/r1-dependency-lock-2.txt`
   - 官方未修改 SGLang source commit `44806dc507835746b67abebad041726c422030ea`
   - SGLang metadata `0.0.0.dev1+g44806dc50`
   - Torch `2.13.0+cu130`
   - SGLang kernel `0.4.6.post1`
   - `comfy-kitchen==0.2.31`
   - 官方支持的 `SGLANG_BUILD_RUST_EXTS=none` build option；未 patch 源码

两组环境均位于 ignored project paths。Torch CUDA smoke 检出 5 张 A5000。Lock 1 的 NCCL 2-GPU all-reduce 在 `NCCL_NET=Socket`、`NCCL_IB_DISABLE=1` 下通过；未修改系统 NCCL/CUDA。

## Attempt Results

公共设置：cache/tmp 全部导向项目 `var/`；模型 alias `./var/cache/MiniMax-H3` 是指向 `.env.local` snapshot 的 ignored symlink；load/generation timeout 各 3600 秒；所有 generation 使用固定 probe。

### A1 — Profile A slot 1 / lock 1

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 .venv-h3/bin/sglang serve \
  --model-path "$H3_MODEL_PATH" --model-variant fl2va \
  --num-gpus 4 --tp-size 4 --ulysses-degree 1 \
  --encoder-parallel auto --performance-mode memory \
  --layerwise-offload-components dit,text_encoder \
  --dit-offload-prefetch-size 1 --dit-layerwise-resident-layers 4 \
  --enable-torch-compile false --warmup-mode off \
  --host 127.0.0.1 --port 30010
```

- 03:02:14Z–03:02:49Z；no generation
- Local snapshot basename `master` caused root modular index fallback；NCCL network plugin initialization segfault
- Peak：295 MiB/GPU；host used 14.31 GiB；process RSS 7.61 GiB；32°C
- A2 仅修 routing/NCCL configuration

### A2 — Profile A slot 2 / lock 1

```bash
NCCL_NET=Socket NCCL_IB_DISABLE=1 CUDA_VISIBLE_DEVICES=0,1,2,3 \
.venv-h3/bin/sglang serve \
  --model-path "$H3_MODEL_PATH" --model-id MiniMax-H3 \
  --model-variant fl2va --num-gpus 4 --tp-size 4 --ulysses-degree 1 \
  --encoder-parallel auto --performance-mode memory \
  --layerwise-offload-components dit,text_encoder \
  --dit-offload-prefetch-size 1 --dit-layerwise-resident-layers 4 \
  --enable-torch-compile false --warmup-mode off \
  --host 127.0.0.1 --port 30010
```

- 03:04:16Z–03:04:56Z；no generation
- NCCL correction worked；`--model-id` 仍未覆盖 local modular index；unsupported Diffusers pipeline exit
- Peak：3605 MiB/GPU；host used 14.50 GiB；process RSS 7.57 GiB；33°C

### B1 — Profile B slot 1 / lock 1

```bash
NCCL_NET=Socket NCCL_IB_DISABLE=1 CUDA_VISIBLE_DEVICES=0,1 \
.venv-h3/bin/sglang serve \
  --model-path "$H3_MODEL_ALIAS" --model-variant fl2va \
  --num-gpus 2 --tp-size 2 --ulysses-degree 1 \
  --encoder-parallel auto --performance-mode memory \
  --layerwise-offload-components dit,text_encoder \
  --dit-offload-prefetch-size 1 --dit-layerwise-resident-layers 0 \
  --enable-torch-compile false --warmup-mode off \
  --host 127.0.0.1 --port 30010
```

- 03:06:41Z–03:09:51Z；no generation
- Native routing succeeded；workers each staged full 53.1 GiB text encoder and began transformer staging
- Peak：6863 MiB/GPU；host used **236.91 GiB**；process RSS 228.29 GiB；37°C
- **Safety disposition：实际越过 235 GiB line 约 1.91 GiB 后 monitor 才观察并 kill，不表述为预算内。** 原 runner 1 秒采样且在 hard line 才 kill，是 first review P1。
- Fix：runner 现在要求 abort threshold < hard line；B2 使用 230 GiB abort threshold

### B2 — Profile B slot 2 / lock 2，official fold correction

```bash
NCCL_NET=Socket NCCL_IB_DISABLE=1 CUDA_VISIBLE_DEVICES=0,1 \
./var/cache/r1-feasibility/venv-lock2/bin/sglang serve \
  --model-path "$H3_MODEL_ALIAS" --model-variant fl2va \
  --num-gpus 2 --tp-size 2 --ulysses-degree 1 \
  --encoder-parallel fold --performance-mode memory \
  --layerwise-offload-components dit,text_encoder \
  --dit-offload-prefetch-size 1 --dit-layerwise-resident-layers 0 \
  --enable-torch-compile false --warmup-mode off \
  --output-path ./var/outputs/r1-feasibility/B2/server \
  --host 127.0.0.1 --port 30010
```

- 04:15:36Z–05:15:37Z；no generation
- Runner exact server environment preflighted project-local `ffprobe`/`ffmpeg` 7.0.2；output path passed `var/outputs/r1-feasibility/` boundary check
- SGLang accepted `encoder_parallel=fold` and logged replica folding proposal
- Stopped at configured 3600-second service load limit；wall evidence includes约 1 second polling/shutdown bookkeeping
- Last progress：NCCL 2.29.7 distributed initialization；no model loading or health
- Peak：417 MiB/GPU；host used 12.07 GiB；process RSS 4.02 GiB；61°C
- 230 GiB abort not triggered；235 GiB line not crossed
- Decision：B2 official correction has been executed and failed within its bounded slot

### C1 — Profile C slot 1 / lock 1 / BF16

```bash
CUDA_VISIBLE_DEVICES=0 .venv-h3/bin/sglang serve \
  --model-path "$H3_MODEL_ALIAS" --model-variant fl2va --num-gpus 1 \
  --performance-mode memory --layerwise-offload-components dit,text_encoder \
  --dit-offload-prefetch-size 1 --dit-layerwise-resident-layers 0 \
  --enable-torch-compile false --warmup-mode off \
  --host 127.0.0.1 --port 30010
```

- 03:10:12Z–03:16:08Z；service load 325.235 s；health/models/video capability passed
- Request accepted；first denoise forward CUDA OOM；terminal `failed`
- Peak：23893 MiB GPU；host used 185.11 GiB；process RSS 176.17 GiB；43°C
- C1 status declared default server file path under project-root `outputs/`，违反 fixed `var/` output boundary；无成功媒体，路径偏差在 runner fix 前发生

### Lock-1 C2 dependency qualification — not a profile slot/generation

- Lock 1 service load rejected `kitchen_int8`：`Invalid quantization method: kitchen_int8`
- No health/request；触发第二组且最后一组 dependency lock

### C2 — Profile C slot 2 / lock 2 / official kitchen_int8

```bash
CUDA_VISIBLE_DEVICES=0 ./var/cache/r1-feasibility/venv-lock2/bin/sglang serve \
  --model-path "$H3_MODEL_ALIAS" --model-variant fl2va --num-gpus 1 \
  --quantization kitchen_int8 --attention-backend fa \
  --performance-mode memory --layerwise-offload-components dit,text_encoder \
  --dit-offload-prefetch-size 1 --dit-layerwise-resident-layers 0 \
  --enable-torch-compile false --warmup-mode off \
  --host 127.0.0.1 --port 30010
```

- 03:25:38Z–04:00:46Z；service load 255.151 s；health/models/video capability passed
- 49/49 denoise：1800.7365 s；decode/mux：41.4224 s
- Server logged `Pixel data generated successfully in 1851.55 seconds`（30m 51.55s）and 22940 MB peak
- API terminal：`failed`，error `ffprobe is required to validate final MiniMax H3 output`
- Failed job cleaned media；content endpoint/checksum unavailable
- Resource monitor peak：23881 MiB GPU；host used 181.71 GiB；process RSS 173.47 GiB；72°C
- C2 server default output was project-root `outputs/`，违反 fixed `var/` path；该 first-review P1 已由 runner preflight + mandatory `--output-path` 修复并在 B2 验证
- Corrected C2 rerun would be Profile C slot 3；Owner 随后明确授权，记录为 C3 exception

### C3 Owner Exception — Profile C slot 3 / lock 2 / corrected kitchen_int8

C3 exact server configuration 与 C2 的模型、量化 request、offload、probe 完全一致，仅修正 media-tool PATH 和 output boundary。`--attention-backend fa` 是请求配置；server 对 head-size 72 不兼容组件明确 fallback，实际为 `torch_sdpa, fa` component-level mix，不宣称全组件 FlashAttention。Generation 前完成 fail-closed hardening 与 spawned preflight review；artifact：`operations/reviews/2026-08-21-r1-c3-preflight-review-final.md`，P0=0、P1=0、P2=0、Decision `safe_to_execute`。

- 07:09:47Z–07:44:54Z；service load 265.110 s；generation polling 1841.575 s
- API terminal：`completed`；inference time 1836.095968 s
- Content HTTP 200；retained MP4 1097858 bytes
- SHA-256：`bc7e0ad866d69fac5edc595fe7cb744007f278bff4816ddb18fc417739a26d27`
- Independent ffprobe：H.264 1344×768，24 fps，124 frames，5.166667 s；AAC LC stereo 32 kHz，5.175 s
- Full video+audio decode：exit 0
- Audio：RMS -23.31 dBFS，peak -5.80 dBFS；no ≥0.5 s silence at -50 dB threshold
- Video：no ≥0.25 s black segment；1 fps contact-sheet visual check 显示 coherent spaceship/character sequence，无 black/corrupt frame；未在本轮做主观调参
- Peak：23881 MiB GPU；host used 181.88 GiB；process RSS 173.78 GiB；72°C
- 230 GiB early abort 未触发；235 GiB hard line 未越过；resource monitor 无 error
- Exact project-local ffmpeg/ffprobe 7.0.2 preflight passed；server/content 都位于 `var/outputs/r1-feasibility/C3-owner-exception/`
- Post-stop snapshot：5 GPUs 均 1 MiB used，无 residual compute process
- Reproducible independent media artifact 记录 input checksum、exact commands、tool versions 和 exit codes

C3 result review：`operations/reviews/2026-08-21-r1-c3-result-review.md`，P0=0、P1=0、P2=3、Decision `valid_probe`。P2 已 disposition：补充 post-stop GPU snapshot、`independent-media-verification.json`，并澄清 requested FA 的 component fallback。

Decision：valid quantized local T2VA probe；满足 matrix `feasible_with_constraints`，约束为 single-card online INT8、接近 24 GiB GPU peak、约 30.6 min inference。

### G4-TP4Q — 4-GPU follow-up slot 1 / load failure

- 4×A5000、TP4×U1、encoder fold、official kitchen_int8、native SGLang、fixed probe
- Lock-2 NCCL default/CUMEM-off first all-reduce timeout；`NCCL_P2P_DISABLE=1` 后 2-rank/4-rank smoke passed；该 fallback 可能损失 scaling efficiency
- 08:27:45Z–08:29:15Z；NCCL init/model routing passed；no health/request/generation
- 每 rank TP-sharded text encoder load 后，transformer full-checkpoint CPU staging 在 4 workers 内重复
- 230 GiB early abort triggered；1-second observation/termination lag 后 peak host used **235.87 GiB**，实际越过 235 GiB hard line 0.87 GiB
- Process RSS 227.78 GiB；GPU 459 MiB/card；34°C max
- Initial immediate snapshot observed four terminating workers；session-wide cleanup fix added；retained delayed snapshot shows no compute process and 1 MiB/GPU

Disposition：不提交 generation、不宣称 4-GPU rate/quality。提议的同-topology correction `G4-TP4Q-adaln` 在 generation 前被 Independent Review 拒绝：installed source 明确禁止 `kitchen_int8` 与 `--minimax-h3-adaln-online true` 组合，并要求 unquantized weights。Artifact：`operations/reviews/2026-08-21-r1-g4-adaln-preflight-review.md`，P0=0、P1=1、Decision `changes_required`。该 P1 通过标记 contract `preflight_rejected`、禁止启动并停止自动扩展来 disposition；没有执行已知无效配置。

## Budget Accounting

- Dependency locks：2 / 2
- Profiles：A、B、C = 3 / 3
- Original profile slots：A 2/2，B 2/2，C 2/2
- Owner exception：C3 1/1，明确保留为 slot 3，不重写原矩阵
- Dependency-only qualification：1（no health/request，不占 profile slot）
- Actual generation submissions：3（C1、C2、C3）；G4-TP4Q failed during load and submitted none
- 4-GPU follow-up：G4-TP4Q load failure；quantized AdaLN staging correction `preflight_rejected`、未执行
- Load/generation configured upper bounds：3600 s；B2 hit load timeout；其他 recorded load/generation 均低于 bound
- Disk：最终 project delta 由 verifier 复算，约 15.14 GiB，低于 100 GiB
- 未执行 ComfyUI、在线 API、GGUF inference、LoRA、Ref2VA、different model 或 R1D

## Resource Summary

| Execution | GPU peak | Host used peak | Process RSS peak | Result |
|---|---:|---:|---:|---|
| A1 | 295 MiB/card | 14.31 GiB | 7.61 GiB | routing/NCCL startup fail |
| A2 | 3605 MiB/card | 14.50 GiB | 7.57 GiB | routing startup fail |
| B1 | 6863 MiB/card | **236.91 GiB** | 228.29 GiB | safety-line breach + abort |
| B2 | 417 MiB/card | 12.07 GiB | 4.02 GiB | 3600 s load timeout at NCCL init |
| C1 | 23893 MiB | 185.11 GiB | 176.17 GiB | generation OOM |
| C2 lock-1 qualification | 9053 MiB | 95.29 GiB | 86.13 GiB | quant method unavailable |
| C2 lock-2 | 23881 MiB | 181.71 GiB | 173.47 GiB | mux then API post-validation fail |
| C3 lock-2 | 23881 MiB | 181.88 GiB | 173.78 GiB | valid completed MP4 + video/audio gates |
| G4-TP4Q | 459 MiB/card | **235.87 GiB** | 227.78 GiB | transformer staging safety breach；no request |

- GPU Xid：server logs 中未发现
- Cleanup：C3 immediate cleanup clean；G4 immediate snapshot 观察到 4 个 terminating workers，session-wide cleanup 后 retained delayed snapshot 为无 compute process、1 MiB/GPU
- 未修改 NVIDIA driver、系统 CUDA toolkit/kernel；未 patch SGLang；未下载第二份权重

## ffprobe / Media Result

| Attempt | Job status | Content | ffprobe video | ffprobe audio | Decode |
|---|---|---|---|---|---|
| A1/A2/B1/B2 | no job | no | not available | not available | not run |
| C1 | failed/OOM | no | not available | not available | not run |
| C2 | failed/post-validation | no retained media | **not verified** | **not verified** | not independently verified |
| C3 | completed | 1097858-byte MP4 | H.264 1344×768/24fps | AAC LC stereo/32kHz | pass |

C2 mux log中的 stereo input 和“generated successfully”不能替代 API gates；C3 是第一个同时获得 completed status、content、checksum、独立 ffprobe 双流与 decode pass 的 valid probe。

## First Review Fixes

Review artifact：`operations/reviews/2026-08-21-r1-independent-review-1.md`。

- P1-1：报告明确 B1 breach；runner 新增 230 GiB early abort、235 GiB hard line 分离
- P1-2：执行 lock-2 `encoder_parallel=fold` B2；结果为 bounded load timeout
- P1-3：披露 C1/C2 root output deviation；runner 强制 output 在 R1 `var/` root；B2 已验证
- P1-4：新增 complete attempt manifest；verifier discover/reject unknown executions，并验证 profile/lock/command/submission/timeout/memory/output/count
- P2-1：runner exact server `PATH` preflight ffprobe/ffmpeg
- P2-2：runner 在 failed terminal 抛错前保存 terminal payload/status/elapsed
- P2-3：verifier 扩大 weight/media candidate deny list，并拒绝未知 binary candidate

Final review：`operations/reviews/2026-08-21-r1-independent-review-final.md`，Review mode `spawned_pi_process`，P0=0、P1=0、P2=2、Decision `blocked`。两个 P2 不推翻当前 evidence；若 Owner 授权新 attempt，必须先修复 verifier 精确 argv/prompt hash checks 与 resource monitor fail-closed。

## Current Control Gate And Owner Options

Single-card feasibility 已从历史 `blocked` 更新为 `feasible_with_constraints`；但 Owner 新增的 4-GPU rate/quality requirement 当前技术路线 blocked：

- lock-2 NCCL 必须关闭 P2P 才能 collective
- TP4 + kitchen_int8 在 transformer full-checkpoint staging 时越过 host hard line
- AdaLN-online 可以减少 staging，但 installed source 明确要求 unquantized weights，不能与 kitchen_int8 组合
- 5-way 不满足 H3 topology divisibility

Owner options：

1. **建议：授权一次 4-GPU unquantized TP4 + AdaLN-online bounded test**
   - 仍使用当前官方 snapshot、lock 2、native SGLang、相同 768p/50-step probe
   - 去掉 `kitchen_int8`，保留 TP4 和 layerwise offload；AdaLN 从当前 safetensors 按 TP shard 重建
   - 质量路线最保守且无需新权重/backend，但显存、速度和最终 host peak 仍需实测
2. **切换到 ComfyUI_RH / DiffSynth fallback**
   - 使用 converted INT8/NF4 component weights 和低内存 runtime
   - 更适合多张卡做 independent replicas 提升 throughput，而不是证明一个请求的 4-way latency
   - 需要新 dependency lock、额外量化权重、backend change 和 supply-chain/license review
3. **接受 single-card SGLang 为 MVP baseline，4-GPU optimization 延后到 R7**
   - 现在进入 R2–R6；R7 再做 worker pool/replica scheduler 与 quality tiers
   - 这是对当前“R1 必须完成 4-GPU”的 scope adjustment
4. **增加 host RAM 后重跑当前 TP4 kitchen_int8**
   - 当前 251 GiB 不足；community/official comparable offload recipes 使用约 377/384 GiB-class host

Owner-gate final review：`operations/reviews/2026-08-21-r1-owner-gate-review.md`，P0=0、P1=0、P2=3、Decision `blocked_owner_decision`。P2 stale chronology/pending/cleanup wording 已在本报告修正。

Owner 决策前 R1 保持 `blocked`，不进入 R2，不创建 acceptance commit。
