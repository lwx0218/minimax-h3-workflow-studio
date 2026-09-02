# MiniMax H3 Studio 驾驭手册

## 当前基线

- Baseline Reset：`accepted`；checkpoint commit 与 post-commit verify 已成功
- Historical R1：`accepted / feasible_with_constraints`
- R2 Runtime Decision：`accepted`；ComfyUI H3 runtime 与 thin Control Plane 方向已确定
- R3 Single-Worker Product：`accepted`；Guided Mode/Advanced Canvas 单 Worker T2VA+FL2VA 产品切片已验证
- 下一 checkpoint：R4 — Multi-Worker MVP (`pending`)

## 新 Session 读取顺序

1. `CONTEXT.md`
2. `docs/adr/0001-use-comfyui-as-studio-foundation.md`
3. `operations/planning/rebaseline-plan-v1.md`
4. `operations/planning/orchestration-v1.md`
5. `operations/planning/initialization-plan.md`
6. `docs/specs/mvp-v0.md`、`docs/architecture/architecture-v0.md`、`docs/development/process.md`
7. `AGENTS.md`、最新 work log 和 review
8. 历史 R1 证据仅用于事实核对

Chat history 不是 source of truth。Source-of-truth precedence 见 rebaseline plan。

## Owner 决策

Owner 只需介入：Goal/Spec 或架构变化、Runtime Decision 的控制选择、危险系统操作、许可/密钥信息和最终产品体验 acceptance。普通文档冲突、测试、Review finding、Fix 和复验由 Builder 处理。

## Checkpoints

| Checkpoint | 结果 |
|---|---|
| R1 — Baseline Reset | 文档、冲突扫描、Review、checkpoint commit |
| R2 — Runtime Decision | 一个可复现的 A5000 ComfyUI H3 runtime；SwarmUI 或 thin Control Plane 决策 |
| R3 — Single-Worker Product | Guided Mode/Advanced Canvas 到单 Worker 的用户闭环 |
| R4 — Multi-Worker MVP | 独立 Runs 并发、五卡 Worker Pool 和最终验收 |

Single-Request Multi-GPU 是 Track X，可选且不阻塞四个 checkpoint。不得恢复旧 R2–R7 或创建字母子阶段。

## 产品边界

ComfyUI backend/frontend 是权威 graph、node、queue 和 execution foundation。Workflow 使用原生 ComfyUI workflow/API；项目不创建独立 WorkflowDocument、Node Registry、ExecutionPlan、DAG Executor、application FIFO queue 或 custom canvas。Guided Mode 是 common path，Advanced Canvas 保留完整 ComfyUI 编辑能力。

Replica Execution（独立 Worker 执行独立 Runs）与 Single-Request Multi-GPU（单请求 model parallel）必须分开。Backend/API 生成不能替代用户从 Guided Mode 或 Advanced Canvas 提交并取得可播放视频和立体声音频。

## Checkpoint 闭环

```text
DoR -> Implement -> Automated Verify -> Risk-Proportional Review
-> Fix P0/P1 -> Regression Verify -> Pre-Commit Gate
-> Work Log/Ledger candidate -> Checkpoint Commit -> Post-Commit Verify
```

Class A source-of-truth、runtime、GPU safety、license 和 concurrency 变化需要独立只读 Review。Review artifact 由 Builder 写入 `operations/reviews/`；P0/P1 必须留在当前 checkpoint 修复，P2 必须记录 disposition。

## R1 历史事实

R1 C3 是有效的 single-card constrained local T2VA probe；约 30.6 分钟不是 interactive default。4-GPU single-request 路径因 host staging/NCCL/AdaLN 约束未证明，已转为 Track X。保留原始报告、manifest、日志和 Review，不重跑、不改写其实验事实。

## 常用状态检查

```bash
git status --short --branch
git log -1 --oneline --decorate
```

后续 session 必须只执行 [`operations/planning/rebaseline-plan-v1.md`](operations/planning/rebaseline-plan-v1.md) 中当前 checkpoint，先做 DoR，再记录 target-host/runtime/model identity，最后完成验证、Review、work log、checkpoint commit 和 post-check。
