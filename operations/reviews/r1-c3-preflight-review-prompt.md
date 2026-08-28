# R1 C3 Preflight Independent Review Prompt

You are an independent reviewer in a spawned PI process. Read only; do not edit files and do not run generation.

Review the Owner-authorized corrected single-card C3 preflight. The prior R1 final review required two P2 hardening changes before any new attempt. Determine whether it is safe to execute one bounded C3.

Read:

- `AGENTS.md`
- `Harness_manual.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/planning/r1-h3-feasibility-matrix.md`
- `operations/planning/r1-external-reference-assessment.md`
- `operations/reviews/2026-08-21-r1-independent-review-final.md`
- `operations/reviews/2026-08-21-r1-c3-preflight-review-1.md`
- `operations/reviews/2026-08-21-r1-feasibility-report.md`
- `operations/reviews/r1-attempt-manifest.json`
- `operations/work_logs/2026-08-21-r1-h3-feasibility.md`
- `scripts/run_r1_h3_attempt.py`
- `scripts/verify_r1.py`
- `scripts/test_r1_hardening.py`
- `var/logs/r1-feasibility/c3-hardening-verify-2.txt`
- `var/outputs/r1-feasibility/C2/metadata.json`
- `var/outputs/r1-feasibility/C2/status.ndjson`

Check specifically:

1. Owner authorization is recorded without rewriting historical slots.
2. Manifest ID uniqueness, exact argv checks and request prompt content re-hash are real, not just documented.
3. Resource monitoring now fails closed on sampling failure and cannot silently mark a run successful.
4. Host abort threshold remains 230 GiB below the 235 GiB hard line.
5. C3 can be limited to existing lock 2, one GPU, official kitchen_int8, fixed probe, exact PATH and compliant output path.
6. No external reference has silently expanded C3 to new weights/backend/approximate acceleration.
7. Existing evidence and Git/runtime boundaries remain honest.

Output one report with:

- `Review mode=spawned_pi_process`
- Findings grouped P0/P1/P2
- P0/P1 counts
- Decision exactly `safe_to_execute` or `changes_required`
- Required fixes before generation, if any

P0/P1 must be zero for `safe_to_execute`. Do not treat this preflight as R1 acceptance.
