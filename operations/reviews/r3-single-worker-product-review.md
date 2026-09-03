# R3 Single-Worker Product Independent Review

Plan: operations/planning/rebaseline-plan-v1.md
Round: R3
Review role: per_round
Review decision: pass
Findings: P0=0 P1=0 P2=0
Candidate immutable: yes
Unresolved P0: 0
Unresolved P1: 0

- Plan: `operations/planning/rebaseline-plan-v1.md`
- Round: `R3`
- Checkpoint: `R3 — Single-Worker Product`
- Review role: `per_round`
- Review mode: `harness_run_independent_review` distinct read-only Pi child
- Review decision: `pass`
- Decision: `pass`
- Status: `passed`
- Candidate immutable: yes
- Unresolved P0: 0
- Unresolved P1: 0
- P0: 0
- P1: 0
- P2: 0

## Scope

Candidate scope:

- `h3_studio/`
- `config/`
- `workflows/`
- `scripts/prepare_r3_distribution.py`
- `scripts/start_r3_single_worker.py`
- `scripts/verify_r3_no_gpu.py`
- `scripts/run_r3_product_e2e.py`
- `docs/operations/r3-single-worker-product.md`
- `README.md`
- `.env.example`
- `Harness_manual.md`
- `operations/planning/rebaseline-plan-v1.md`
- `operations/planning/initialization-plan.md`
- `operations/work_logs/2026-09-02-r3-single-worker-product.md`

Environment scope: `.pi/settings.json` and `.pi/npm/` are non-candidate Pi Fleet capability dirtiness and are not staged for the R3 product commit.

## Review Summary

Final per-round re-review returned `pass` with P0=0, P1=0 and P2=0. Reviewer confirmed the candidate remains ComfyUI-first: Guided Mode submits native ComfyUI API prompts, Advanced Canvas remains the pinned ComfyUI frontend, Run/Artifact records are traceability metadata, and the candidate does not introduce a custom canvas, WorkflowDocument, DAG executor, node registry, or second graph runtime.

Limitations: read-only review; reviewer did not rerun commands, GPU jobs, media decode or modify files. Runtime/E2E evidence was assessed from the review bundle and work log rather than by inspecting ignored `var/` artifacts directly.

## Earlier Findings And Resolutions

An earlier per-round review pass produced three P2 findings; Builder fixed all three:

1. Stale `Harness_manual.md` status — fixed to show R2 accepted and R3 current/in-progress.
2. Start wrapper could leave Worker running on normal Studio exit — fixed with `finally` cleanup for the launched Worker process.
3. Advanced Canvas T2VA workflow note had stale geometry — fixed to `864×480/5s`.

A subsequent re-review produced two P1 and one P2; Builder fixed all three and reran regression before the final pass:

1. P1 host absolute model path in committed work log — fixed by replacing command examples with `$EXTERNAL_MINIMAX_H3_MODEL_ROOT`.
2. P1 sidecar manifest lacked hash and copied too broadly — fixed with deterministic FL2VA sidecar tree SHA-256 `c641032d2ee63183299e97f3ed1664f04fc630f03234cf0af8530a40c7f86144`, directory-hash validation, and manifest-declared sidecar copying only.
3. P2 dependency lock weak — fixed with `config/python-lock-r3.txt` and pip constraints usage in `scripts/prepare_r3_distribution.py`.

## Regression Verification After Fixes

```bash
python3 -m py_compile h3_studio/*.py scripts/prepare_r3_distribution.py scripts/start_r3_single_worker.py scripts/verify_r3_no_gpu.py scripts/run_r3_product_e2e.py
python3 scripts/verify_r3_no_gpu.py
H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT python3 scripts/prepare_r3_distribution.py --skip-install --compute-sha
H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT python3 scripts/prepare_r3_distribution.py
git diff --check
python3 scripts/verify_rebaseline_docs.py
```

Results: PASS. Committed-path absolute-host scan excluding `var/` and `.pi/` found no host-specific absolute path except the worktree `.git` pointer. Runtime cleanup from the real product E2E remained valid: R3-launched PIDs were killed, `nvidia-smi --query-compute-apps` produced no rows, and ports `30210`/`30211` were closed.

## Review Conclusion

R3 per-round review passes with no unresolved P0/P1/P2. Proceed to final integrated review / pre-commit closeout for R3.
