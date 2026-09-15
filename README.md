# MiniMax H3 Director（单卡候选，待独立复核）

一个原生 ComfyUI + 固定版本 AIMixer Director、一张可见 GPU。只用已有本地 FL2VA/Qwen/VAE/sidecar，不下载模型：FL2VA 独立副本同步重排 QKV 权重和逐行 scale，Qwen 仅归一化键名前缀，VAE 合入本地归一化参数并等价物化音频 weight_norm；原件不动。

已实测同参数 T2V 两次、I2V、首尾帧，均输出 320×320、39帧/24fps、1.625秒的非黑运动视频与立体声音轨；实际浏览器原生导入、Run提交、产物播放及单服务停止/重启已验证。属于小尺寸短片 smoke，不承诺更大尺寸/时长/参考质量或多卡收益。独立 reviewer 尚待复核。旧下载文件的72字节修复仍未授权，原 `.part` 原样保留，本轮未使用。

准备/启动候选统一项目 `.venv`，不回退旧 runtime venv、不注入外部 site-packages、不自动重装 Torch/CUDA。默认 `scripts/start.py` 只起单卡 Director、仅监听回环，默认端口 30210，不起 Studio/五 worker。依赖记录是当前隔离环境实装的传递集合，**不是干净重建成功证明**。

- [候选运行说明](docs/director-single-gpu.md)
- [本地模型单卡实测](operations/work_logs/2026-09-15-h3-director-local-model.md)；[此前停止记录](operations/work_logs/2026-09-15-h3-director-single-gpu.md)
- `workflows/comfy-ui/director-single-{t2v,i2v,fl2v}.json`：原生单段 smoke 图。

```bash
set -a; . ./.env.local; set +a  # 按运行说明填本地模型与独立副本目标
python3 scripts/prepare_runtime.py
python3 scripts/start.py       # http://127.0.0.1:30210/，Ctrl-C停止
```

`--install-deps` 已禁用：观察清单没有精确 CUDA wheel 身份，不能作为安装锁。

## 历史 Studio 路线（非本轮交付）

以下描述的是旧 RH 工作流历史能力，不能用于证明当前隔离后的原生 Director 可用。旧 Studio 代码保留，只可显式 `--legacy-studio` 选择；旧 RH 真机采样未回归。

本地、单机、单用户的历史 MiniMax-H3 音视频生成工作台。ComfyUI（固定版本）负责画布、节点、队列和执行；本项目旧 Studio 包含 Guided Mode、GPU 任务分配与画布代理。

```
浏览器 ──► Studio :30210 ──┬──► worker-gpu0  ComfyUI :30211 (GPU 0)
          Guided Mode      ├──► worker-gpu1  ComfyUI :30212 (GPU 1)
          /canvas/<id>/    ├──► …
          /api/runs        └──► worker-gpu4  ComfyUI :30215 (GPU 4)
```

一张卡一个 ComfyUI 进程；Studio 是唯一入口，worker 只监听本机回环地址。

## 历史入口

旧环境准备命令已由原生 Director 准备替代，不再用 `prepare_runtime.py` 重建旧 RH 环境。仅对已有旧运行时保留显式入口（未做当前隔离环境的真实采样回归）：

```bash
python3 scripts/start.py --legacy-studio --workers worker-gpu0
```

当前原生路线请使用上方入口和运行说明；不要同时运行旧 Studio 与单卡 Director 占用同一 GPU/端口。

打开 `http://<studio-host>:30210/`。

- Guided Mode：选 workflow（T2VA / FL2VA）、profile（draft / balanced / final）、prompt、seed，提交。任务进入 FIFO 队列，由空闲 worker 执行；超过并发上限的任务显示"排队第 N 位"而不是报错。
- 画布：`/canvas/<worker-id>/` 是该 worker 的原生 ComfyUI 界面（通过 Studio 代理）。在画布里直接排队的任务只在那一张卡上跑，不经过调度。
- 产物：`/api/runs/<run_id>/artifacts/<id>/file`，支持 Range，页面里可直接播放。

## 目录

```
h3_studio/      服务端：config / store / workers / service / comfy / workflows / server + static/index.html
config/         worker-pool.json  generation-profiles.json  runtime-lock.json  asset-manifest.json  requirements-lock.txt
workflows/      comfy-ui/（可导入画布的图）  comfy-api/（Guided Mode 提交用的 API 格式）
scripts/        prepare_runtime.py  start.py  e2e.py  dev_fake_workers.py
tests/          python3 -m unittest（fake ComfyUI worker，不需要 GPU）
docs/           ARCHITECTURE.md  OPERATIONS.md  LICENSES.md  adr/
var/            运行时数据（ignored）
```

## 常用命令

```bash
python3 -m unittest -v                         # 单元 + HTTP 层测试，10 秒左右
python3 scripts/dev_fake_workers.py            # 无 GPU 起一个带 5 个假 worker 的 Studio，看 UI
python3 scripts/start.py --legacy-studio --workers worker-gpu0 # 显式历史入口
python3 scripts/e2e.py concurrent --count 3    # 真机并发测试 + 媒体校验（看主机内存峰值）
python3 scripts/e2e.py profiles                # draft/balanced/final 各跑一次
```

## 历史实测与边界（不代表本轮通过）

- 旧 RH 环境曾验证：单 A5000 上 T2VA/FL2VA 出带立体声的 864×480 / 5 s 视频；两卡并发。
- `safe_concurrent_runs` 默认 2：来自 251 GiB 主机内存下的两卡实测（每个运行中的 worker 约 41 GiB 主存）。放开到 3–5 之前先用 `e2e.py concurrent --count N` 实测。
- 多卡加速**单个**任务（Single-Request Multi-GPU）尚未实现，路线评估见 [docs/OPERATIONS.md](docs/OPERATIONS.md#多卡路线)。
- 无鉴权、无多用户、不做公网部署。模型权重、运行时、媒体和日志都在 `var/`，不进 Git。

R1–R4 阶段的 review、work log 和探针脚本保留在 tag `v0.1-r4-mvp`。

<!-- HARNESS:README:MANAGED:START -->
## Harness / Pi Onboarding

- 模型合同：`AGENTS.md`
- 人类手册：`Harness_manual.md`
- Pi capabilities：`.pi/`
- 项目 evidence：`docs/project-intake/`、`operations/`

第一次进入：

```bash
pi --name "00-orchestration"
```

在 Orchestration session 里澄清需求、收敛范围、切分开发 round。规划确认后用 `/fleet` 把每个 round 分发成独立 session；round 内由 pi-subagents 分配 builder / reviewer，新增代码由 ponytail 做门禁。

Owner 只在规划阶段介入。已有 baseline 后，清楚的 bounded task 直接执行并验证。
<!-- HARNESS:README:MANAGED:END -->
