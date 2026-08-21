# MiniMax H3 Workflow Studio Master Plan

## Gate

- Project：MiniMax H3 Workflow Studio
- Goal：交付单机单用户、支持真实 T2VA/FL2VA 的基础 Workflow Studio MVP
- Source of truth：本仓库 Goal/Spec/Architecture/Plan；MiniMax-H3 官方资料为模型行为基线
- Entrypoints：`AGENTS.md`、`Harness_manual.md`、本文件
- Constraints：本地大模型、5×A5000、项目内运行数据、独立 workflow contract、无权重入库
- Route：`spec-then-plan`
- Quality contract：`docs/development/process.md`

## Scope Boundary

当前 MVP 固定为 R1–R7。Bug Fix、Review 和复验留在原 round 内，不创建 R1B、R1C 等新 round。只有 Owner 批准的 Goal/Spec 变化才能重新基线。

Phase 3 是 MVP 后 backlog，不参与当前项目收线。

## Round Ledger

| Round | Delivery | Status | Acceptance Evidence |
|---|---|---|---|
| Phase 0 | Intake、Spec、Architecture、Master Plan、驾驭手册、质量合同、Git baseline | `accepted` | final review pass；本状态随 baseline commit 生效 |
| R1 | H3 本地真实 T2VA 可行性 | `pending` | feasibility report + media probe metadata |
| R2 | Workflow/Node contracts 与 DAG 校验 | `pending` | schema/tests/review |
| R3 | SQLite、FIFO Queue、Executor、Artifact Store、Mock API | `pending` | integration tests/review |
| R4 | 基础画布与 Mock 端到端 | `pending` | frontend build + E2E/review |
| R5 | SGLang Adapter 与真实 T2VA 垂直闭环 | `pending` | golden workflow/review |
| R6 | FL2VA、素材、Prompt Builder、取消、压缩与清理 | `pending` | FL2VA matrix/recovery tests/review |
| R7 | 全量回归、安全、文档、性能基线和 MVP 验收 | `pending` | acceptance report + final review |

## Phase 0：Governance Baseline

### Scope

- 固化 Goal、MVP Spec 和非目标
- 定义架构边界和项目内运行目录
- 固定 R1–R7 交付 gate
- 定义 Builder、Automated Verifier、Independent Reviewer 与 Owner 职责
- 建立 Review Checklist、work log 和 Git checkpoint 规则
- 提供项目驾驭、compact 和 session handoff 手册

### Acceptance

- 可提交文件无宿主机绝对路径
- 模型、环境文件和运行产物被 Git 忽略
- R1–R7 scope 与最终验收固定
- Review 模式经过 capability check
- Phase 0 independent review 无 P0/P1
- Pre-Commit Acceptance Gate 通过
- Ledger accepted candidate 与 evidence 一起创建 baseline commit
- post-commit 检查通过后 Phase 0 accepted 生效

## Phase 1：Foundation And Minimum Prototype

Phase 1 只包含 R1–R4，不再使用 A/B/C 子阶段命名。

### R1：H3 Local Feasibility

#### Scope

- 创建 `.venv-h3/`
- 锁定首个 SGLang/Torch/CUDA 组合
- 验证 snapshot root
- 严格按照 `operations/planning/r1-h3-feasibility-matrix.md` 执行有限实验矩阵
- 提交真实 T2VA，检查 MP4 视频流和音频流
- 记录显存、主存、启动参数和耗时

#### Stop Decision

必须收敛为：

- `feasible`
- `feasible_with_constraints`
- `blocked`：由 Owner 决定更换 backend 或调整 Goal

Mock 或在线 API 不得替代本地成功结论。

### R2：Contracts And DAG

#### Scope

- WorkflowDocument v1
- NodeDefinition/NodeResult
- typed ports
- DAG validation/topological ordering
- Run state contract

#### Acceptance

- Schema 正反例测试
- 环路、未知节点、端口和缺失输入测试
- Contract review 无 P0/P1

### R3：Backend Execution Core

#### Scope

- Backend package
- SQLite migrations/repositories
- 单并发 FIFO queue
- Executor 和重启状态恢复
- Artifact Store 和项目内路径边界
- MockH3Backend
- 最小 API

#### Acceptance

- Mock 持久执行闭环
- 排队、取消、失败和 interrupted 测试
- Artifact 路径逃逸测试

### R4：Frontend Mock Vertical Slice

#### Scope

- React/TypeScript/Vite
- 基础节点画布
- 节点增删、连线和参数编辑
- Workflow 保存/加载
- Mock run、状态和测试产物展示

#### Acceptance

- 前端 build/typecheck
- Mock E2E
- 保存加载一致性

## Phase 2：Real H3 MVP

Phase 2 只包含 R5–R7。

### R5：SGLang T2VA Vertical Slice

- 实现 H3Backend/SGLang adapter
- UI 到 backend 到 SGLang 到带音频 MP4
- 保存完整运行快照和 artifact metadata
- 建立真实 T2VA golden workflow

### R6：FL2VA And Run Management

- Raw Prompt 与本地 Prompt Builder
- 首帧、尾帧和首尾帧 FL2VA
- 上传、预览、下载和删除
- 取消、重启恢复和失败清理
- 大 JSON/日志压缩

### R7：MVP Hardening And Acceptance

- 全量自动回归
- T2VA/FL2VA golden matrix
- 安全和路径检查
- Git ignore/portability 检查
- 性能基线和已知限制
- 全仓 independent review
- MVP acceptance report
- Owner 最终体验确认

## Final Acceptance Gate

MVP 只有在以下条件全部满足时收线：

1. `docs/specs/mvp-v0.md` 的 12 项验收标准全部有证据
2. R1–R7 全部为 `accepted`
3. 自动测试、构建和真实 H3 golden workflows 通过
4. 无未解决 P0/P1 finding
5. P2 finding 全部有 disposition
6. 所有运行数据位于 `var/` 且不进入 Git
7. 操作、恢复和已知限制文档完整
8. Owner 完成一次 UI 与真实生成体验确认
9. 创建最终 checkpoint；tag 仅在 Owner 要求时创建

## Quality Loop

每个 round 强制执行：

```text
DoR -> Implement -> Automated Verify -> Independent Review
    -> Fix P0/P1 -> Regression Verify -> Pre-Commit Gate
    -> Work Log + Ledger accepted candidate -> Checkpoint Commit
    -> Post-Commit Verify -> accepted effective
```

不得把 Review/Fix 转移给 Owner 逐条驱动。Commit 失败时 Ledger 必须恢复为 `in_progress`，不得保留失真的 accepted 状态。

## Change Control

- 普通 Bug：原 round 内修复
- 非 MVP enhancement：Phase 3 backlog
- 技术路线阻塞：Round 标记 `blocked`，等待 Owner 决策
- Goal/Spec 变化：单独 change request，经 Owner 确认后才能调整 Round Ledger
- 不允许通过添加字母子阶段隐藏失控范围

## Next Control Gate

Phase 0 baseline review 与 commit 完成后，新建干净 session 进入 R1。R1 开始重型依赖安装前，再检查 Definition of Ready 和实验矩阵。
