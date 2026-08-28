# R1 Owner Control-Gate Independent Review Prompt

You are an independent reviewer in a spawned PI process. Read only; do not edit or run generation.

Review the complete current R1 state after valid single-card C3 and failed/rejected 4-GPU paths. Decide whether evidence is honest, P0/P1 are dispositioned, and pausing for Owner route choice is correct.

Read:

- `AGENTS.md`
- `Harness_manual.md`
- `docs/specs/mvp-v0.md`
- `docs/architecture/architecture-v0.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/planning/r1-h3-feasibility-matrix.md`
- `operations/planning/r1-external-reference-assessment.md`
- `operations/reviews/review-checklist.md`
- `operations/reviews/2026-08-21-r1-feasibility-report.md`
- `operations/reviews/2026-08-21-r1-c3-preflight-review-final.md`
- `operations/reviews/2026-08-21-r1-c3-result-review.md`
- `operations/reviews/2026-08-21-r1-g4-preflight-review-1.md`
- `operations/reviews/2026-08-21-r1-g4-preflight-review-2.md`
- `operations/reviews/2026-08-21-r1-g4-preflight-review-final.md`
- `operations/reviews/2026-08-21-r1-g4-adaln-preflight-review.md`
- `operations/reviews/2026-08-21-r1-verification.md`
- `operations/reviews/r1-verification-output.txt`
- `operations/reviews/r1-attempt-manifest.json`
- `operations/work_logs/2026-08-21-r1-h3-feasibility.md`
- `scripts/run_r1_h3_attempt.py`
- `scripts/verify_r1.py`
- `scripts/verify_r1_media.py`
- `scripts/test_r1_hardening.py`
- `var/outputs/r1-feasibility/C3-owner-exception/metadata.json`
- `var/outputs/r1-feasibility/C3-owner-exception/independent-media-verification.json`
- `var/outputs/r1-feasibility/C3-owner-exception/post-stop-gpu-snapshot.json`
- `var/outputs/r1-feasibility/G4-TP4Q/metadata.json`
- `var/outputs/r1-feasibility/G4-TP4Q/server.log`
- `var/outputs/r1-feasibility/G4-TP4Q/post-stop-gpu-snapshot.json`

Check:

1. C3 legitimately supports `feasible_with_constraints` without overstating subjective quality.
2. G4 host hard-line breach/no-request outcome is explicit.
3. Known-invalid kitchen_int8 + AdaLN online correction was not executed and verifier rejects it outside `preflight_rejected` state.
4. All prior preflight/result P0/P1 findings are fixed or safely dispositioned.
5. External repository assessment distinguishes primary evidence/community claims and justifies no silent backend switch.
6. Owner options are technically meaningful, especially unquantized AdaLN-online versus ComfyUI/DiffSynth fallback versus defer/RAM.
7. Round must remain blocked/no acceptance commit/no R2 until Owner decision.
8. Any remaining P0/P1/P2.

Output:

- `Review mode=spawned_pi_process`
- Findings grouped P0/P1/P2
- counts
- Decision exactly `blocked_owner_decision` or `changes_required`
- concise recommendation

P0/P1 must be zero for `blocked_owner_decision`.
