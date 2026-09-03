# Operations

目标机器：1 台主机，5 × RTX A5000（24 GB），251 GiB 内存，PCIe、无 NVLink。

## 准备

```bash
cp .env.example .env.local && $EDITOR .env.local
set -a; . ./.env.local; set +a
python3 scripts/prepare_runtime.py --check-only          # 模型文件存在 + safetensors 头
python3 scripts/prepare_runtime.py --check-only --compute-sha   # 全量 SHA-256（慢）
python3 scripts/prepare_runtime.py                       # ComfyUI v0.34.2 + RH 节点 + venv + 权重软链
```

运行时放在 `H3_RUNTIME_ROOT`（默认 `var/runtime/`）。旧版本在 `var/runtimes/r3-single-worker-product/`，直接 `mv` 过来即可，不必重装。

需要的模型文件（`config/asset-manifest.json`）：
`MiniMax-H3-FL2VA-int8_convrot.safetensors`、`qwen3-vl-32b-int8_convrot.safetensors`、`MiniMax-H3-video_vae.safetensors`、`MiniMax-H3-audio_vae.safetensors`、`FL2VA/` sidecar 目录。

## 启动 / 停止

```bash
python3 scripts/start.py                                  # 全部 worker + Studio
python3 scripts/start.py --workers worker-gpu0,worker-gpu1
python3 scripts/start.py --no-workers                     # 只起 Studio
python3 scripts/start.py --comfy-arg=--use-sage-attention # 给每个 ComfyUI 传额外参数
```

Ctrl-C / SIGTERM 会依次停掉 Studio 和所有 worker。PID 在 `var/logs/*.pid`，日志在 `var/logs/comfyui-<worker-id>.log` 和 `var/logs/h3-studio.log`。

确认清理干净：

```bash
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory --format=csv,noheader,nounits
ss -ltnp '( sport = :30210 or sport = :30211 or sport = :30212 or sport = :30213 or sport = :30214 or sport = :30215 )'
```

## 并发上限与主机内存

`config/worker-pool.json`：

| 键 | 默认 | 含义 |
|---|---|---|
| `safe_concurrent_runs` | 2 | 同时执行的 Run 数上限，多出来的排队 |
| `host_ram_abort_gib` | 230 | 主机已用内存 ≥ 此值时停止派发新 Run |
| `host_ram_hard_gib` | 235 | 硬线（同上，留作报警区分） |
| `health_interval_s` | 5 | 后台健康检查间隔 |

已有测量：两卡并发峰值主机内存 96.8 GiB（空载 14.8 GiB → 每个运行中的 worker 约 41 GiB）。线性外推 5 并发约 220 GiB，贴着 230 GiB 线，所以默认停在 2。要放开：

```bash
python3 scripts/e2e.py concurrent --count 3   # 看输出里的 peak_host_used_gib
python3 scripts/e2e.py concurrent --count 4
python3 scripts/e2e.py concurrent --count 5
```

每一档都在 abort 线以下再把 `safe_concurrent_runs` 调上去。如果 5 并发不够，要么接受 3–4，要么加内存（SGLang / vLLM-Omni 对 24 GB 卡的推荐都是 384 GiB 主机内存）。另一个方向是查每个 worker 那 40 GiB 主存花在哪（RH 节点的 layerwise offload 把 DiT 放在 pinned host memory；文本编码器编码完是否释放），可能省一半。

## 验证

```bash
python3 -m unittest -v                  # 不需要 GPU
python3 scripts/e2e.py profiles         # draft/balanced/final，媒体校验（H.264 + 立体声 AAC + 864×480×124 帧 + 无黑场/静音）
python3 scripts/e2e.py fl2va
python3 scripts/e2e.py concurrent --count 2
```

`e2e.py` 需要 ffmpeg/ffprobe，默认路径 `var/cache/tools/ffprobe-static-extracted/`，可用 `--ffmpeg/--ffprobe` 覆盖。结果和下载的媒体在 `var/logs/e2e/`。

已测参考时间（单 A5000，5 s 864×480）：draft 170 s、balanced 260 s、final 295 s。

## 多卡路线

两种"多卡"要分开：

**Replica Execution（各跑各的）** — 已实现，受主机内存限制，见上节。

**Single-Request Multi-GPU（多卡加速一个任务）** — 未实现。候选路线：

1. **ComfyUI-MiniMaxH3-Parallel**（社区节点，最贴合现状）。主卡正常跑模型，其余卡只接收 attention 的 Q/K/V 头切片，权重不复制，所以不额外吃主机内存。作者在 4×RTX PRO 6000 上实测 denoise 阶段 2/3/4 卡为 1.50×/1.82×/2.02×，端到端 1.19×/1.32×/1.39×。硬约束：只支持 ComfyUI **原生** H3 节点（当前模板用的是 RH 节点，要换）；只支持 Comfy Kitchen INT8 attention（我们锁的 comfy-kitchen 0.2.31 正是它要的版本）；要求 GPU 之间双向 CUDA peer access。先跑下面的测试：

   ```bash
   nvidia-smi topo -m
   var/runtime/venv/bin/python - <<'EOF'
   import torch
   n = torch.cuda.device_count()
   print([[torch.cuda.can_device_access_peer(i, j) if i != j else "-" for j in range(n)] for i in range(n)])
   a = torch.ones(256 * 1024 * 1024, device="cuda:0"); b = a.to("cuda:1"); torch.cuda.synchronize(); print("p2p copy ok", b.sum().item())
   EOF
   ```

   R1 阶段的证据是 NCCL 默认 P2P 第一次 all-reduce 超时、关掉 P2P 才通——在 PCIe 无 NVLink 的机器上通常是主板 ACS 没关。如果上面测试失败或挂住，需要在 BIOS 关 ACS（或内核参数 `pci=noacs`，视主板）。通了以后在 A5000 PCIe 上预期比作者的 Blackwell 数据再差一些，4 卡端到端 1.3× 左右。56 个注意力头按卡均分，第 5 张卡进不来。

   部署形态：一个 ComfyUI 进程占 GPU 0–3（`CUDA_VISIBLE_DEVICES=0,1,2,3 ... --use-ck-attention`）作为 "worker-parallel"，GPU 4 保留为普通 worker。同一时刻一张卡只能属于一个进程，所以"吞吐模式"（5×单卡）和"加速模式"（1×四卡 + 1×单卡）要用不同的 `worker-pool.json` 启动。

2. **SGLang / vLLM-Omni 的 TP / Ulysses**。正统的多卡推理，但意味着放弃 ComfyUI 回到独立推理服务。R1 在这台机器上失败的两个原因都没变：每个 rank 把完整 checkpoint 载进 CPU（251 GiB 不够，官方建议 384 GiB）；NCCL P2P 不可用。且 A5000（Ampere）没有 FP8 tensor core，社区 4×L40S 的 FP8 路线收益还要打折。不建议再投入，除非先加内存。

3. **不用多卡的单卡提速**（最便宜，先做）。同样需要换到 ComfyUI 原生 H3 节点：`--use-sage-attention`（A5000 支持，官方 wiki 称中端卡最多约 2×）、Spectrum-MiniMax-H3 节点（跳过部分 transformer 评估，约 30%）、H3 Turbo / PDD 4-step 蒸馏 LoRA（速度数倍，画质和音频会降，适合 draft profile）。叠起来，balanced 的 260 s 有希望降到 100 s 以内，比多卡收益更大。

建议顺序：换原生 H3 节点并重出三个 profile 的模板 → P2P 测试 → 单卡提速项逐个实测 → 视 P2P 结果决定是否接入 Parallel 节点 → 实测 3/4/5 并发放开上限。

## 参考

- SGLang MiniMax-H3 cookbook: https://docs.sglang.ai/cookbook/diffusion/MiniMax/MiniMax-H3
- vLLM-Omni MiniMax-H3 recipe: https://github.com/vllm-project/vllm-omni/blob/main/recipes/MiniMaxAI/MiniMax-H3.md
- ComfyUI-MiniMaxH3-Parallel: https://github.com/AesSedai/ComfyUI-MiniMaxH3-Parallel
- ComfyUI 原生 H3 支持: https://comfyui-wiki.com/en/tutorial/advanced/video/minimax/minimax-h3
- ComfyUI-Spectrum-MiniMax-H3: https://github.com/xmarre/ComfyUI-Spectrum-MiniMax-H3
- ComfyUI_RH_MinMaxH3（当前模板使用的节点）: https://github.com/HM-RunningHub/ComfyUI_RH_MinMaxH3
