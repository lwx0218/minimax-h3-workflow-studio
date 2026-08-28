# Pi Handoff — MiniMax H3 Studio Rebaseline

## Use

Paste the prompt below into a clean Pi session opened at the repository root. Attach or place the five files from this rebaseline package at their indicated repository paths before asking Pi to act.

This handoff intentionally makes the first session documentation-only. Do not combine rebaseline and ComfyUI installation in one session or commit.

## Repository Paths For This Package

```text
CONTEXT.md
docs/adr/0001-use-comfyui-as-studio-foundation.md
operations/planning/rebaseline-plan-v1.md
operations/planning/orchestration-v1.md
operations/handoffs/pi-rebaseline-handoff.md
```

## Prompt For Pi

```text
You are resuming MiniMax H3 Studio after an Owner-approved architecture rebaseline.

Repository:
https://github.com/lwx0218/minimax-h3-workflow-studio

Audited remote main at handoff creation:
b532a55f4549a2177ecd95237a4f3510cfb0aec5

This session has exactly one goal: commit the new source-of-truth baseline. Do not install ComfyUI, download weights, run GPU experiments, or implement product code.

Owner-approved decisions:
1. The product is ComfyUI-first. Pinned upstream ComfyUI backend and frontend provide the authoritative graph, node, queue, and execution semantics.
2. The MVP uses native ComfyUI workflow/API formats. Do not create an independent WorkflowDocument, Node Registry, DAG Executor, application FIFO queue, or custom canvas.
3. The common user path is Guided Mode/App Mode; the full ComfyUI canvas remains available for advanced work.
4. Multi-GPU MVP means at least two isolated ComfyUI Workers can execute independent Runs concurrently. All five A5000s must be usable over queued work subject to measured safe concurrency.
5. Single-request TP/Ulysses is a bounded later experiment and does not block the functional product.
6. The historical C3 attempt remains a valid feasible-with-constraints SGLang probe, but its approximately 30.6-minute route is not the interactive product baseline.
7. The delivery plan has four named checkpoints: Baseline Reset, Runtime Decision, Single-Worker Product, and Multi-Worker MVP.
8. Runtime Decision will validate an optimized ComfyUI H3 path on A5000 and disposition SwarmUI versus a thin project Control Plane.
9. Backend CLI/API generation is technical evidence only. Functional MVP is accepted only when a user submits through Guided Mode or Advanced Canvas, observes execution, and receives a playable video with stereo audio.

Read fully, in this order:
- CONTEXT.md
- docs/adr/0001-use-comfyui-as-studio-foundation.md
- operations/planning/rebaseline-plan-v1.md
- operations/planning/orchestration-v1.md
- operations/handoffs/pi-rebaseline-handoff.md

Then inspect, do not blindly trust, the existing:
- README.md
- AGENTS.md
- Harness_manual.md
- docs/project-intake/minimax-h3-workflow.md
- docs/specs/mvp-v0.md
- docs/architecture/architecture-v0.md
- docs/development/process.md
- operations/planning/initialization-plan.md
- latest R1 work log, feasibility report, owner-gate review, and attempt manifest

Execution contract for this session:

1. Preflight
   - Print current branch, HEAD, and concise worktree state.
   - If HEAD differs from the audited SHA, inspect intervening commits and reconcile without discarding user work.
   - Confirm the five rebaseline files are present and internally consistent.

2. Rebaseline existing normative documents
   - Update README current status: historical R1 is accepted / feasible_with_constraints; Baseline Reset is current; Runtime Decision is next.
   - Update intake, MVP spec, architecture, and the Master Plan/Checkpoint Ledger (`operations/planning/initialization-plan.md`) so future implementation follows ComfyUI-first architecture.
   - Update AGENTS.md and Harness_manual.md read order and session routing.
   - Mark incompatible historical future-plan clauses SUPERSEDED with a direct link to operations/planning/rebaseline-plan-v1.md.
   - Preserve old R1 evidence and chronology. Do not delete or rewrite experiment results.
   - Replace the old R2-R7 ledger with the four named checkpoints. Do not preserve seven rounds under new names.

3. Anti-drift mechanical checks
   - Search every normative Markdown file for active instructions to build WorkflowDocument, Node Registry, ExecutionPlan, DAG Executor, frontend canvas, single-concurrency FIFO, or to block Runtime Decision on four-GPU TP success.
   - Historical evidence may mention these terms. Active future instructions may not contradict the new plan.
   - Search for statements that describe ComfyUI as only a visual reference or optional fallback and correct normative occurrences.
   - Check that Replica Execution and Single-Request Multi-GPU are defined separately.
   - Check that no normative document treats backend-only generation as final MVP acceptance.
   - Check that all source-of-truth links resolve within the repository.

4. Verification and review
   - Add or update a lightweight documentation verifier if existing verification cannot detect source-of-truth conflicts.
   - Run documentation/link/consistency checks and existing safe non-GPU validation.
   - Run one independent Class-A documentation review against the Owner decisions above.
   - Fix every P0/P1 finding inside this session and rerun only the affected checks.
   - Keep review artifacts concise; do not reproduce full prompts or documents.

5. Commit and post-check
   - Update the Rebaseline ledger/work log with actual evidence.
   - Create one scoped checkpoint commit, suggested message:
     docs: rebaseline H3 Studio on ComfyUI foundation
   - Run fast post-commit checks.
   - Mark Rebaseline accepted only at the successful committed HEAD.
   - Do not begin Runtime Decision in this session.

Required final response:
- outcome and new source-of-truth order;
- changed files;
- every old clause/document marked superseded;
- verification commands and results;
- review findings and dispositions;
- commit SHA and clean/dirty worktree state;
- exact prompt for a fresh Runtime Decision session.

Stop for the Owner only if the repository has newer changes that materially conflict with these approved decisions, or if preserving existing user work makes a safe rebaseline impossible. Ordinary documentation conflicts are yours to resolve using the precedence above.
```

## Expected First-Session Outcome

Pi should return one documentation checkpoint and stop. The correct next state is:

```text
Baseline Reset: accepted
Historical R1: accepted / feasible_with_constraints
Runtime Decision: next
Product code: not started in the rebaseline commit
ComfyUI/model downloads: not started in the rebaseline session
```

If Pi begins building an independent contract/frontend, installs runtime dependencies before committing the rebaseline, preserves the old seven-round structure, or continues to call R1 blocked on TP4, stop that session and reissue this handoff.

## Runtime Decision Session Seed

Pi must generate the final Runtime Decision prompt from the committed repository. It should preserve these minimum instructions:

```text
Execute only Runtime Decision from operations/planning/rebaseline-plan-v1.md.
First run the Definition of Ready and record exact target-host topology, disk, RAM, GPU, source, runtime, and model-asset identities. Run one bounded A5000 ComfyUI H3 primary profile with cold/warm evidence and at most one correction, then disposition the SwarmUI controller spike. Do not build Guided Mode, a Control Plane, or multi-worker product code in Runtime Decision. Do not revive the independent WorkflowDocument or canvas plan. Complete verification, risk-proportional review, work log, checkpoint commit, and post-commit check before marking Runtime Decision accepted.
```
