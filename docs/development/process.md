# Development And Quality Process

## Purpose

定义 MiniMax H3 Workflow Studio MVP 的固定交付方式，避免：

- 每轮只实现不 Review
- 依赖用户逐次提示 Bug Fix
- Phase/round 字母无限膨胀
- 没有证据就声明完成

## Delivery Contract

- 当前 MVP 固定为 R1–R7
- 一个 round 是一个交付 gate，不是一条聊天消息
- Bug、Review 和复验属于当前 round，不创建新 round
- 只有 Owner 批准的 scope change 才能重新基线
- Phase 3 不属于当前 MVP

## Roles

### Builder

主 Pi session 负责实现、验证、修复和 closeout。

### Automated Verifier

由项目测试、类型检查、lint、构建、契约校验和真实 H3 golden workflow 提供机械证据。

### Independent Reviewer

目标模式：`spawned_pi_process`。

要求：

- 新 Pi 进程或新 session
- 只读工具
- 读取 contract、round scope 和完整改动
- 输出 P0/P1/P2 findings
- 不修改实现
- Review artifact 写入 `operations/reviews/`

如果该模式未通过 capability check，使用 `same_session`，并在 work log 中明确隔离级别降低。

### Owner

负责 Goal、Spec、重大架构变化、外部授权和最终体验接受。Owner 不负责驱动常规 Review/Fix 循环。

## Round Lifecycle

```text
Definition of Ready
  -> Round Plan
  -> Implement
  -> Automated Verify
  -> Independent Review
  -> Fix P0/P1
  -> Regression Verify
  -> Final Review Decision
  -> Pre-Commit Acceptance Gate
  -> Work Log + Ledger accepted candidate
  -> Acceptance Commit
  -> Post-Commit Verify
  -> accepted effective
```

一轮可以跨多个工具调用或 session。Ledger 中待提交的 `accepted` 是 candidate 状态，只有 acceptance commit 成功且 post-commit 检查通过后才生效；若 commit 失败，必须恢复为 `in_progress`。

## Definition of Ready

开始一个 round 前必须满足：

- 前置 round 已 accepted，或当前为 R1
- Round Ledger 中 scope 和 acceptance 明确
- 已读取 Goal、Spec、Architecture 和最新 evidence
- 已列出预期改动面和验证命令
- 没有未决的阻塞性产品决策
- Git 基线明确，机器本地生成物被忽略

不满足时先补合同或报告 blocked，不直接编码。

## Pre-Commit Acceptance Gate

创建 acceptance commit 前必须同时满足：

1. Round acceptance criteria 全部通过
2. 自动验证命令成功，或失败项有明确且获准的例外
3. Independent Review 已产出 artifact
4. P0/P1 finding 为零
5. P2 finding 已记录 disposition
6. 回归测试在修复后重新通过
7. work log 记录文件、命令、结果和已知缺口
8. Git 候选内容不包含 secret、模型、数据库、缓存或运行媒体

通过后才可以把 Ledger 准备为 `accepted` candidate 并创建 checkpoint commit。

## Definition of Done

一轮最终 accepted 还必须满足：

1. Pre-Commit Acceptance Gate 已通过
2. Ledger 的 `accepted` candidate、work log 和 review artifact 已包含在 acceptance commit
3. acceptance commit 成功
4. post-commit 验证确认 commit 存在且工作树符合预期

缺少任一项时只能是 `in_progress` 或 `blocked`。这避免“必须先 DoD 才能 commit，但 DoD 又要求 commit”的循环。

## Review Severity

- P0：安全、数据破坏、权重/密钥入库、核心结果错误；禁止接受
- P1：违反 spec、关键功能失效、重要回归、不可恢复状态；禁止接受
- P2：非阻塞维护性、体验或后续增强；记录后可以接受

Reviewer 必须给出文件/行为证据，不能只有笼统评价。

## Fixed Round Map

| Round | Scope | Acceptance Gate |
|---|---|---|
| R1 | 本地 H3 T2VA feasibility | 真实成功或形成 bounded stop decision |
| R2 | Workflow/Node/DAG contracts | Schema 与校验测试通过 |
| R3 | Storage/Queue/Executor/Mock API | Mock backend 持久执行闭环通过 |
| R4 | Frontend basic DAG | 保存、加载、Mock run 端到端通过 |
| R5 | SGLang + T2VA | 真实 T2VA 从 UI 到 MP4 闭环通过 |
| R6 | FL2VA 与完整运行管理 | 首/尾/首尾帧、取消、压缩和清理通过 |
| R7 | MVP hardening | spec 验收矩阵、全仓 Review、文档和基线通过 |

## Bounded Failure Policy

### R1

H3 feasibility 使用有限实验矩阵。不能无限增加调优子阶段。结果必须收敛为：

- feasible
- feasible_with_constraints
- blocked，需要 Owner 选择后端或调整目标

### 其他 Round

- 普通 Bug：留在原 round 修复
- 超出 scope 的 enhancement：放入 Phase 3 backlog
- 根本架构错误：标记 blocked，提交 change request，不私自增加 round

## Git Policy

- Phase 0 创建 baseline commit
- 每个 R1–R7 只在 Pre-Commit Acceptance Gate 通过后创建 acceptance commit
- Review 前保留可审查 diff
- 不提交 `.env.local`、`var/` 产物、虚拟环境或模型
- 不自动 push 远端
- tag 仅在 R7 最终验收后创建，除非 Owner 另行要求

## Operator Interaction Policy

Builder 只在以下控制门暂停：

- 需要改变 Goal/Spec
- R1 技术路线不可行
- 需要外部 secret、许可或业务判断
- 即将执行未获授权的破坏性/系统级操作
- 最终 R7 Owner acceptance

其余测试、Review、Fix 和复验不要求 Owner 逐步发 prompt。

## Honest Completion Rule

AI、测试和独立 AI Review 都不能保证零缺陷。流程保证的是：

- 不跳过质量门
- 不隐藏失败
- 不把 incomplete 称为 complete
- 每个结论都有可回看的 evidence
- 重大残余风险由 Owner 明确接受
