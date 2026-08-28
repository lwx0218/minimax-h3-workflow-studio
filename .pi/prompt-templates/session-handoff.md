---
description: Generate a durable handoff for a new implementation session
argument-hint: "[R1-<delivery-slug>|build-<task-slug>]"
---

# New Session Handoff

Generate a handoff only after the Owner has confirmed the Plan and required durable evidence has been written.

For fixed-round delivery, verify that `${1:-R1-<delivery-slug>}` exactly matches the active Round's declared primary implementation session name. Do not invent a second acceptance unit. For a same-Round continuation, use the declared base plus `-cont-2` (incrementing as needed) and state that the Round ID and gate are unchanged.

The handoff must identify:

1. applicable `AGENTS.md`, README, architecture/spec contracts
2. approved Plan path, active Round ID, and current Ledger/task status
3. declared primary implementation session and whether this is a continuation
4. latest work log and review artifact, if any
5. one bounded delivery target and its non-goals
6. dependencies and Definition of Ready
7. expected change surfaces
8. unresolved findings, blockers, assumptions, and backlog
9. exact validation commands or strategy
10. required Independent Review mode, artifact path, and capability evidence
11. acceptance evidence and exact next control gate
12. blocked/rebaseline conditions and prohibition on scope expansion, Phase acceptance, or letter-suffixed Rounds without Owner approval

Output a copyable implementation prompt. When `harness-flow` is available, call `harness_offer_session_handoff` with only the approved Plan path, Round ID, and declared session name. The extension derives latest evidence and extracts the complete handoff only from the Ledger and matching owning-Round exact labels; it must validate Plan/Round/session and request one UI confirmation before parent-linked new/name/single prompt submission.

Always retain this manual fallback and tell the human to run it on cancel/capability failure:

```text
/session
/new
/name ${1:-R1-<delivery-slug>}
```

Use `/name build-<task-slug>` for non-fixed work. The copyable sequence remains supported even with project-local `harness-flow`. Do not claim the local extension is an npm/git/pi.dev package.

State explicitly:

- `Round` is the only acceptance-bearing unit; a continuation session remains in the active Round
- chat history is not the durable source of truth
- Bug/Fix/Review remains in the current task/Round
- the Builder automatically calls `harness_run_independent_review` after verification and re-reviews P0/P1 fixes; the child is non-interactive/no-session/strict read-only and the Builder writes durable evidence
- the last planned Round requires a separate Final Integrated Independent Review before its pre-commit gate
- no accepted claim before required review, acceptance commit, and post-commit verify
- `/new` creates a clean session but is not Independent Review
