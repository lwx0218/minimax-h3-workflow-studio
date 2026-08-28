# MiniMax H3 Studio

MiniMax H3 Studio 是一个面向单机单用户的本地 H3 音视频生成产品。产品复用固定版本的 ComfyUI backend 与 frontend 作为 workflow、node、queue 和 execution 的权威基础，在其上提供 H3 Guided Mode、Advanced Canvas 与多 Worker 协调。

## 当前状态

- **Baseline Reset：accepted**（checkpoint commit 及 post-commit verify 已通过）
- **Historical R1：accepted / feasible_with_constraints**
- **下一 checkpoint：Runtime Decision**
- 产品实现：尚未开始
- ComfyUI 安装、模型下载和新的 GPU 实验：本次重置未执行
- R1 证据：[`operations/reviews/2026-08-21-r1-feasibility-report.md`](operations/reviews/2026-08-21-r1-feasibility-report.md)
- 重基线来源：[`CONTEXT.md`](CONTEXT.md)、[`docs/adr/0001-use-comfyui-as-studio-foundation.md`](docs/adr/0001-use-comfyui-as-studio-foundation.md)、[`operations/planning/rebaseline-plan-v1.md`](operations/planning/rebaseline-plan-v1.md)

历史 R1 的单卡 C3 是有效的约束可行性证据：official `kitchen_int8` 路径生成了带视频和立体声音频的 MP4，但约 30.6 分钟的 cold probe 不是交互产品基线。4-GPU 单请求路线保持为可选 Track X，不阻塞产品路线。

## 产品边界

- Guided Mode 是常用入口；完整 ComfyUI Advanced Canvas 保留给高级编辑。
- H3 Workflow 使用原生 ComfyUI workflow/API 格式；不创建平行的 WorkflowDocument、Node Registry、ExecutionPlan、DAG Executor 或自定义画布。
- 多 GPU MVP 通过至少两个隔离的 ComfyUI Worker 执行独立 Runs（Replica Execution）；Single-Request Multi-GPU 是独立的后续实验。
- Backend/API 生成只是技术证据；MVP 必须由用户从产品入口提交、观察执行并取得可播放的带立体声音频视频。
- 模型权重、运行时、缓存、日志、数据库和媒体不进入 Git；项目配置通过未提交的 `.env.local` 承接。

## Source of Truth

按优先级阅读：

1. [`CONTEXT.md`](CONTEXT.md)
2. [`docs/adr/0001-use-comfyui-as-studio-foundation.md`](docs/adr/0001-use-comfyui-as-studio-foundation.md)
3. [`operations/planning/rebaseline-plan-v1.md`](operations/planning/rebaseline-plan-v1.md)
4. [`operations/planning/orchestration-v1.md`](operations/planning/orchestration-v1.md)
5. [`operations/planning/initialization-plan.md`](operations/planning/initialization-plan.md)
6. [`docs/specs/mvp-v0.md`](docs/specs/mvp-v0.md)、[`docs/architecture/architecture-v0.md`](docs/architecture/architecture-v0.md) 与 [`docs/development/process.md`](docs/development/process.md)
7. [`AGENTS.md`](AGENTS.md)、[`Harness_manual.md`](Harness_manual.md)
8. 最新 work log/review；历史 R1 计划、日志、Review 和运行证据只说明已发生的事实

## Checkpoints

1. **Baseline Reset** — 文档、冲突扫描、Review 和 checkpoint commit
2. **Runtime Decision** — 在 A5000 上验证一个可复现的优化 ComfyUI H3 路径，并决定 SwarmUI 或 thin Control Plane
3. **Single-Worker Product** — Guided Mode/Advanced Canvas 的单 Worker 用户闭环
4. **Multi-Worker MVP** — 独立 Runs 并发、五卡 Worker Pool 运维和 MVP 验收

Single-Request Multi-GPU 属于可选 Track X，不是第五个 checkpoint，也不能阻塞上述路线。详见 [`operations/planning/rebaseline-plan-v1.md`](operations/planning/rebaseline-plan-v1.md)。

## 配置与运行数据

```bash
cp .env.example .env.local
```

当前 session 不启动产品。未来运行数据统一置于 `var/`；服务默认只监听 `127.0.0.1`，通过 SSH tunnel 访问。

## 历史证据

R1 的实验结果、manifest、锁定版本、资源记录和 Review artifact 均保留在 `operations/`；不重写实验事实来迎合新架构。旧 R1 future-plan clauses 已由重基线计划取代。
