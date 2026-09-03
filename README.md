# MiniMax H3 Studio

本地、单机、单用户的 MiniMax-H3 音视频生成工作台。ComfyUI（固定版本）负责画布、节点、队列和执行；本项目只加一层很薄的 Studio：一个 Guided Mode 页面、一个把任务分配到多张 GPU 的调度器，以及每张卡 ComfyUI 画布的反向代理。

```
浏览器 ──► Studio :30210 ──┬──► worker-gpu0  ComfyUI :30211 (GPU 0)
          Guided Mode      ├──► worker-gpu1  ComfyUI :30212 (GPU 1)
          /canvas/<id>/    ├──► …
          /api/runs        └──► worker-gpu4  ComfyUI :30215 (GPU 4)
```

一张卡一个 ComfyUI 进程；Studio 是唯一入口，worker 只监听本机回环地址。

## 快速开始

```bash
cp .env.example .env.local        # 填 H3_MODEL_ROOT，需要局域网访问时把 H3_STUDIO_HOST 改成 0.0.0.0
set -a; . ./.env.local; set +a

python3 scripts/prepare_runtime.py --check-only   # 校验模型文件
python3 scripts/prepare_runtime.py                # 拉取固定版本 ComfyUI + venv + 链接权重（一次）
python3 scripts/start.py                          # 启动 5 个 worker + Studio，Ctrl-C 全部停止
```

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
python3 scripts/start.py --workers worker-gpu0 # 只起一张卡
python3 scripts/e2e.py concurrent --count 3    # 真机并发测试 + 媒体校验（看主机内存峰值）
python3 scripts/e2e.py profiles                # draft/balanced/final 各跑一次
```

## 现状与边界

- 已验证：单 A5000 上 T2VA/FL2VA 出带立体声的 864×480 / 5 s 视频；两卡并发。
- `safe_concurrent_runs` 默认 2：来自 251 GiB 主机内存下的两卡实测（每个运行中的 worker 约 41 GiB 主存）。放开到 3–5 之前先用 `e2e.py concurrent --count N` 实测。
- 多卡加速**单个**任务（Single-Request Multi-GPU）尚未实现，路线评估见 [docs/OPERATIONS.md](docs/OPERATIONS.md#多卡路线)。
- 无鉴权、无多用户、不做公网部署。模型权重、运行时、媒体和日志都在 `var/`，不进 Git。

R1–R4 阶段的 review、work log 和探针脚本保留在 tag `v0.1-r4-mvp`。
