---
name: governance-loop-entry
description: Start or resume the minimal governance loop for an external project. Use for intake, planning, closeout, portability checks, and lightweight handoff updates.
---

# Governance Loop Entry

## Purpose

Use this skill when `MiniMax H3 Workflow Studio` needs a PI-first governance entrypoint.

This skill is intentionally narrow. It starts with lightweight routing, then expands only when needed. It helps the operator:

- capture intake
- decide whether a plan is needed
- summarize validation
- close out a round
- record portability notes

It does not implement project business logic, runtime adapters, or heavy scaffolding.

Default stance:

- native `Pi` first
- simple path first
- upgrade later

## Read First

1. `AGENTS.md`
2. `.pi/agents/README.md`
3. `.pi/prompt-templates/governance-loop.md`

## Baseline Companion Skills

This starter ships with these optional baseline skills:

- `grill-me`
  - use when the request is still fuzzy and there is no stable doc baseline yet
- `grill-with-docs`
  - use when the repo already has contracts, intake, plans, or other docs you should grill against
- `grilling`
  - use when the next route is unclear and you need to decide between simple path, `Plan`, `Spec`, review-only, or `Needs-extension`

## Workflow

1. Fixed gate
   - capture goal, source of truth, entrypoints, constraints, outputs
   - use at most one discovery round before making a routing decision
2. Route
   - `trivial`: execute directly and keep the response short
   - `grill-first`: use `grill-me`, `grill-with-docs`, or `grilling` only when the route is still unstable
   - `plan`: create or refresh a plan before implementation
   - `needs-extension`: stop at the boundary and note the missing package, extension, MCP, or specialist capability
3. Execute
   - keep changes minimal and aligned to the current request
4. Verify
   - record what was checked and what remains unverified
5. Closeout
   - summarize changed files, results, portability notes, and next actions

Do not treat planner-coder-reviewer style orchestration as the default path.
Only upgrade into a heavier workflow when complexity, risk, or handoff needs clearly justify it.

## Trigger Matrix

- stay on the simple path when the task is bounded and one discovery round settles the facts
- use `grill-me` when the user has an idea but the design boundary is not stable yet
- use `grill-with-docs` when a plan or proposal should be challenged against the current repo contract
- use `grilling` when you need a route decision:
  - stay simple
  - enter `Plan`
  - enter `Spec` then `Plan`
  - ask for review-only
  - stop at `Needs-extension`
- recommend subagents, MCP, or packages only when the current task exposes a real capability boundary

## Durable Evidence

For this starter project, durable records are project-local by default. Prefer these locations:

- `docs/project-intake/`
- `operations/planning/`
- `operations/work_logs/`
- `operations/reviews/`

These paths refer to this project's own repository, not the Workspace root.

Do not create durable evidence by default for `trivial` tasks.

Create or refresh records only when the task:

- enters `Plan`
- spans multiple rounds or needs handoff
- changes contract, bootstrap behavior, or portability assumptions
- needs a formal review trail

If the project is only `bootstrap-ready`, record that state clearly.
Only describe the project as `runtime-ready` when `pi` and provider/auth are also ready.

## Boundaries

- Do not add business-specific logic here.
- Do not create a multi-platform runtime layer here.
- Do not hardcode host absolute paths in committed files.
- Prefer repo-relative paths and small, reviewable changes.
- Do not force a default planner-coder-reviewer loop.
- Treat `graphify` as optional discovery, not an automatic post-process.
