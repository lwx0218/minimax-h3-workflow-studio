# Work Log：R4 Multi-Worker MVP

- Date：2026-09-03
- Plan：`operations/planning/rebaseline-plan-v1.md`
- Round：`R4`
- Primary implementation session：`R4-multi-worker-mvp`
- Git baseline：`f4113dd` (`r3: accept single-worker product`)
- Checkpoint：`R4 — Multi-Worker MVP`
- Status：`accepted_candidate_to_commit`
- Route：Owner-authorized fixed checkpoint / Class A concurrency+GPU safety + Class B product

## Scope Boundary

Candidate scope:

- Extend the R3 thin Studio server into a Worker Pool Control Plane while keeping ComfyUI as the graph, queue and execution authority.
- Add stable Worker identity/GPU/port/output/tmp/log namespaces for five A5000 Workers.
- Add safe active-Run assignment, host RAM fail-closed behavior, per-Run Worker/Artifact correlation and startup recovery.
- Add R4 start/verification/E2E/profile scripts, operator docs, license inventory and final acceptance report.

Non-goals held: no Single-Request Multi-GPU MVP gate, no ComfyUI frontend fork, no custom canvas, no independent WorkflowDocument/DAG Executor/Node Registry, no arbitrary third-party node market, no public/multi-tenant deployment, no system driver/kernel/CUDA changes.

Environment scope: pre-existing local `.pi`/harness-flow/Pi Fleet dirtiness remains non-candidate and must not be staged. R4 runtime evidence, logs, outputs, media, venv and ComfyUI clones are under ignored `var/`.

## Rehydrate / DoR

- Branch / HEAD at start: `r4-multi-worker-mvp` at `f4113dd`.
- Worktree at start: clean product tree plus non-candidate `.pi` capability dirtiness.
- R3 accepted facts retained: Guided Mode + Advanced Canvas entry, single Worker ComfyUI product slice, T2VA/FL2VA workflow templates, Run/Artifact traceability.
- R2 accepted controller decision retained: `build_thin_control_plane`; SwarmUI not adopted.
- Model root used for R4 probes: `$H3_MODEL_ROOT` external model directory.
- Key FL2VA INT8 ConvRot safetensors revalidated: header OK (`header_len=108064`, `tensor_count=1039`), SHA-256 `4e464ae3d21ff81ef51efced3420cbf2d6139a5ec1ccc6f9793b43b158ebf738`.
- Host: 5 × NVIDIA RTX A5000, 24,564 MiB each; RAM 251 GiB; root filesystem about 1.4 TiB available; ports `30210`..`30215` initially closed.

## Implemented Candidate

- `config/worker-pool.json` defines five Workers:
  - `worker-gpu0`..`worker-gpu4`;
  - GPUs `0`..`4`;
  - ports `30211`..`30215`;
  - per-Worker output/tmp/log namespaces;
  - `safe_concurrent_runs=2`, `host_ram_abort_gib=230`, `host_ram_hard_gib=235`.
- `h3_studio/workers.py` adds thin Worker Pool coordination:
  - health discovery via ComfyUI `/system_stats`;
  - healthy-idle least-recent assignment;
  - in-memory reservation during concurrent submissions;
  - fail-closed `NoWorkerAvailable` when no Worker/safety slot/RAM is available or RAM status cannot be read;
  - host memory checks from `/proc/meminfo`, including abort and hard-line status;
  - strict WorkerSpec HTTP(S) URL/port validation;
  - stale active Run recovery on startup.
- `h3_studio/server.py` now:
  - exposes `/api/workers` and Worker Pool status in `/api/health`/`/api/config`;
  - assigns each Run to exactly one Worker before native ComfyUI prompt submission;
  - records Worker Pool identity in Run metadata;
  - routes progress WebSocket, cancel, history refresh and artifact proxy through the assigned Worker;
  - returns `503 no_worker_available` instead of queuing unsafe project-owned FIFO work;
  - cleans temporary multipart upload directories after request handling;
  - avoids interrupting a Worker when cancel is requested for an already terminal Run.
- `scripts/start_r4_worker_pool.py` starts selected/all isolated Workers and the Studio server, records PIDs/lifecycle evidence, handles SIGINT/SIGTERM cleanup and uses per-Worker output/tmp/log dirs.
- `scripts/verify_r4_no_gpu.py` validates five-Worker discovery shape, distinct assignment for two active Runs, safe-concurrency fail-closed, artifact correlation and release/reassignment without GPU.
- `scripts/run_r4_concurrent_e2e.py` submits two independent product Runs concurrently and validates media/artifacts with resource sampling.
- `scripts/run_r4_profile_matrix.py` runs Draft/Balanced/Final profile matrix through the product API with resource sampling.
- `config/generation-profiles.json` now includes Draft, Balanced and Final candidate profiles with explicit pruned/INT8/quantized disclosures and no lossless claim.
- `docs/operations/r4-multi-worker-mvp.md`, `docs/operations/license-inventory.md`, `.env.example`, `README.md`, `Harness_manual.md` and `operations/reviews/r4-multi-worker-mvp-acceptance-report.md` document R4 operation, recovery, license, packaging and acceptance evidence.

## Automated Verification

Fast checks passed:

```bash
python3 -m py_compile h3_studio/*.py scripts/prepare_r3_distribution.py scripts/start_r3_single_worker.py scripts/start_r4_worker_pool.py scripts/verify_r3_no_gpu.py scripts/verify_r4_no_gpu.py scripts/run_r3_product_e2e.py scripts/run_r4_concurrent_e2e.py scripts/run_r4_profile_matrix.py
python3 scripts/verify_r3_no_gpu.py
python3 scripts/verify_r4_no_gpu.py
python3 scripts/verify_rebaseline_docs.py
git diff --check
```

Asset validation passed:

```bash
H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT python3 scripts/prepare_r3_distribution.py --skip-install --compute-sha
H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT python3 scripts/prepare_r3_distribution.py
```

Runtime paths are ignored by `/var/*`; ffmpeg/ffprobe tools were symlinked under ignored `var/cache/tools/` from an existing local cache for media validation.

Final review hardening regression additionally passed:

```bash
python3 -m py_compile h3_studio/*.py scripts/verify_r4_no_gpu.py
python3 scripts/verify_r4_no_gpu.py
```

`verify_r4_no_gpu.py` now covers terminal/active cancellation scope, invalid WorkerSpec URL/port rejection and host-RAM-status-unavailable fail-closed behavior in addition to the original R4 no-GPU checks.

## Target-Host R4 Evidence

### Two concurrent independent Runs

Command path: `scripts/start_r4_worker_pool.py --workers worker-gpu0,worker-gpu1` plus `scripts/run_r4_concurrent_e2e.py`.

Raw ignored evidence:

- `var/logs/r4-multi-worker-mvp/concurrent-e2e-result-monitor.json`
- `var/logs/r4-multi-worker-mvp/workers-before-concurrent-monitor.json`
- `var/logs/r4-multi-worker-mvp/workers-after-concurrent-monitor.json`
- `var/logs/r4-multi-worker-mvp/compute-apps-after-two-worker-monitor.txt`
- `var/logs/r4-multi-worker-mvp/ports-after-two-worker-monitor.txt`

Results:

| Run | Worker | Status | Created→completed | Media gate |
|---|---|---:|---:|---|
| `run-e55395560754` | `worker-gpu0` / GPU 0 | completed | 286 s | PASS |
| `run-f8b8b9c802d4` | `worker-gpu1` / GPU 1 | completed | 281 s | PASS |

- Distinct Workers: PASS.
- Wall-clock overlap: PASS.
- Media validation: H.264 video, AAC stereo audio, 864×480, 124 frames, full decode, no black/silence detector hits for both Runs.
- Concurrent resource summary: host peak 96.776 GiB used; GPU0 peak 22,855 MiB / 71°C; GPU1 peak 22,855 MiB / 60°C.

### Five Worker discovery

Command path: `scripts/start_r4_worker_pool.py --workers all` then `/api/workers`.

Raw ignored evidence:

- `var/logs/r4-multi-worker-mvp/five-worker-discovery.json`
- `var/logs/r4-multi-worker-mvp/compute-apps-after-five-worker.txt`
- `var/logs/r4-multi-worker-mvp/ports-after-five-worker.txt`

Results:

- Worker count: 5.
- Healthy Workers: `worker-gpu0`, `worker-gpu1`, `worker-gpu2`, `worker-gpu3`, `worker-gpu4`.
- Safe active H3 concurrency: 2.
- Discovery-time host memory: total 251.536 GiB, used 14.784 GiB, available 236.752 GiB.

### Profile matrix

Command path: `scripts/start_r4_worker_pool.py --workers worker-gpu0` plus `scripts/run_r4_profile_matrix.py`.

Raw ignored evidence:

- `var/logs/r4-multi-worker-mvp/profile-matrix-result-monitor.json`
- `var/logs/r4-multi-worker-mvp/compute-apps-after-profile-monitor.txt`
- `var/logs/r4-multi-worker-mvp/ports-after-profile-monitor.txt`

Results:

| Profile | Run | Wall seconds | Peak host / GPU0 | Media gate |
|---|---|---:|---:|---|
| `draft-r4-a5000` | `run-4cb17b083535` | 170.293 | 56.263 GiB / 22,855 MiB | PASS |
| `balanced-r2-a5000` | `run-cabfc1272c47` | 260.540 | 55.630 GiB / 22,163 MiB | PASS |
| `final-r4-a5000` | `run-50cb15e708e8` | 295.465 | 52.502 GiB / 22,163 MiB | PASS |

Draft/Final are R4 candidate profiles at the same 864×480/5s MVP geometry. They remain pruned/INT8/quantized and are not reference/lossless quality claims.

## Cleanup / Git Boundary

- After two-Worker, five-Worker and profile validations, `nvidia-smi --query-compute-apps=...` produced no remaining compute rows.
- Ports `30210`..`30215` were closed after cleanup.
- Only R4 wrapper/Studio/ComfyUI PIDs recorded in ignored `var/logs/r4-multi-worker-mvp/` were terminated.
- Candidate Git scope excludes `.pi/` and all ignored `var/` runtime data.

## Review

Initial independent review session: `R4-multi-worker-review-subagent`; it returned a fail decision with P1 concerns around stale recovery/cleanup/safety handling and Advanced Canvas evidence clarity. Builder fixed stale recovery, temporary upload cleanup, SIGTERM handling, host hard-line status, and WorkerSpec URL/port validation, then requested re-review.

Owner clarified that the restarted worker must not open extra Fleet review sessions. Final scoped re-review was completed inside this R4 worker session. It confirmed the earlier P1/P2 fixes and added two small hardening fixes before pass: fail-closed when host RAM status is unavailable, and cancellation no-op for terminal Runs so a later request cannot interrupt an assigned Worker's unrelated current work. Regression `python3 scripts/verify_r4_no_gpu.py` now covers those cases.

Final review artifact: `operations/reviews/r4-multi-worker-mvp-review.md`; verdict `pass`, P0=0, P1=0, P2=3 disposition accepted.

## Anti-Drift Check

1. Reuses ComfyUI semantics: yes.
2. Introduces WorkflowDocument/DAG/node registry/queue/canvas: no.
3. Control Plane becoming graph executor: no; it only assigns native prompts and records operational Run/Artifact metadata.
4. Replica Execution vs Single-Request Multi-GPU conflated: no.
5. Optimization presented as reference/lossless: no.
6. Community claim used as target-host evidence: no.
7. Failed multi-GPU blocks R4: no; Track X remains separate.
8. Review proportional: yes; independent read-only review and re-review requested.
9. Superseded docs regain authority: no.

## Known Limits / P2 Candidates

- Five simultaneous H3 generations are not claimed; all five Workers are addressable/discoverable and active H3 concurrency is capped at two by RAM safety.
- Advanced Canvas direct ComfyUI submissions run on the selected Worker’s native ComfyUI queue; Studio Run records are produced for Guided/product API submissions through the Control Plane.
- Cancellation uses assigned-Worker ComfyUI `/interrupt`; precise mid-generation interrupt latency remains bounded by ComfyUI.
- R4 remains local single-user only with `127.0.0.1` default binding.

## Next

Run pre-commit gate, create scoped R4 checkpoint commit, run post-commit verify, then request final Owner acceptance. Do not push.
