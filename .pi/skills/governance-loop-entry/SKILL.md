---
name: governance-loop-entry
description: Start or resume the minimal governance loop, including greenfield kickoff, bounded planning, closeout, portability checks, and handoff. Use when a project needs routing or durable governance evidence.
---

# Governance Loop Entry

## Purpose

Provide a PI-first governance entrypoint for `MiniMax H3 Workflow Studio`. Start lightweight, expand only when complexity or the absence of an approved baseline requires it.

Default stance:

- native Pi first
- greenfield/no-baseline kickoff before implementation
- simple path after an approved baseline exists
- upgrade only when justified

## Read First

1. `AGENTS.md`
2. `Harness_manual.md`
3. `.pi/agents/README.md`
4. `.pi/prompt-templates/project-kickoff.md`
5. `.pi/prompt-templates/governance-loop.md`
6. `.pi/prompt-templates/session-handoff.md`

## Applicability Gate

- Greenfield or no approved baseline Plan:
  - use `00-orchestration` and the project-kickoff contract
  - remain planning-only until explicit Owner Plan confirmation
- Existing stable approved baseline plus a later bounded task:
  - use normal `Gate -> Route`
  - do not force kickoff, fixed rounds, Spec, or Plan when the simple path is sufficient

## Pre-Approval No-Write Boundary

Before the Owner confirms the greenfield Plan, you may read/infer/discuss and present a Plan Preview in chat.

You must not:

- modify business code or configuration
- create/update Plan, intake, `CONTEXT.md`, ADR, work log, review, or other project artifact
- install dependencies or run destructive/system actions
- start implementation or claim development progress

Bootstrap-created scaffold predates the conversation and does not authorize additional writes.

## Bounded Discovery Contract

When blockers require user decisions:

- maximum 3 discovery rounds by default
- each round groups 3–5 related blocking decisions
- target maximum 12–15 blocking decisions
- every decision includes a recommended default
- the Owner may answer `accept recommended defaults`
- infer facts from repository evidence instead of asking
- ask only if the answer changes scope/acceptance, architecture/data ownership, or a hard-to-reverse/high-risk choice
- move non-blocking uncertainty to assumptions or backlog
- after the budget, ask whether to enter `deep-discovery`; do not continue without explicit opt-in

Every discovery response ends with:

- Resolved
- Assumed
- Blocking
- Deferred
- Question budget remaining

Stop when all blocking scope, architecture, and acceptance decisions are resolved, while non-blocking uncertainty is assumed or deferred and validation/control gates are clear.

## Route

- `direct-execute`: clear bounded task with approved baseline
- `grill-first`: route remains unstable; select one applicable grilling skill
- `plan`: cross-file, contract, portability, handoff, risk, or validation requires durable planning
- `review-only`: inspect a candidate without implementation
- `needs-extension`: a real package/extension/specialist boundary blocks the task

Do not treat planner-coder-reviewer orchestration as the default.

## Optional Baseline Skills

- `grill-me`: fuzzy request without stable repository/doc baseline
- `grill-with-docs`: stress-test a substantive approved decision baseline or explicit contract conflict; bootstrap-only scaffold does not trigger it
- `grilling`: settle the workflow route
- `domain-modeling`: optional only for material domain-language/ownership ambiguity; no-write before Plan approval

All interview skills share the bounded discovery contract above.

## Plan Preview Terminal States And Confirmation

For a greenfield/no-baseline project, every orchestration turn ends in one state:

1. `blocking-decisions`: bounded decisions plus discovery budget state only
2. `ready-for-approval`: complete Plan Preview plus the mandatory viability/change/approval closeout
3. `approved-and-persisted`: approved evidence plus the proposed next session and durable-source-based handoff

When ready, end with:

```text
以上 Plan 是否可行？是否还有需要继续确认或修改的地方？

- 如需修改：直接说明修改点
- 如无其他问题：回复“确认计划”
- 确认后我将持久化 Plan，并生成下一开发 session 的名称和交接内容
```

Accepting recommended discovery defaults is not durable Plan approval. After a complete Preview, call `harness_request_plan_approval`; persist nothing unless it returns `approved`. `changes_requested` revises the Preview and `cancelled` writes nothing. If the extension is unavailable, Owner `确认计划` / equally explicit confirmation is the manual fallback. After approval, write only approved evidence and generate the session handoff; do not implement business work in `00-orchestration`.

## Later Implementation Session Or Existing-Baseline Execution

Plan confirmation inside `00-orchestration` authorizes only approved evidence persistence and handoff. It never authorizes business implementation in that session.

Execute/Verify/Closeout applies only when:

- a later named implementation session has loaded the approved Plan/handoff; or
- an existing approved-baseline task routed directly outside greenfield orchestration

Then:

- keep implementation minimal and aligned to the approved/bounded request
- run exact relevant checks
- record what passed, failed, or remains unverified
- summarize changed files, outcome, portability, and next control gate

## Optional Fixed-Round Delivery

Use fixed rounds only for complex, cross-session, high-risk, or formally accepted delivery. Never impose them on a clear simple-path task.

When active:

- `Round` is the sole acceptance-bearing unit; `Phase` may only be non-authoritative narrative grouping
- each Round declares in its owning section: Round ID, one primary implementation session name, independently reviewable delivery boundary, non-goals, dependencies/Definition of Ready, expected change surfaces, exact validation strategy, distinct per-Round/final-integrated artifact paths when applicable, Independent Review mode, acceptance evidence, exact next gate, blockers/assumptions, and blocked/rebaseline conditions
- a continuation such as `R1-<slug>-cont-2` remains in the same Round and cannot change its delivery or acceptance gate
- the current Builder automatically starts required per-Round Independent Review after automated verification
- P0/P1 remains in the Round through automatic Fix/Verify/Re-review; P2 receives a disposition
- after all planned delivery, the last Round runs a separate Final Integrated Independent Review before pre-commit acceptance; no hidden repair Round is created
- inability to establish capability/auth/read-only reviewer isolation is `blocked` or uses an approved distinct-human fallback

## Durable Evidence

Project-local by default:

- `docs/project-intake/`
- `operations/planning/`
- `operations/work_logs/`
- `operations/reviews/`

Create/refresh evidence only when the task enters Plan, crosses sessions, changes contract/bootstrap/portability, or needs formal review.

State `bootstrap-ready` versus `runtime-ready` accurately.

## Session Handoff And Review

After approved Plan persistence, read the fixed Round's declared primary implementation session name and call `harness_offer_session_handoff`. It validates durable Plan/Round/session metadata, shows the session/target/summary, requests one Owner confirmation, and on confirm creates a parent-linked session, names it, and submits the prompt once.

On cancel/capability failure, or if `harness-flow` is unavailable, generate `/session-handoff <declared-session-name>` and tell the human:

```text
/session
/new
/name <declared-session-name>
```

Use `/name build-<task-slug>` for non-fixed work. A continuation uses the same Round's base name plus `-cont-2`; it does not create another Round. Keep the copyable fallback and do not claim project-local `harness-flow` is a public package.

`/new` is not Independent Review. A gate labeled Independent Review requires the Builder to call `harness_run_independent_review` for a distinct non-interactive/no-session/strict read-only process after capability check, or use a distinct approved `human_review`. The child writes no artifact; the Builder captures the result. Fixed-round Builders start required review automatically rather than asking the Owner.

## Boundaries

- no business-specific logic in this skill
- no host absolute paths in committed files
- no automatic push
- no automatic deep-discovery
- no forced domain modeling or fixed-round workflow
