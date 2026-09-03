# AGENTS.md

## Project Contract

MiniMax H3 Studio 采用 external-first、PI-native、最小治理模式。本仓库承载项目源码、配置和运行产物；外部 starter 只作来源或治理参考。

`AGENTS.md` 是项目内模型执行入口；产品和交付权威仍按 Source Of Truth 顺序解析。`.pi/` 是 capability layer，不是 policy authority；extension、skills、prompt templates 默认 passive，不会因为存在而自动启用 formal workflow、Round、handoff、review gate 或进度 widget。

## 文档语言约定

面向 Owner 的聊天总结、交付说明、状态报告，以及面向 Owner 和用户的 README、操作说明、工作日志和 Review 正文默认以中文为主。新增或实质更新的项目文档正文默认中文；文件名、代码标识、命令、协议字段和必要英文引用可以保留英文。已批准或归档的英文历史证据不强制全文翻译；如需更新，优先补中文状态说明，避免破坏历史语境。`docs/` 放产品合同、研究事实基线和参考材料；`operations/` 放 Plan、orchestration、work log、review 和 archive。临时 zip、一次性 handoff、runtime residue 不作为长期事实源。

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

默认永远先走 native Pi `simple` path：理解请求、必要时少量澄清、执行 bounded change、运行相称验证、用中文总结。复杂、跨文件、跨 session 或已有历史 Plan/evidence 不会自动升级为 fixed Round、handoff、Independent Review 或 formal gate。

默认最多一个 discovery 回合补齐目标、约束、入口和交付物，然后选择：

- `direct-execute`：清晰、有限的后续任务；
- `plan`：目标、范围、风险、验证或交接需要 durable clarification；
- `review-only`：Owner 只要 findings，不要实现；
- `needs-extension`：确有 package/extension/协作能力缺口。

Plan 只用于澄清 goal、scope、risk 和 validation；除非 Owner 明确批准 formal mode，Plan 不自动创建 fixed Round、handoff、Independent Review 或 formal acceptance gate。当前已批准的 R1–R4 产品 checkpoint 仍按 rebaseline plan 执行；其他小任务不得仅因治理脚手架而强制创建多角色闭环。

只有 Goal/Spec 变化、Owner control decision、危险系统操作、formal mode activation 或最终 acceptance 才暂停。

## Review Scope And Governance Layer

Independent Review 只评审当前 active task / Round 的 candidate 是否满足批准合同，必须区分三类 scope：

- `candidate scope`：当前任务 / Round 请求验收的实际变更；reviewer 可以对它给 P0/P1/P2。
- `context scope`：判断 candidate 所需的只读合同、Plan、spec、source、tests、baseline；进入 context 不等于成为 candidate。
- `environment / dirty-worktree scope`：Git dirty/untracked、pre-existing local files、工具目录、环境残留；只用于透明记录、immutability 和污染风险判断，不自动成为当前 candidate。

进入 review bundle 不等于进入 candidate scope。Git changed/untracked paths 不自动进入当前产品 Round / task 的验收范围。Review 发现非当前任务问题时，应分类为当前产品阻塞、review evidence limitation、governance maintenance issue 或非当前 task / Round backlog；不要把 governance / harness / `.pi/` 问题当成产品 candidate P1 去修。

项目开发过程中，`.pi/` / harness 治理层问题不得被擅自修改。`.pi/`、harness-flow、extensions、skills、prompts、settings、session handoff/review tooling 都属于治理层；发现问题时默认单独记录为 `governance maintenance issue` 或 `review limitation`，不进入当前产品 candidate，也不阻塞当前产品验收，除非它让必要门禁完全无法成立。只要不直接阻断产品开发或验收判断，就继续当前产品 task / Round；不自动修 harness，不重复 reload / re-review 来修治理工具。只有严重恶性 bug 导致项目无法继续，并且 Owner 明确授权后，才允许修改 `.pi/` / harness 相关文件；即便严重阻断，也必须作为单独 governance maintenance 记录，不能混入产品 Round / task candidate。

严重阻断例子包括：无法生成任何 review evidence、无法保护 candidate immutability、工具会错误修改项目文件、handoff / review gate 完全不可用。

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
