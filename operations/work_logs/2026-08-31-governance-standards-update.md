# Work Log：治理标准最小同步

## Metadata

- Project: MiniMax H3 Studio
- Task: governance standards minimal sync
- Timestamp (UTC): 2026-08-31T00:00:00Z
- Owner: project Owner
- Route: direct-execute
- Source of truth: `AGENTS.md` / `operations/planning/rebaseline-plan-v1.md`

## Summary

Owner 要求参考 `/home/superuser/dev/Harness_Workspace` 已完成的轻量治理更新，将与本项目相关的治理层规则最小化同步到当前仓库。本任务不创建新的 fixed Round，不要求 Independent Review，不修改 `.pi/` 或 harness tooling，不改变 R2/R3/R4 产品交付范围。

## Candidate Scope

本次 candidate scope 仅包含治理文档最小更新：

- `AGENTS.md`
- `Harness_manual.md`
- `README.md`
- `operations/planning/orchestration-v1.md`
- `operations/orchestration/independent-review-and-round-scope-standard.md`
- `operations/orchestration/governance-maintenance-backlog.md`
- `docs/README.md`
- `operations/reviews/review-checklist.md`
- `operations/work_logs/2026-08-28-governance-standards-update.md`

## Context Scope

只读参考：

- 当前项目：`CONTEXT.md`、ADR-0001、rebaseline plan、orchestration-v1、Checkpoint Ledger、MVP spec、architecture、development process、`README.md`、`Harness_manual.md`、最新 baseline-reset work log/review、历史 R1 事实证据。
- 外部项目：`/home/superuser/dev/Harness_Workspace/AGENTS.md`、`README.md`、`Harness_manual.md`、`operations/planning/2026-08-29-lightweight-governance-core-reset.md`、`docs/manual/governance-reference.md`、`docs/manual/document-governance.md`、starter `AGENTS.md`。

进入 context scope 不等于进入 candidate scope。

## Environment / Dirty-Worktree Scope

实施前工作树已有：

```text
 M AGENTS.md
 M Harness_manual.md
```

实施过程中曾短暂创建未提交的 formal plan/review artifact；随后 Owner 要求直接在本 session 做最小治理同步，因此已移除这些未提交 artifact，避免把本次 simple/direct 任务误变成 formal gate。`AGENTS.md` 与 `Harness_manual.md` 均为本次目标文件并纳入 candidate。

## Implemented Standards

- 同步 Harness 轻量治理核心：默认先走 native Pi `simple` path；Plan 只澄清目标、范围、风险和验证；除非 Owner 明确批准 formal mode，否则不自动创建 fixed Round、handoff、Independent Review 或 formal acceptance gate。
- 明确 `.pi/` 是 capability layer，不是 policy authority；extension、skills、prompt templates 默认 passive。
- 保留本项目已批准 R1–R4 产品 checkpoint 的有效性；其他小任务不得仅因历史 Plan/evidence、跨文件或治理脚手架存在而自动升级为 formal mode。
- 在 `README.md`、`AGENTS.md` 和 `Harness_manual.md` 明确 simple 默认、formal opt-in 和 `.pi/` capability layer 边界。
- 固化项目文档正文默认中文和 `docs/**` / `operations/**` 目录边界。
- 固化 Independent Review 三类 scope：`candidate scope`、`context scope`、`environment / dirty-worktree scope`。
- 明确进入 review bundle 不等于进入 candidate scope；Git changed/untracked paths 不自动进入当前产品 Round / task 的验收范围。
- 明确 `.pi/` / harness / extension / skill / prompt / settings / handoff-review tooling 问题默认记录为 `governance maintenance issue` 或 `review limitation`，不作为产品 candidate P1 自动修复。

## Validation

已执行：

```bash
git diff --check
git status --short
git diff --exit-code -- .pi scripts var inputs outputs .env.example .env.local
git status --short -- .pi scripts var inputs outputs .env.example .env.local
for p in src tests data; do if [ -e "$p" ]; then git diff --exit-code -- "$p"; git status --short -- "$p"; else echo "$p: absent"; fi; done
rg -n "candidate scope|dirty-worktree|governance maintenance|不得擅自修改|\\.pi|harness|Independent Review|simple|capability layer|formal mode" AGENTS.md README.md Harness_manual.md docs operations
```

结果：

- `git diff --check`：PASS。
- protected diff/status for `.pi scripts var inputs outputs .env.example .env.local`：PASS，无输出。
- `src`、`tests`、`data`：当前不存在。
- `rg`：PASS，关键规则已在 candidate 文档中落地。
- 未改 production code、tests、data、runtime config、`.pi/` 或 harness/extension/skill/prompt/settings 文件。

## Review

本任务按 Owner 最新指示采用 simple/direct 最小治理同步，不是 fixed-Round delivery；不要求 Independent Review。此前未提交 formal handoff/review 尝试失败不作为当前任务门禁，也不触发 harness 修复。

## Next

可由 Owner 决定是否创建 scoped commit。产品路线未改变，当前产品下一 checkpoint 仍为 R2 Runtime Decision。
