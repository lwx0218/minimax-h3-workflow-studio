# R3 Single-Worker Product Operations

This checkpoint turns the accepted R2 ComfyUI MiniMax-H3 runtime into a single-Worker product slice.

## Scope

- Guided Mode is served by `python -m h3_studio.server`.
- Advanced Canvas is the complete pinned ComfyUI frontend at the Worker URL.
- The Studio server submits native ComfyUI API prompts and stores Run/Artifact metadata under ignored `var/h3-studio/`.
- ComfyUI remains the only graph, queue and execution engine.

## Prepare Controlled Distribution

Set the external model root, then prepare the ignored runtime:

```bash
export H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT
python3 scripts/prepare_r3_distribution.py --compute-sha
```

This creates `var/runtimes/r3-single-worker-product/`, installs the pinned ComfyUI/RH node stack, copies non-weight sidecars into the ComfyUI model root, and symlinks large `*.safetensors` weights from `H3_MODEL_ROOT`.

## Start Single Worker Product

```bash
export H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT
python3 scripts/start_r3_single_worker.py --gpu 0
```

Defaults:

- Studio: `http://127.0.0.1:30210`
- Worker / Advanced Canvas: `http://127.0.0.1:30211`
- Run metadata: `var/h3-studio/runs/`
- Worker outputs: `var/outputs/r3-single-worker-product/worker-gpu<gpu>/`（default `worker-gpu0`）
- Logs: `var/logs/r3-single-worker-product/`

## Guided Mode

Open the Studio URL. Select:

- `T2VA` for text-to-video+audio.
- `FL2VA` for first-frame-to-video+audio; upload a first-frame image.

The page displays status, ComfyUI WebSocket progress events when available, and playable/retrievable video Artifacts after completion.

## Advanced Canvas

Open the Advanced Canvas link from the Studio page. Load native ComfyUI workflow files from:

- `workflows/comfy-ui/t2va-balanced-r2-a5000.json`
- `workflows/comfy-ui/fl2va-first-frame-balanced-r2-a5000.json`

These are ComfyUI workflows, not a project-owned canvas or graph format.

## Validation

Fast no-GPU/mock check:

```bash
python3 scripts/verify_r3_no_gpu.py
```

Real product E2E after the product is running:

```bash
python3 scripts/run_r3_product_e2e.py \
  --ffmpeg var/cache/tools/ffprobe-static-extracted/ffmpeg \
  --ffprobe var/cache/tools/ffprobe-static-extracted/ffprobe
```

The real check submits one T2VA and one FL2VA through the Studio product API and validates returned media for video stream, stereo audio stream, full decode, expected 864×480 / 124-frame shape, no black segments, and no silence segments.

## Known R3 Limits

- R3 intentionally uses one Worker bound to one GPU; multi-Worker scheduling is R4.
- Cancellation is mapped to ComfyUI `/interrupt`, so the supported boundary is the active single Worker.
- The Balanced profile is the R2 accepted route; it is not final MVP performance acceptance.
