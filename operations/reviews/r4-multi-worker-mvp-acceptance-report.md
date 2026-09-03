# R4 Multi-Worker MVP Acceptance Report

Status: accepted candidate to commit; final review passed, pending scoped checkpoint commit, post-commit verify and final Owner acceptance.

## Product acceptance summary

| Requirement | Candidate result | Evidence |
|---|---|---|
| Guided Mode submission/status/artifact retrieval | PASS from R3 and retained in R4 Worker Pool product surface | R3 work log; R4 `/api/runs` records and concurrent E2E |
| Advanced Canvas uses pinned ComfyUI frontend | PASS; each Worker exposes full ComfyUI frontend, no fork/custom canvas | `config/runtime-lock.json`; `docs/operations/r4-multi-worker-mvp.md` |
| T2VA and FL2VA valid frontend Runs | PASS from R3 accepted product E2E | `operations/work_logs/2026-09-02-r3-single-worker-product.md` |
| Two independent concurrent Worker Runs | PASS | `var/logs/r4-multi-worker-mvp/concurrent-e2e-result.json` |
| Five A5000 Worker Pool discovery | PASS | `var/logs/r4-multi-worker-mvp/five-worker-discovery.json` |
| Run traceability | PASS | R4 Run records under ignored `var/h3-studio/runs/`; `scripts/verify_r4_no_gpu.py` |
| Cancel/failure/recovery/cleanup boundary | PASS to documented local boundary | `docs/operations/r4-multi-worker-mvp.md`; no-GPU fail-closed/recovery/cancel tests; cleanup evidence |
| Draft/Balanced/Final profile evidence | PASS candidate matrix | `var/logs/r4-multi-worker-mvp/profile-matrix-result.json` |
| Security/default trust boundary | PASS | local bind; approved node/runtime manifests; no arbitrary node market |
| Git runtime boundary | PASS candidate | `.gitignore`; runtime evidence remains under ignored `var/` |
| License inventory | PASS candidate | `docs/operations/license-inventory.md` |
| Operator docs | PASS candidate | `docs/operations/r4-multi-worker-mvp.md`; README updates |

## Key R4 target-host results

Two concurrent Guided/API product submissions completed valid media on distinct Workers with overlap:

| Run | Worker | Status | Created→completed | Media gate |
|---|---|---:|---:|---|
| `run-e55395560754` | `worker-gpu0` / GPU 0 | completed | 286 s | PASS: H.264 video, AAC stereo audio, 864×480, 124 frames, full decode, no black/silence |
| `run-f8b8b9c802d4` | `worker-gpu1` / GPU 1 | completed | 281 s | PASS: H.264 video, AAC stereo audio, 864×480, 124 frames, full decode, no black/silence |

Concurrent resource peaks: host used 96.776 GiB; GPU0 22,855 MiB; GPU1 22,855 MiB; peak temperatures GPU0 71°C and GPU1 60°C. Evidence: `var/logs/r4-multi-worker-mvp/concurrent-e2e-result-monitor.json`.

Five Worker discovery:

- `worker-gpu0`..`worker-gpu4` healthy on `127.0.0.1:30211`..`:30215`.
- `safe_concurrent_runs=2`.
- Host memory at discovery: total 251.536 GiB, used 14.784 GiB, available 236.752 GiB.

Profile matrix, single Worker sequential product submissions:

| Profile | Sigma points | Run | Wall seconds | Peak host/GPU0 memory | Media gate | Disclosure |
|---|---:|---|---:|---:|---|---|
| `draft-r4-a5000` | 9 | `run-4cb17b083535` | 170.293 | 56.263 GiB / 22,855 MiB | PASS | pruned/INT8/quantized, fewer-step approximation, not lossless/reference |
| `balanced-r2-a5000` | 21 | `run-cabfc1272c47` | 260.540 | 55.630 GiB / 22,163 MiB | PASS | pruned/INT8/quantized, R2/R3 proven route |
| `final-r4-a5000` | 25 | `run-50cb15e708e8` | 295.465 | 52.502 GiB / 22,163 MiB | PASS | higher-step quantized/pruned candidate, not lossless/reference |

Profile evidence: `var/logs/r4-multi-worker-mvp/profile-matrix-result-monitor.json`.

## Cleanup evidence

After two-Worker, five-Worker and profile validations:

- `nvidia-smi --query-compute-apps=...` produced no remaining compute rows.
- `ss` showed ports `30210`..`30215` closed.
- Launched PIDs were limited to R4 wrapper/Studio/ComfyUI PIDs recorded under ignored `var/logs/r4-multi-worker-mvp/`.

## Known limits and P2 dispositions

- Five simultaneous H3 generations are not claimed. The MVP evidence supports all five Workers addressable with active H3 concurrency capped at two by measured host RAM safety.
- Draft and Final are R4 candidate profiles at the same 864×480/5s geometry. Final is not a non-quantized/reference route and must not be described as lossless.
- Cancellation uses assigned-Worker ComfyUI `/interrupt` for active Studio Runs only; terminal Run cancel is a no-op, and exact mid-generation cancellation latency remains bounded by ComfyUI behavior.
- This is local single-user only; no auth, public deployment, quotas or multi-tenancy are included.

## Anti-drift conclusion

The R4 candidate reuses ComfyUI graph/execution/queue semantics, keeps the Control Plane as Worker/Run coordination only, does not introduce WorkflowDocument/DAG Executor/Node Registry/custom canvas, and keeps Replica Execution separate from Single-Request Multi-GPU Track X. Final review verdict: PASS, P0=0, P1=0, P2=3 disposition accepted.
