# AGENTS.md

## Purpose

`MiniMax H3 Workflow Studio` 采用外部项目优先的最小治理模式。

本仓库应承载项目自己的源码、配置和运行产物；`Harness_Workspace` 只作为 starter 来源或治理参考，不应长期充当本项目的默认业务开发面。

## Fixed Gate

默认先过一个固定前置 gate，而不是直接展开完整闭环：

1. 用最多一个发现回合补齐目标、约束、入口和交付物
2. 在下一回合明确落到以下三选一：
   - 直接执行
   - 进入 `Plan`
   - 标记需要 package、extension 或额外协作能力

如果任务仍然模糊，优先继续收窄范围，而不是默认把流程扩成重型治理编排。

## Default Routing

- `trivial` 任务：默认直接执行，只在会话里给出 `result`、`verify`、`next step`
- `non-trivial` 任务：按需进入 `Plan`，再执行最小必要验证
- 只有在复杂度、风险、并行收益或独立审查价值明确存在时，才拆成多角色或多阶段协作

## MVP Development Contract

当前 MVP 的执行合同位于：

- `Harness_manual.md`
- `docs/specs/mvp-v0.md`
- `docs/architecture/architecture-v0.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/reviews/review-checklist.md`

执行 R1–R7 时：

- Round Ledger 是唯一进度基线
- Bug、Review 和复验留在原 round，不新增字母子阶段
- 每轮必须完成 `Implement -> Automated Verify -> Independent Review -> Fix -> Regression Verify -> Pre-Commit Gate -> Work Log/Ledger candidate -> Checkpoint Commit -> Post-Commit Verify`
- 没有 Review artifact、验证证据或仍有 P0/P1 finding 时，不得创建 acceptance commit；Ledger 的 accepted candidate 仅在 commit 与 post-commit 检查成功后生效
- 目标 Review mode 为 `spawned_pi_process`；未通过 capability check 时必须明确降级为 `same_session`
- 只有 Goal/Spec 变化、技术路线阻塞、危险操作或最终 Owner acceptance 才暂停等待用户
- 新 session 必须先读取驾驭手册、合同、Round Ledger、最新 work log 和 review

Phase 3 是 MVP 后 backlog，不参与当前 R1–R7 收线。

## Optional Grilling Skills

这个 starter 默认带三个可选 baseline skills，用于在 route 不清晰时做升级判断：

- `grill-me`
  - 需求或设计仍然模糊，但还没有稳定文档基线时使用
- `grill-with-docs`
  - 已有 `AGENTS.md`、intake、plan 或 contract 文档，需要 against-docs 盘问时使用
- `grilling`
  - 需要判断是继续 simple path，还是升级到 `Plan`、`Spec`、review、subagent、skill、MCP 或 package 时使用

这些 skills 是按需触发，不是默认必经关卡。优先保住 native PI simple path。

## Evidence Paths

最小治理留痕目录：

- `docs/project-intake/`
- `operations/planning/`
- `operations/work_logs/`
- `operations/reviews/`

按需创建或刷新这些 durable evidence；默认不为 `trivial` 任务新建新文档。

只有在以下情况才建议落盘：

- 明确进入 `Plan`
- 任务跨轮次或需要交接
- 变更影响 contract、bootstrap 或 portability
- 需要正式 review 或后续追踪

## Readiness

- `bootstrap-ready`：项目脚手架、project-local evidence 目录和首个 `docs/project-intake/<project-slug>.md` 已生成
- `runtime-ready`：在 `bootstrap-ready` 基础上，本机已安装 `pi` 且 provider/auth 已配置

初始化完成后，先按 native PI simple path 推进；不要因为 starter 已生成就把项目误判为默认开箱即用。

## Portability Rules

- 提交内容优先使用相对路径。
- 不要在仓库文件中硬编码宿主机绝对路径。
- 需要环境差异时，优先用环境变量或本地未提交配置承接。
- `.pi/` 只保留最小可读入口，不在其中叠加重型 runtime 抽象。

## Boundary

这个项目里的 `.pi` 资产是一期的 canonical governance entry，只负责：

- intake
- planning（按需）
- closeout
- portability

不要把业务实现、项目运行逻辑、多底座适配层或默认重闭环塞进 starter skill 或 prompt template。
