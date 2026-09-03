# Architecture

## 原则

1. **ComfyUI 是执行引擎，不是参考。** 画布、节点、队列、执行、进度事件全部来自固定版本的上游 ComfyUI（见 `config/runtime-lock.json`）。本项目不写画布、不写 DAG 执行器、不写节点注册表、不定义第二套 workflow 格式。理由见 [adr/0001](adr/0001-use-comfyui-as-studio-foundation.md)。
2. **一张卡一个 ComfyUI 进程。** ComfyUI 单进程只用一张卡、只有一个串行队列，这是上游架构。多卡 = 多进程（worker）。
3. **Studio 只做三件事：** 分配任务、记录任务、代理界面。它提交的是原生 ComfyUI API prompt，记录的是 Run 元数据，不碰图语义。
4. **零第三方依赖。** `h3_studio/` 只用标准库，可以用系统 `python3` 跑，不依赖 ComfyUI 的 venv。

## 组件

| 模块 | 职责 |
|---|---|
| `config.py` | 读 `config/*.json` 和环境变量（`H3_*`），profile 别名解析 |
| `store.py` | Run 记录：`var/h3-studio/runs/<run_id>/run.json`，内存索引 + 写穿；状态常量 |
| `workers.py` | `WorkerPool`：worker 列表、后台健康检查线程、租约（worker ↔ run）、主机内存闸门、LRU 分配 |
| `service.py` | `StudioService`：提交 → FIFO 队列 → 派发到 worker → 轮询 `/queue` `/history` 同步状态 → 释放；取消；重启恢复 |
| `comfy.py` | 最小 ComfyUI HTTP 客户端 + history 解析 |
| `workflows.py` | 把 profile / prompt / seed 打进 `workflows/comfy-api/*.json` 模板的指定节点 |
| `server.py` | HTTP：JSON API、静态页、产物流式代理（Range 透传）、`/canvas/<id>/` HTTP+WebSocket 反向代理 |
| `assets.py` | 校验 `H3_MODEL_ROOT` 下的模型文件（存在性、safetensors 头、可选 SHA-256） |
| `static/index.html` | Guided Mode 页面：提交表单、任务列表（多任务同时显示进度）、worker 池状态 |

## Run 生命周期

```
pending ──► submitting ──► queued ──► running ──► completed
   │             │            │          │     └─► failed
   └─────────────┴────────────┴──────────┴───────► cancelled
```

- `pending`：在 Studio 队列里，没有 worker。取消 = 直接标记。
- `submitting`：已租到 worker，正在上传首帧 / 提交 prompt。
- `queued`：在该 worker 的原生 ComfyUI 队列里（`/queue` 的 `queue_pending`）。取消 = `POST /queue {"delete":[prompt_id]}`，不会影响该卡上正在跑的其他任务。
- `running`：`/queue` 的 `queue_running`。取消 = `POST /interrupt`。
- 终态通过 `/history/<prompt_id>` 判定；`completed` 时从 history 里收集视频产物。
- 一个 Run 从 `submitting` 到终态一直持有 worker 租约；租约数 ≤ `safe_concurrent_runs`。

派发规则（`service.dispatch`）：按创建时间 FIFO；主机内存超过 abort/hard 线、租约满、或没有健康空闲 worker 时整个队列等待（不跳队）。后台线程每 3 秒同步所有活动 Run 并尝试派发，所以浏览器不开着任务也会推进。

重启恢复（`service.recover`）：对磁盘上仍是活动状态的 Run，问 worker 的 history/queue：完成了就收产物，还在跑就重新挂租约，worker 已经不认识它就标 failed。

## 网络

- Studio 监听 `H3_STUDIO_HOST:H3_STUDIO_PORT`（默认 `127.0.0.1:30210`，要给局域网用改成 `0.0.0.0`）。
- worker 监听 `config/worker-pool.json` 的 `worker_host`（默认 `127.0.0.1`）+ 各自端口，只被 Studio 访问。
- `/canvas/<worker-id>/...` 原样转发给 worker（HTTP 和 WebSocket）。ComfyUI 前端用相对路径请求 API，所以能挂在子路径下；代理会把 `Host`/`Origin` 改写成 worker 自己的地址以通过 ComfyUI 的 origin 检查。
- 页面上的进度条来自 `/canvas/<id>/ws?clientId=<run.client_id>`：Studio 用 `client_id` 提交 prompt，浏览器用同一个 id 连 worker 的 WebSocket 就能收到 `progress` 事件。

## 术语

- **Worker**：绑定一张 GPU 的独立 ComfyUI 进程。
- **Worker Pool**：全部 worker；`safe_concurrent_runs` 限制同时执行的 Run 数（由主机内存决定，不是 GPU 数）。
- **Run**：一次 Guided Mode 提交：输入快照、profile、模型/运行时身份、seed、分配到的 worker、状态、产物。
- **Generation Profile**：`draft / balanced / final`，一组采样参数（分辨率、时长、sigma 点数等）。
- **Replica Execution**：多 worker 各跑各的 Run（已实现）。
- **Single-Request Multi-GPU**：多张卡加速同一个 Run（未实现，见 OPERATIONS.md）。
