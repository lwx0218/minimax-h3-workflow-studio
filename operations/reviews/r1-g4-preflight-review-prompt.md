# R1 Four-GPU Preflight Independent Review Prompt

You are an independent reviewer in a spawned PI process. Read only; do not edit or run generation.

Review whether the Owner-authorized `G4-TP4Q` launch is bounded and safe after valid single-card C3. This is a 4-GPU output-rate/resource/quality baseline, not a backend expansion.

Read:

- `AGENTS.md`
- `Harness_manual.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/planning/r1-h3-feasibility-matrix.md`
- `operations/planning/r1-external-reference-assessment.md`
- `operations/reviews/2026-08-21-r1-feasibility-report.md`
- `operations/reviews/2026-08-21-r1-c3-result-review.md`
- `operations/reviews/2026-08-21-r1-g4-preflight-review-1.md`
- `operations/reviews/2026-08-21-r1-g4-preflight-review-2.md`
- `operations/reviews/r1-attempt-manifest.json`
- `operations/work_logs/2026-08-21-r1-h3-feasibility.md`
- `scripts/run_r1_h3_attempt.py`
- `scripts/verify_r1.py`
- `scripts/test_r1_hardening.py`
- `var/logs/r1-feasibility/g4-preflight-verify-3.txt`
- `var/outputs/r1-feasibility/G4-nccl-smoke/preflight.txt`
- `var/outputs/r1-feasibility/G4-nccl-smoke/world2.status.txt`
- `var/outputs/r1-feasibility/G4-nccl-smoke/world2.log`
- `var/outputs/r1-feasibility/G4-nccl-smoke/world2-cumem-off.status.txt`
- `var/outputs/r1-feasibility/G4-nccl-smoke/world2-cumem-off.log`
- `var/outputs/r1-feasibility/G4-nccl-smoke/world2-p2p-off.status.txt`
- `var/outputs/r1-feasibility/G4-nccl-smoke/world2-p2p-off.log`
- `var/outputs/r1-feasibility/G4-nccl-smoke/world4-p2p-off.status.txt`
- `var/outputs/r1-feasibility/G4-nccl-smoke/world4-p2p-off.log`
- `var/outputs/r1-feasibility/C3-owner-exception/metadata.json`

Check:

1. Owner authorization and 4-of-5/legal TP4×U1 topology are explicit.
2. Existing lock 2 only; no new weights/backend/source patch/system modification.
3. `NCCL_P2P_DISABLE=1` is justified by smoke evidence and exact launch environment, with degraded scaling risk disclosed.
4. `kitchen_int8` + TP4 + encoder fold is not known-invalid in the installed unmodified SGLang source; if unsupported, require fail-fast qualification rather than generation.
5. 230 GiB early abort / 235 GiB hard line, monitor fail-closed, 3600 s load/generation bounds and output/tool paths remain enforced.
6. The exact launch cannot overwrite C3 or drift to TP2/U2, lossless, another model, reduced resolution, approximate sampler/cache, or fifth GPU.
7. One fixed probe can provide a first-output rate and quality comparator against C3 without claiming warm throughput/stability.
8. Any required pre-launch fixes.

Output:

- `Review mode=spawned_pi_process`
- Findings grouped P0/P1/P2
- counts
- Decision exactly `safe_to_execute` or `changes_required`

P0/P1 must be zero for `safe_to_execute`. This is preflight only, not R1 acceptance.
