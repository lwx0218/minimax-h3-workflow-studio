# AGENTS.md

## Project Contract

MiniMax H3 Studio 采用 external-first、PI-native、最小治理模式。本仓库承载项目源码、配置和运行产物；外部 starter 只作来源或治理参考。

## Source Of Truth

新 session 必须依次读取：

1. `CONTEXT.md`
2. `docs/adr/0001-use-comfyui-as-studio-foundation.md`
3. `operations/planning/rebaseline-plan-v1.md`
4. `operations/planning/orchestration-v1.md`
5. `operations/planning/initialization-plan.md`
6. `docs/specs/mvp-v0.md`、`docs/architecture/architecture-v0.md`、`docs/development/process.md`
7. `Harness_manual.md`、最新 work log 和 review
8. 历史 R1 证据（只用于已执行事实）

发生冲突时，按 [`operations/planning/rebaseline-plan-v1.md`](operations/planning/rebaseline-plan-v1.md) 的 precedence 处理。旧 future-plan clauses 已 SUPERSEDED，不得通过复制粘贴恢复其 authority。

## Fixed Gate And Routing

默认最多一个 discovery 回合补齐目标、约束、入口和交付物，然后选择：

- `direct-execute`：清晰、有限的后续任务；
- `plan`：跨文件、风险、交接或验证需要 durable Plan；
- `needs-extension`：确有 package/extension/协作能力缺口。

只有 Goal/Spec 变化、Owner control decision、危险系统操作或最终 acceptance 才暂停。不要因为治理脚手架而强制创建多角色闭环。

## Current Baseline Reset Boundary

本次 Baseline Reset 只做文档、冲突扫描、Review、checkpoint commit 和 post-commit verify：

- 不安装 ComfyUI；
- 不下载权重；
- 不运行 GPU 实验；
- 不写产品代码；
- 保留 R1 实验事实，不延续旧 R2–R7 编排。

## Product Architecture Rules

- Pinned ComfyUI backend/frontend 是 graph、node、queue、execution 和 progress 的权威 foundation。
- MVP 使用原生 ComfyUI workflow/API 格式；不创建独立 WorkflowDocument、Node Registry、ExecutionPlan、DAG Executor、application FIFO queue 或 custom canvas。
- Guided Mode 是 common path；Advanced Canvas 使用完整 ComfyUI frontend。
- Control Plane 只协调 Workers 和 Runs，不成为第二个 graph execution engine。
- Replica Execution 与 Single-Request Multi-GPU 分开；后者是 Track X，不是 Functional MVP gate。
- Backend CLI/API generation 只能作为 engineering evidence，不能替代用户可见的 frontend submission、execution status 和 playable video+stereo-audio acceptance。

## Delivery And Evidence

当前 checkpoint Ledger 位于 `operations/planning/initialization-plan.md`；durable evidence 位于 `operations/work_logs/` 和 `operations/reviews/`。每个 checkpoint 按其 contract 执行 DoR、实现、自动验证、风险比例 Review、Fix/复验、Pre-Commit Gate、scoped commit 和 post-commit verify。

Review 目标模式为 `spawned_pi_process`；若 capability 不可用必须明确记录降级，不能假装独立。P0/P1 留在当前 checkpoint 修复；P2 必须 disposition。accepted 只在 commit 与 post-commit 成功后生效。

## Portability

- 提交使用相对路径；不硬编码宿主机绝对路径。
- `.env.local`、虚拟环境、模型、数据库、cache、logs、media 和 `var/` runtime 不入 Git。
- `.pi/` 只承担 intake、planning、closeout 和 portability，不放业务实现或 runtime abstraction。
