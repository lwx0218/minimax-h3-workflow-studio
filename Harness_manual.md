# MiniMax H3 Studio 驾驭手册

## 文档语言约定

面向 Owner 的聊天总结、交付说明、状态报告和控制门提示默认使用中文。治理文档新增或实质更新默认使用中文；文件名、命令、代码标识、协议字段和必要原文引用可保留英文。

## 默认治理模式

默认先走 native Pi `simple` path：理解请求、必要时少量澄清、执行 bounded change、运行相称验证、用中文总结。只有 Owner 明确批准时，才启用 fixed Round、Independent Review、session handoff 或 formal acceptance gate。

`.pi/` 是 capability layer，不是 policy authority；extension、skills、prompt templates 的存在不会自动激活 formal workflow。历史 operations 记录只作为事实证据，不自动恢复旧流程。

当前已批准的 R1–R4 产品 checkpoint 仍按 rebaseline plan 执行；其他小任务不要因为跨文件、历史 evidence 或治理脚手架存在而自动升级为 fixed Round。

## 当前基线

- Baseline Reset：`accepted`；checkpoint commit 与 post-commit verify 已成功
- Historical R1：`accepted / feasible_with_constraints`
- R2 Runtime Decision：`accepted`；ComfyUI H3 runtime 与 thin Control Plane 方向已确定
- R3 Single-Worker Product：`accepted`；Guided Mode/Advanced Canvas 单 Worker T2VA+FL2VA 产品切片已验证
- R4 Multi-Worker MVP：`accepted_candidate_to_commit`；final review 已通过，等待 scoped commit、post-commit verify 和 Owner final acceptance

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
| R4 — Multi-Worker MVP | 独立 Runs 并发、五卡 Worker Pool 和最终验收（accepted candidate to commit） |

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

Class A source-of-truth、runtime、GPU safety、license 和 concurrency 变化在对应批准 checkpoint/formal task 中需要独立只读 Review。Review artifact 由 Builder 写入 `operations/reviews/`；P0/P1 必须留在当前 checkpoint 修复，P2 必须记录 disposition。

Independent Review 必须区分 candidate scope、context scope 与 environment / dirty-worktree scope。进入 review bundle 不等于进入 candidate scope；Git changed/untracked paths 不自动进入当前产品 Round / task 的验收范围。`.pi/` / harness / extension / skill / prompt / settings 问题默认记录为 governance maintenance issue 或 review limitation，不作为产品 candidate P1 自动修。

## R1 历史事实

R1 C3 是有效的 single-card constrained local T2VA probe；约 30.6 分钟不是 interactive default。4-GPU single-request 路径因 host staging/NCCL/AdaLN 约束未证明，已转为 Track X。保留原始报告、manifest、日志和 Review，不重跑、不改写其实验事实。

## 常用状态检查

```bash
git status --short --branch
git log -1 --oneline --decorate
```

R4 candidate 使用 `scripts/start_r4_worker_pool.py` 启动 Worker Pool；详见 `docs/operations/r4-multi-worker-mvp.md`。后续 session 必须只执行 [`operations/planning/rebaseline-plan-v1.md`](operations/planning/rebaseline-plan-v1.md) 中当前 checkpoint，先做 DoR，再记录 target-host/runtime/model identity，最后完成验证、Review、work log、checkpoint commit 和 post-check。
