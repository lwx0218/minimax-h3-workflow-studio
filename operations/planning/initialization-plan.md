# MiniMax H3 Studio Checkpoint Ledger

> **SUPERSEDED legacy plan:** this file replaces the former R1–R7 future-delivery ledger. The historical R1 experiment records remain unchanged as evidence. The governing source is [`operations/planning/rebaseline-plan-v1.md`](rebaseline-plan-v1.md).

## Gate

- Project：MiniMax H3 Studio
- Goal：ComfyUI-first local H3 Studio with Guided Mode, Advanced Canvas and multi-Worker Replica Execution
- Current checkpoint：R3 — Single-Worker Product (`accepted`)
- Next checkpoint：R4 — Multi-Worker MVP (`pending`)
- Route：`fixed-round-plan`
- Source precedence：[`CONTEXT.md`](../../CONTEXT.md) → accepted ADR → [`operations/planning/rebaseline-plan-v1.md`](rebaseline-plan-v1.md) → [`operations/planning/orchestration-v1.md`](orchestration-v1.md) → current product docs → historical evidence

## Checkpoint Ledger

| Round | Primary implementation session | Independently reviewable delivery boundary | Acceptance evidence | Status |
|---|---|---|---|---|
| R1 | R1-baseline-reset | ComfyUI-first source of truth、冲突检查、文档 Review 和 checkpoint | docs; conflict scan; review; checkpoint commit | accepted |
| R2 | R2-runtime-decision | A5000 上一个可复现优化 H3 ComfyUI path；SwarmUI 或 thin Control Plane disposition | valid cold/warm media probe; pinned stack; SwarmUI disposition | accepted |
| R3 | R3-single-worker-product | Controlled Distribution、Guided Mode、Advanced Canvas、单 Worker T2VA/FL2VA | controlled Distribution; valid workflows; traceable Runs and Artifacts | accepted |
| R4 | R4-multi-worker-mvp | 至少两个独立 Worker 并发、五卡 queued work、安全和最终 MVP | two concurrent valid Runs; five-GPU pool readiness; recovery/profile/packaging evidence | pending |

Historical R1 feasibility is `accepted / feasible_with_constraints` as evidence disposition during R1 Baseline Reset. R2 Runtime Decision is `accepted` at the R2 checkpoint commit. It is not a fifth/current checkpoint. Single-Request Multi-GPU is optional Track X and does not block the ledger.

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
- Bug 和 Review finding 留在当前 Round；不创建字母子阶段或隐藏后续 acceptance unit。Round R1–R4 是四个 named checkpoints 的编号，不是旧 R1–R7 的延续。
- 只有 Owner 批准的 Goal/Spec/architecture change 才能重基线。
