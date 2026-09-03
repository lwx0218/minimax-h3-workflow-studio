# R4 Multi-Worker MVP Operations

Status: R4 accepted candidate to commit; final review passed, pending scoped commit, post-commit verify and Owner final acceptance.

## Runtime shape

- Studio: `172.16.2.111:30210`
- Worker Pool config: `config/worker-pool.json`
- Workers: `worker-gpu0`..`worker-gpu4`, each an isolated ComfyUI service bound with `CUDA_VISIBLE_DEVICES=<gpu>` and ports `30211`..`30215`.
- Runtime root: ignored `var/runtimes/r3-single-worker-product/` (R3 pinned ComfyUI/RH distribution reused for R4).
- R4 logs/outputs/tmp: ignored `var/logs/r4-multi-worker-mvp/`, `var/outputs/r4-multi-worker-mvp/<worker-id>/`, `var/tmp/r4-multi-worker-mvp/<worker-id>/`.

The Control Plane only assigns native ComfyUI API prompts to healthy Workers and records Run/Artifact metadata. It does not implement a graph executor, node registry, ComfyUI replacement queue, or custom canvas.

## Prepare

```bash
export H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT
python3 scripts/verify_r4_no_gpu.py
python3 scripts/prepare_r3_distribution.py --compute-sha
python3 scripts/prepare_r3_distribution.py
```

The key FL2VA INT8 ConvRot asset must remain:

```text
MiniMax-H3-FL2VA-int8_convrot.safetensors
sha256=4e464ae3d21ff81ef51efced3420cbf2d6139a5ec1ccc6f9793b43b158ebf738
```

## Start

Start all five addressable Workers with the measured safe concurrency still enforced by the Studio Control Plane:

```bash
export H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT
python3 scripts/start_r4_worker_pool.py --workers all
```

For a two-Worker concurrency validation or reduced-memory operation:

```bash
python3 scripts/start_r4_worker_pool.py --workers worker-gpu0,worker-gpu1
```

Open `http://172.16.2.111:30210/`. Guided Mode submits to the Worker Pool with scheduling, safe-concurrency checks and Run traceability. Advanced Canvas opens the first healthy pinned ComfyUI frontend; direct Advanced Canvas submissions use that Worker's native ComfyUI queue and should be operated within the same documented safe-concurrency limit. Individual Worker frontends are available at `http://172.16.2.111:30211/` through `:30215/` when those Workers are launched.

## Safety limits

- Host RAM observed by `/proc/meminfo` is checked before assignment.
- R4 default `safe_concurrent_runs=2`, `host_ram_abort_gib=230`, `host_ram_hard_gib=235`.
- R2 measured one H3 Worker probe at about 72 GiB process RSS / 55 GiB host-used peak; R4 two-Worker concurrent evidence completed under the abort line.
- If no healthy idle Worker is available, the safe concurrency limit is full, RAM status is unavailable, or the RAM abort/hard line is reached, Studio returns `503 {"error":"no_worker_available"}` and does not enqueue extra work in a project-owned FIFO.

## Validation commands

```bash
python3 -m py_compile h3_studio/*.py scripts/*.py
python3 scripts/verify_r3_no_gpu.py
python3 scripts/verify_r4_no_gpu.py
python3 scripts/verify_rebaseline_docs.py
python3 scripts/run_r4_concurrent_e2e.py \
  --ffmpeg var/cache/tools/ffprobe-static-extracted/ffmpeg \
  --ffprobe var/cache/tools/ffprobe-static-extracted/ffprobe \
  --timeout 5400 \
  --out var/logs/r4-multi-worker-mvp/concurrent-e2e-result.json
python3 scripts/run_r4_profile_matrix.py \
  --ffmpeg var/cache/tools/ffprobe-static-extracted/ffmpeg \
  --ffprobe var/cache/tools/ffprobe-static-extracted/ffprobe \
  --timeout 5400 \
  --out var/logs/r4-multi-worker-mvp/profile-matrix-result.json
```

R4 media gates require H.264 video, stereo AAC audio, full decode, expected `864×480`/124-frame geometry, and no black/silence detector hits.

## Recovery and cleanup

- `scripts/start_r4_worker_pool.py` records launched PIDs in ignored `var/logs/r4-multi-worker-mvp/**.pid` and lifecycle evidence in `var/manifests/r4-worker-pool-lifecycle.json`.
- Stop the wrapper with Ctrl-C/SIGINT for controlled shutdown. If needed, terminate only PIDs recorded in the R4 log directory.
- Verify cleanup:

```bash
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory --format=csv,noheader,nounits
ss -ltnp '( sport = :30210 or sport = :30211 or sport = :30212 or sport = :30213 or sport = :30214 or sport = :30215 )'
```

- Studio marks completed/failed/cancelled Runs terminal when refreshed. On startup, stale active Runs on unhealthy Workers older than the recovery window are marked failed by `WorkerPool.recover_stale_runs()`.
- Run records remain under ignored `var/h3-studio/runs/<run_id>/run.json`; generated media remains under ignored Worker output namespaces.

## Known limits

- R4 supports single-host operator operation only; no auth, quotas, multi-tenancy or public binding.
- Guided Mode/product API Runs are scheduled and traced by Studio. Direct Advanced Canvas submissions are native ComfyUI Worker submissions and are not converted into Studio Run records unless submitted through the Studio API.
- Cancellation maps active Studio Runs to ComfyUI `/interrupt` on the assigned Worker and is bounded by ComfyUI behavior; cancelling an already terminal Run does not interrupt the Worker.
- Five simultaneous H3 generations are intentionally not enabled by default; all five GPUs are addressable, while active H3 concurrency remains capped at two pending further host-RAM evidence.
