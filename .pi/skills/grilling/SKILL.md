---
name: grilling
description: Stress-test a plan or design one decision at a time, then recommend the right route. Invoke when the next step is unclear or the agent must decide whether to stay simple or upgrade workflow.
---

# Grilling

Interview the user relentlessly about every aspect of this request until you reach a shared understanding.

Walk down each branch of the decision tree, resolving dependencies between decisions one by one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the repo, explore the repo instead.

## Purpose

Use this skill to decide whether the request should:

- stay on the native `Pi` simple path
- enter `Plan`
- enter `Spec` then `Plan`
- request a review-only pass
- stop at `Needs-extension`

This skill is a routing aid. It does not make `Plan`, subagent work, MCP use, or package installation the default.

## Output

When the grilling is done, summarize:

1. the settled goal
2. the key decisions and unresolved edges
3. the recommended route:
   - `direct-execute`
   - `plan`
   - `spec-then-plan`
   - `review-only`
   - `needs-extension`
4. whether there is a capability gap:
   - skill
   - MCP
   - package / extension
   - specialist review

## Routing Heuristics

- Prefer `direct-execute` when the task is bounded, low-risk, and can be settled in conversation plus one discovery round.
- Prefer `plan` when the task is cross-file, contract-sensitive, portability-sensitive, or needs explicit verification.
- Prefer `spec-then-plan` when the goal is clear but the requirement boundary is still unstable.
- Prefer `review-only` when the user wants findings before implementation.
- Prefer `needs-extension` when the task depends on browser automation, external systems, missing packages, MCP tools, or specialist capability that the current starter does not already provide.

## Boundaries

- Do not jump into implementation before the route is clear.
- Do not create a long plan if the request can remain on the simple path.
- Do not recommend subagents or MCP by default; recommend them only when the dependency is real.
