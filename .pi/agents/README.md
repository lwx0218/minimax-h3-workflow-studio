# Agents

这个目录只保留最小 agent 说明，不预置重型角色矩阵。

- 人类从项目根 `Harness_manual.md` 进入
- agent 以项目根 `AGENTS.md` 为执行合同
- greenfield/no-baseline 的首 session 使用 `00-orchestration`，确认 Plan 前保持 no-write
- existing approved baseline 的 bounded task 继续走 `Gate -> Route` simple path

启动/路由资源：

- `/project-kickoff`：首 session bounded discovery、完整 Plan Preview、viability/change 问题；随后用 `harness_request_plan_approval` 得到结构化 Owner decision，接受 discovery defaults 不等于批准 Plan
- `harness_offer_session_handoff`：approved Plan 持久化后验证 Round/session，并在一次 confirmation 后创建 parent-linked session、命名和提交 prompt；`/session-handoff` 始终是 manual fallback
- `/governance-loop`：已有 baseline 的 later bounded task
- `grill-*`：route 不稳定时按 distinct trigger 启用，共享 bounded question budget
- `domain-modeling`：仅在 domain ambiguity material 时启用；approval 前 no-write，之后才 record

默认不要求 planner、coder、reviewer 全量出场。只有 fixed-round Plan 才要求每个 Round 由当前 Builder 自动调用 `harness_run_independent_review` 发起 capability-checked distinct read-only child Review、在原 Round Fix/Verify/Re-review P0/P1，并在全部 delivery 完成后执行 Final Integrated Independent Review。child 不写 artifact；Builder 留痕。simple path 仍保持轻量；`/new` 不是 Review。
