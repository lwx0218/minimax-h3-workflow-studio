---
name: grilling
description: Decide the correct workflow route through a bounded blocking-decision interview. Use when it is unclear whether to direct-execute, Plan, Spec then Plan, review-only, or stop at Needs-extension.
---

# Grilling

Use this skill to settle the route, not to interrogate every design branch.

## Route Outcomes

- `direct-execute`
- `plan`
- `spec-then-plan`
- `review-only`
- `needs-extension`

## Interview Contract

- default maximum 3 discovery rounds
- 3–5 related blocking decisions per round
- target maximum 12–15 blocking decisions total
- recommended default for every decision
- allow `accept recommended defaults`; this resolves discovery decisions but never approves a durable Plan
- infer repository facts rather than asking
- ask only when the answer changes scope/acceptance, architecture/data ownership, or a hard-to-reverse/high-risk choice
- assume or defer non-blocking details
- budget exhaustion with blockers requires explicit Owner choice: enter `deep-discovery` or stop/mark blocked

End every response with:

- Resolved
- Assumed
- Blocking
- Deferred
- Question budget remaining

## Routing Heuristics

- `direct-execute`: approved baseline, bounded low-risk request, clear validation
- `plan`: cross-file, contract, portability, handoff, or explicit verification needs
- `spec-then-plan`: requirement boundary remains unstable
- `review-only`: findings requested before implementation
- `needs-extension`: browser/external system/missing package/specialist capability is genuinely required

Stop when blockers in scope, architecture, and acceptance are resolved and all other uncertainty is assumed/deferred.

## Greenfield No-Write Boundary

In `00-orchestration` before Plan approval, return route and Plan Preview in chat only. Do not edit code/config or create Plan, domain records, work log, or review artifacts.

## Output

1. settled goal
2. key decisions and unresolved blockers
3. resolved/assumed/deferred items
4. selected route and why
5. capability gap, if real
6. next human control gate and remaining budget

## Boundaries

- no unbounded one-question-at-a-time loop
- no implementation before route/approval is clear
- no automatic deep-discovery
- no default subagent/MCP/package recommendation
