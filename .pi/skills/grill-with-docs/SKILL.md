---
name: grill-with-docs
description: Stress-test a plan or design against the repo's current contract and evidence. Invoke when a repo already exists and the agent should grill against AGENTS, intake, plans, work logs, or related docs.
---

# Grill With Docs

Interview me relentlessly about every aspect of this plan until we reach a shared understanding.

Walk down each branch of the design tree, resolving dependencies between decisions one by one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the repo, explore the repo instead.

## Domain Awareness

When you explore the repo, anchor the grilling against the current project-local baseline:

1. `AGENTS.md`
2. `docs/project-intake/`
3. `operations/planning/`
4. `operations/work_logs/`
5. `operations/reviews/`
6. `.pi/prompt-templates/`
7. any existing specs, plans, or contract docs relevant to the request

## Use This When

- the user already has a repo, plan, design, or contract draft
- the route decision should be pressure-tested against existing project language
- implementation would be expensive to undo if the framing is wrong
- a request touches contract, bootstrap, portability, workflow, or evidence expectations

## During The Session

- Call out conflicts between the current proposal and the repo's documented contract.
- Sharpen vague language into terms the repo can actually use.
- Check whether existing intake, plans, or work logs already answer a question before asking the user.
- Suggest whether a decision belongs only in the conversation, in a refreshed plan, or in another durable artifact.

## Output

Finish with:

1. the clarified understanding
2. the documented facts you anchored against
3. the recommended next route:
   - `direct-execute`
   - `plan`
   - `spec-then-plan`
   - `review-only`
   - `needs-extension`
4. which project-local docs should be refreshed, if any

## Boundaries

- Do not assume every grilling session must write new files.
- Do not create heavyweight docs if the request can remain on the simple path.
- Do not recommend subagents, MCP, or packages unless the current repo evidence shows a real boundary or capability gap.
