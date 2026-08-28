# Development And Quality Process

## Purpose

本流程服务于四个 named checkpoints，避免把历史 R1 实验闭环误延续为旧 R2–R7 产品编排。`Round` 不再是本项目当前的产品进度单位；Baseline Reset、Runtime Decision、Single-Worker Product、Multi-Worker MVP 是唯一的交付 checkpoint。

## Source of Truth

执行顺序为 [`CONTEXT.md`](../../CONTEXT.md)、accepted ADR、[`operations/planning/rebaseline-plan-v1.md`](../../operations/planning/rebaseline-plan-v1.md)、[`operations/planning/orchestration-v1.md`](../../operations/planning/orchestration-v1.md)、[`operations/planning/initialization-plan.md`](../../operations/planning/initialization-plan.md)、MVP spec、architecture、本文件、`AGENTS.md` 和 `Harness_manual.md`，再读最新 work log/review。旧 R1 计划/Review/work log 只证明历史事实；其未来计划条款已 SUPERSEDED。

## Checkpoint Lifecycle

适用的 checkpoint 按风险选择最小闭环：

```text
Definition of Ready -> Implement -> Automated Verify -> Risk-Proportional Review
  -> Fix P0/P1 -> Regression Verify -> Pre-Commit Gate
  -> Work Log + Ledger candidate -> Checkpoint Commit -> Post-Commit Verify
```

Baseline Reset 是 Class A 文档/架构重基线：必须做冲突扫描、链接检查和一次独立只读文档 Review。产品 checkpoint 的验证深度按其 contract 执行；不要预先开发后续 checkpoint 的代码。

## Baseline Reset Contract

范围仅限：落入 package 的 source-of-truth 文件，更新 README、intake、MVP spec、architecture、Master Plan/Checkpoint Ledger（`operations/planning/initialization-plan.md`）、AGENTS 和 Harness manual，处置旧 future-plan clauses，记录 R1 为 `accepted / feasible_with_constraints`，将 Runtime Decision 设为 next，并提交一个文档 checkpoint。

明确禁止：安装 ComfyUI、下载权重、GPU 实验、修改驱动/内核、产品实现、重写或删除 R1 证据。

## Review

- Class A：source-of-truth、runtime/model lock、GPU safety、licenses、concurrency 和 artifact deletion；需要独立 reviewer，记录 P0/P1/P2。
- Class B：产品 Control Plane、workflow templates、Runs、Guided Mode 和 recovery；自动验证加 focused review。
- Class C：例行文档和非执行模板；机械检查加 self-review。

P0/P1 必须在当前 checkpoint 修复并复验；P2 必须有 disposition。Reviewer 不修改候选文件；Builder 负责记录 durable artifact。

## Pre-Commit Gate

提交前必须满足：

1. checkpoint acceptance criteria 已满足；
2. 自动验证成功，或例外已明确记录；
3. 要求的 Review artifact 存在；
4. P0/P1 为零，P2 有 disposition；
5. work log 记录文件、命令、结果和已知限制；
6. staged 内容不含 secret、权重、数据库、cache、环境或媒体。

Checkpoint 的 `accepted candidate` 只有在 commit 成功且 post-commit 检查通过后才生效。不要把聊天记录当作 durable authority。

## Historical R1

R1 结论保留为：single-card local H3 `feasible_with_constraints`；C3 是有效 evidence；约 30.6 分钟不是 interactive baseline；4-GPU single-request 路线未证明，转入 Track X。R1 的旧 blocked gate 不再阻塞 Runtime Decision，也不重新启动 R2–R7。

## Git And Portability

- 一个 checkpoint 一个 scoped commit；不自动 push。
- 权重、runtime state、logs、cache、databases、media 和 `.env.local` 必须 ignored。
- 提交路径使用相对路径，不硬编码宿主机绝对路径。
- 若发现与 Owner 已批准决策实质冲突，停止并请求 Owner；普通文档冲突由 Builder 依据 source-of-truth precedence 修复。
