# R1 G4 AdaLN Correction Preflight Review Prompt

You are an independent reviewer in a spawned PI process. Read only; do not edit or execute generation.

The initial Owner-authorized `G4-TP4Q` passed NCCL/routing but failed during duplicated transformer CPU staging: 230 GiB abort triggered, observed peak 235.87 GiB, no request. Review the only same-topology correction `G4-TP4Q-adaln`.

Read:

- `AGENTS.md`
- `Harness_manual.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/planning/r1-h3-feasibility-matrix.md`
- `operations/reviews/2026-08-21-r1-feasibility-report.md`
- `operations/reviews/2026-08-21-r1-g4-preflight-review-1.md`
- `operations/reviews/2026-08-21-r1-g4-preflight-review-2.md`
- `operations/reviews/2026-08-21-r1-g4-preflight-review-final.md`
- `operations/reviews/r1-attempt-manifest.json`
- `operations/work_logs/2026-08-21-r1-h3-feasibility.md`
- `scripts/run_r1_h3_attempt.py`
- `scripts/verify_r1.py`
- `scripts/test_r1_hardening.py`
- `var/logs/r1-feasibility/g4-adaln-preflight-verify.txt`
- `var/outputs/r1-feasibility/G4-TP4Q/metadata.json`
- `var/outputs/r1-feasibility/G4-TP4Q/server.log`
- `var/outputs/r1-feasibility/G4-TP4Q/resources.csv`
- `var/outputs/r1-feasibility/G4-TP4Q/post-stop-gpu-snapshot.json`
- `var/cache/sglang-src/python/sglang/multimodal_gen/runtime/loader/component_loaders/transformer_loader.py`
- `var/cache/sglang-src/python/sglang/multimodal_gen/runtime/models/dits/minimax_h3.py`
- `var/cache/sglang-src/python/sglang/multimodal_gen/runtime/server_args/server_args.py`

Check:

1. Initial G4 hard-line breach and no-generation result are honest.
2. AdaLN online is official unmodified installed-source behavior, valid with TP4/current safetensors/kitchen_int8, and excludes AdaLN weights from normal model load rather than approximating/caching a different model.
3. Exact contract changes only `--minimax-h3-adaln-online true`, output ID, and safer 220 GiB abort; all model/request/backend/topology/provenance/environment controls remain pinned.
4. The online rebuild's TP-sharded checkpoint reads and output semantics are sufficient to justify one bounded attempt, while quality equivalence remains something the output comparison must verify.
5. Session-wide process cleanup and post-stop GPU checks are now fail-closed.
6. No additional correction will be auto-created if this fails.
7. Any P0/P1 required before execution.

Output:

- `Review mode=spawned_pi_process`
- Findings grouped P0/P1/P2
- counts
- Decision exactly `safe_to_execute` or `changes_required`

P0/P1 must be zero for `safe_to_execute`. This is preflight only.
