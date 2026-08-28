# 项目 Intake：MiniMax H3 Studio

## Metadata

- Project：MiniMax H3 Studio
- Project slug：`minimax-h3-workflow`
- Source of truth：本仓库；优先级见 [`CONTEXT.md`](../../CONTEXT.md)
- Governance mode：external-first、PI-native、按 checkpoint 按需治理
- Project root：`.`
- Governance entry：`AGENTS.md`、`Harness_manual.md`、`.pi/`
- PI readiness：`runtime-ready`
- Application readiness：`bootstrap-ready`；产品实现尚未开始
- 当前状态：Baseline Reset accepted candidate；Runtime Decision next
- 目标部署地区：中国
- 目标用户：单机、单用户创作者

## 目标

交付一个以 MiniMax-H3 为核心的本地产品：复用 pinned ComfyUI backend/frontend 的 graph、node、queue、执行和进度语义，提供 Guided Mode 与完整 Advanced Canvas，并最终通过隔离 Workers 支持独立 Runs 的并发执行。

## 架构决策

- ComfyUI 是 Studio foundation 和 workflow/API 语义的权威来源，不是视觉参考或可选 fallback。
- H3 Workflow 使用原生 ComfyUI workflow/API 格式；不维护独立 WorkflowDocument、Node Registry、ExecutionPlan、DAG Executor、application FIFO queue 或 custom canvas。
- Guided Mode 是常用产品入口；Advanced Canvas 使用完整 pinned ComfyUI frontend。
- Control Plane 只发现 Worker、分派 Run、观察进度和记录 Artifact，不重新解释或执行 graph。
- Replica Execution（多个 Worker 执行独立 Runs）与 Single-Request Multi-GPU（一个请求的 model parallel）严格分开。后者为 Track X，可不阻塞 MVP。

## 现状与约束

- 5 × RTX A5000，约 251 GiB host RAM，无 active NVLink；R1 记录了 P2P/NCCL 与 CPU staging 约束。
- Historical R1 C3：single-card official `kitchen_int8` T2VA probe 有效，`feasible_with_constraints`；约 30.6 分钟，不是交互产品基线。
- R1 事实、权重和运行产物保留在 `operations/` 与外部路径；本次不重跑实验。
- 模型权重位于仓库外，通过 `.env.local` 引用；运行时、缓存、日志、媒体和数据库不入 Git。
- 本次 Baseline Reset 不安装 ComfyUI、不下载权重、不运行 GPU 实验、不写产品代码。

## MVP 边界

必须最终支持：

- Guided Mode 的 H3 输入、提交、进度、预览/取回；
- Advanced Canvas 中原生 ComfyUI H3 Workflow 的保存、编辑和提交；
- T2VA 与 FL2VA 的有效带立体声音频视频；
- 至少两个隔离 Worker 的独立 Run 并发；
- 五张卡可在测得安全并发上限下参与 queued work；
- Run、Workflow/API snapshot、profile、model/runtime identity、seed、timing、status、Artifact 的追踪；
- 默认不执行任意第三方节点或不受信任 workflow 字段。

不包含：自定义 graph/canvas、平行可执行 workflow contract、任意第三方节点安装、公网多租户、Single-Request Multi-GPU MVP gate。

## Durable Outputs

- Source language：[`CONTEXT.md`](../../CONTEXT.md)
- ADR：[`docs/adr/0001-use-comfyui-as-studio-foundation.md`](../adr/0001-use-comfyui-as-studio-foundation.md)
- Rebaseline Plan：[`operations/planning/rebaseline-plan-v1.md`](../../operations/planning/rebaseline-plan-v1.md)
- Orchestration：[`operations/planning/orchestration-v1.md`](../../operations/planning/orchestration-v1.md)
- MVP spec：[`docs/specs/mvp-v0.md`](../specs/mvp-v0.md)
- Architecture：[`docs/architecture/architecture-v0.md`](../architecture/architecture-v0.md)
- Work logs：`operations/work_logs/`
- Review evidence：`operations/reviews/`

## Historical disposition

旧 intake 中将 ComfyUI 定义为参考、要求独立 contract、单并发 FIFO 和 R1–R7 的未来条款已由 [`operations/planning/rebaseline-plan-v1.md`](../../operations/planning/rebaseline-plan-v1.md) **SUPERSEDED**。旧 R1 实验文档仍只作为事实证据读取。
