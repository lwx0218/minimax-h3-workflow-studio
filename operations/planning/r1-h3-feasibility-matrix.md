> **SUPERSEDED future-plan notice:** This file is retained as historical R1 execution evidence. Its bounded experiment instructions and blocked decision gate are not the current product route. Future runtime work follows [`rebaseline-plan-v1.md`](rebaseline-plan-v1.md). Do not rerun R1 from this document.

# R1 H3 Local Feasibility Matrix

## Purpose

为 5×RTX A5000 上的 MiniMax-H3 本地 T2VA 建立硬边界，防止 R1 通过无限版本、拓扑、offload 和量化组合发生隐性膨胀。

本文件是 R1 的 Definition of Ready 组成部分。R1 不得绕过本矩阵自行增加实验分支。

## Fixed Probe

所有 generation attempt 使用同一个 probe：

- model variant：`fl2va`
- task：`t2va`
- short edge：768
- aspect ratio：16:9
- duration：5 seconds
- seed：0
- prompt：使用 MiniMax-H3 官方可复现 T2VA 示例中的固定结构化 prompt，保存其来源和内容 hash
- output：项目 `var/outputs/r1-feasibility/`

除非 API 对帧数有强制对齐要求，不得通过降低分辨率、取消音频或缩短到模型支持范围以下来伪造成功。

## Environment Budget

- 最多尝试 2 组 SGLang/Torch 依赖锁定组合
- 不修改系统 NVIDIA driver、CUDA toolkit 或 kernel；如必须修改，R1 标记 blocked 并请求 Owner 授权
- 不 patch SGLang 源码来规避失败
- 不下载另一份完整 H3 权重
- `.venv-h3`、cache、log 和 output 必须位于项目目录并被 Git 忽略
- R1 新增磁盘使用上限：100 GiB，不含已有外部模型

## Deployment Profiles

最多执行 3 个 profile，每个 profile 最多 2 次 generation attempt：第一次按预设执行，第二次只允许修正明确的配置/API 错误。总 generation attempt 上限为 6。

### Profile A：4-GPU Lossless Memory Mode

允许范围：

- GPU count：4
- TP：4 或安装版本对 H3 明确支持的等价 4-way weight sharding
- Ulysses：1
- precision/quantization：原始 BF16/FP32，不量化
- performance mode：memory
- layerwise offload：只允许 `dit`、`text_encoder`、`vae` 的官方支持组合
- prefetch：1
- resident layers：0–4
- torch compile：disabled

### Profile B：2-GPU Lossless Memory Mode

允许范围：

- GPU count：2
- TP：2
- Ulysses：1
- precision/quantization：原始 BF16/FP32，不量化
- 其余范围与 Profile A 相同

### Profile C：1-GPU 24G Bounded Fallback

允许范围：

- GPU count：1
- performance mode：memory
- layerwise offload：`dit,text_encoder`，只有明确内存需要时才加入 `vae`
- prefetch：1
- resident layers：0
- torch compile：disabled
- 第一次 attempt：不量化
- 第二次 attempt：仅允许官方文档支持的 `kitchen_int8`

不得在 R1 增加 ComfyUI backend、在线 API、GGUF、LoRA、不同模型或 Ref2VA profile。这些只能在 R1 blocked decision 后由 Owner 重新选择。

## Per-Attempt Safety Limits

- 服务启动/模型加载上限：60 分钟
- 单个 5 秒 probe generation 上限：60 分钟
- 主机内存安全线：235 GiB；接近安全线且持续增长时中止
- GPU 温度、Xid、OOM 或进程崩溃必须记录
- 不并发执行多个 generation
- 每次失败必须先记录根因，再决定是否使用该 profile 的第二次 attempt

## Success Validation

一个 attempt 只有同时满足以下条件才算成功：

1. H3 服务正常启动并通过 health/capability 探测
2. T2VA 请求被接受并最终进入 completed/succeeded
3. content endpoint 返回非空 MP4
4. `ffprobe` 检出视频流和音频流
5. 视频时长在模型对 5 秒请求的合理对齐范围内
6. 视频可解码，音频不是缺失流
7. 记录启动参数、依赖锁、GPU/主存峰值、加载耗时、生成耗时和输出 checksum

画面和声音质量需保存人工抽检结论，但 R1 不进行主观质量调参。

## Stop Decisions

### `feasible`

- 至少一个非量化 profile 完成有效 probe
- 服务加载和单次生成均未超过 60 分钟
- 未越过主存安全线
- 无持续性 GPU/进程错误

### `feasible_with_constraints`

满足有效 probe，但至少存在一项：

- 只有 `kitchen_int8` 成功
- 需要独占 4 张 GPU 或显著 CPU offload
- 5 秒生成耗时超过 30 分钟但不超过 60 分钟
- 需要记录的质量、稳定性或资源限制

进入 R2 前必须把约束写入 architecture 和 work log。

### `blocked`

满足任一条件：

- 2 组依赖锁均无法形成可启动环境
- 3 个 profile、最多 6 次 generation attempt 后仍无有效 probe
- 所有路径都超过时间或内存安全线
- 需要未授权的系统级修改、额外完整权重或源码 patch
- 反复出现 GPU Xid、不可恢复崩溃或无法生成音频流

Blocked 后停止 R1，由 Owner 在 SGLang 调整、ComfyUI backend、在线 API或 Goal 变更之间做选择；不得自动新增 R1D。

## Required Evidence

每个 attempt 记录：

- profile/attempt ID
- exact command（去除 secret）
- package lock/version
- visible GPUs
- start/end timestamps
- peak GPU/CPU memory
- status/error
- output path、size、checksum、ffprobe summary
- decision

R1 review 必须核对 attempt 总数和 Stop Decision，确认没有超出矩阵。

## Owner-Authorized Change Control：2026-08-21

原矩阵已 bounded `blocked` 后，Owner 明确授权重新打开 R1：

1. **一次 corrected single-card C3 exception**
   - 与 C2 使用相同 lock 2、official `kitchen_int8`、FlashAttention、固定 768p/5s/50-step probe
   - 唯一 operational corrections：project-local ffmpeg/ffprobe 进入 exact server `PATH`；server output 固定在 `var/outputs/r1-feasibility/`
   - generation 前必须修复 final review 两个 P2 hardening findings 并通过自动验证
   - 这是明确记录的第三个 Profile C slot，不回写成原矩阵内 attempt
2. **C3 valid 后执行 bounded 4-GPU performance/quality follow-up**
   - 只使用现有 5 张 A5000 中的 4 张；H3 的 56 heads/64 partitions 不允许 5-way topology
   - 先做 lock-2 NCCL/topology smoke，再允许 model load/generation
   - baseline topology 从合法的 `TP4 × Ulysses1` 开始；是否增加 `TP2 × Ulysses2` 取决于 host-memory 预算和第一组证据
   - 保持同模型、prompt、seed、768p、5s 与非近似 50-step baseline，先比较 output rate/resource/quality；不得通过降分辨率、Turbo LoRA 或 cache 伪造 4-GPU improvement
   - 每个 topology 最多一个 configuration correction；任何 host used 达 230 GiB early-abort threshold 时立即停止
   - first-output rate 固定定义为 `media duration seconds / submit-to-terminal wall seconds`；同时单独报告 service load。G4/C3 speedup 使用相同 probe 的 generation elapsed ratio，只能标记为 cold single-probe comparison，不得宣称 warm throughput、稳定性或 sustained scaling

External references 的评估位于 `operations/planning/r1-external-reference-assessment.md`。它们提供 fallback/优化设计，不自动授权第三组 dependency lock、新权重或 ComfyUI/DiffSynth backend execution。
