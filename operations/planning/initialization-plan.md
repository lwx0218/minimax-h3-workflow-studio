# MiniMax H3 Studio Checkpoint Ledger

> **SUPERSEDED legacy plan:** this file replaces the former R1–R7 future-delivery ledger. The historical R1 experiment records remain unchanged as evidence. The governing source is [`operations/planning/rebaseline-plan-v1.md`](rebaseline-plan-v1.md).

## Gate

- Project：MiniMax H3 Studio
- Goal：ComfyUI-first local H3 Studio with Guided Mode, Advanced Canvas and multi-Worker Replica Execution
- Current checkpoint：Baseline Reset
- Next checkpoint：Runtime Decision
- Route：`checkpoint-plan`
- Source precedence：[`CONTEXT.md`](../../CONTEXT.md) → accepted ADR → [`operations/planning/rebaseline-plan-v1.md`](rebaseline-plan-v1.md) → [`operations/planning/orchestration-v1.md`](orchestration-v1.md) → current product docs → historical evidence

## Checkpoint Ledger

| Checkpoint | Delivery | Status | Acceptance evidence |
|---|---|---|---|
| Baseline Reset | ComfyUI-first source of truth、冲突检查、文档 Review 和 checkpoint | `accepted` | package files、normative docs、verifier、Class-A review、commit/post-check |
| Runtime Decision | A5000 上一个可复现优化 H3 ComfyUI path；SwarmUI 或 thin Control Plane disposition | `queued` | cold/warm valid media、pinned stack、controller decision |
| Single-Worker Product | Controlled Distribution、Guided Mode、Advanced Canvas、单 Worker T2VA/FL2VA | `queued` | clean start、用户可见提交/进度、视频+立体声音频 |
| Multi-Worker MVP | 至少两个独立 Worker 并发、五卡 queued work、安全和最终 MVP | `queued` | two concurrent valid Runs、pool/recovery/quality/packaging evidence |

Historical R1 is `accepted / feasible_with_constraints` as evidence disposition during Baseline Reset. It is not a fifth/current checkpoint. Single-Request Multi-GPU is optional Track X and does not block the ledger.

## Baseline Reset Acceptance

- [x] package source files placed at their declared repository paths
- [x] README、intake、MVP spec、architecture、Master Plan、AGENTS、Harness manual updated
- [x] incompatible legacy future-plan clauses marked `SUPERSEDED` or replaced with direct source link
- [x] R1 evidence retained; historical C3 and 4-GPU constraints preserved
- [x] no ComfyUI install, weight download, GPU experiment or product code
- [x] documentation/link/consistency verifier passed
- [x] independent Class-A documentation review passed with no P0/P1
- [x] scoped checkpoint commit and post-commit verify (accepted at committed HEAD)

## Legacy Disposition

The former clauses requiring an independent WorkflowDocument, Node Registry, ExecutionPlan, DAG Executor, custom canvas, single-concurrency application FIFO, ComfyUI-as-reference-only semantics, and TP4 success before future implementation are **SUPERSEDED** by the rebaseline plan. They are not renamed rounds and must not be reintroduced through old prompts, reviews, or handoffs.

## Checkpoint Rules

- DoR、实现、自动验证、风险比例 Review、Fix/复验、Pre-Commit Gate、work log、scoped commit、post-commit verify 属于当前 checkpoint。
- Bug 和 Review finding 留在当前 checkpoint；不创建 R* 字母子阶段或隐藏后续 acceptance unit。
- 只有 Owner 批准的 Goal/Spec/architecture change 才能重基线。
