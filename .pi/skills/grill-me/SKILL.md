---
name: grill-me
description: Interview the user relentlessly to sharpen a plan or design before building. Invoke when the request is still fuzzy, there is no stable repo/doc baseline yet, or the user asks to be grilled.
---

# Grill Me

Interview me relentlessly about every aspect of this plan until we reach a shared understanding.

Walk down each branch of the design tree, resolving dependencies between decisions one by one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the repo, explore the repo instead.

## Use This When

- the user has an idea but the boundary is still fuzzy
- there is not yet a stable plan, spec, or project-local evidence trail to anchor against
- you need to pressure-test assumptions before deciding whether to stay simple or upgrade workflow
- the user explicitly asks to be grilled

## Desired Outcome

By the end of the session, the user and the agent should share a working understanding of:

- the goal
- the source of truth
- the main constraints
- the risky or ambiguous branches
- the likely route:
  - stay simple
  - create a plan
  - create a spec first
  - stop at a capability boundary

## Boundaries

- Do not turn this into an implementation session.
- Do not ask multi-question walls; keep it one question at a time.
- Do not create durable evidence by default unless the route clearly upgrades into `Plan` or another recorded workflow.
