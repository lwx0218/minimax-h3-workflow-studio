# Work Log：R3 Single-Worker Product

- Date：2026-09-02
- Plan: `operations/planning/rebaseline-plan-v1.md`
- Round: `R3`
- Round ID: `R3`
- Primary implementation session: `R3-single-worker-product`
- Git baseline: `56fdda4cc3825034a9b4c6b2ccdaf98aede14ccf`
- Checkpoint: `R3 — Single-Worker Product`
- Status：`accepted_candidate_before_commit`
- Route：Owner-authorized fixed checkpoint / Class B product + Class A runtime/asset boundary
- Candidate worktree：`r3-single-worker-product` at R2 accepted baseline `56fdda4`

## Scope Boundary

Candidate scope:

- Controlled Distribution manifests and preparation/start scripts.
- Native ComfyUI API/UI workflow templates for T2VA and FL2VA first-frame.
- Thin project-owned Studio server for Guided Mode, Run/Artifact traceability, status/progress display and single Worker submission.
- Operator documentation, README/.env example and checkpoint-state updates.

Non-goals held: no Multi-Worker scheduling, no Single-Request Multi-GPU, no ComfyUI frontend fork, no custom canvas, no parallel WorkflowDocument/DAG executor/node registry/application FIFO queue, no arbitrary third-party node market.

Environment / dirty-worktree scope: this R3 worktree contains pre-existing Pi Fleet capability dirtiness (`.pi/settings.json`, `.pi/npm/`) outside candidate scope. These paths were not modified for product delivery and must not be staged into the R3 product commit.

## Rehydrate / DoR

- Source-of-truth documents read in required precedence order.
- Current branch: `r3-single-worker-product`.
- R2 accepted facts retained: ComfyUI `v0.34.2`, RH MiniMax-H3 `d6c5f7b`, torch `2.14.0+cu130`; R2 controller decision `build_thin_control_plane`.
- Runtime defaults: Studio `127.0.0.1:30210`, single Worker / Advanced Canvas `127.0.0.1:30211`, GPU `0`, runtime/log/output/data under ignored `var/`.
- External model root supplied via `H3_MODEL_ROOT`; no model weights copied into Git.

Asset validation with full SHA-256:

| Asset | SHA-256 | Result |
|---|---|---|
| `MiniMax-H3-FL2VA-int8_convrot.safetensors` | `4e464ae3d21ff81ef51efced3420cbf2d6139a5ec1ccc6f9793b43b158ebf738` | PASS |
| `qwen3-vl-32b-int8_convrot.safetensors` | `e9d0a5cc9df09c99882bf0fffd82a71d16e9247338cc3990f7d332a969c53203` | PASS |
| `MiniMax-H3-video_vae.safetensors` | `aa4a9ffb89cced1fa9f2a8e0dbd72853f8c01e2f08be9c4a0915fc9d1ecabbfa` | PASS |
| `MiniMax-H3-audio_vae.safetensors` | `37dddc2f3e6d5d5139d823d5ea283bbf304dadcb885b1ccda818aa13dade5ea2` | PASS |

## Implemented Candidate

- `h3_studio/` Python stdlib Studio server:
  - Guided Mode HTML form for T2VA and FL2VA first-frame;
  - native ComfyUI API prompt submission only;
  - status polling from `/history/{prompt_id}`;
  - direct ComfyUI WebSocket progress event display in browser;
  - cancel mapped to ComfyUI `/interrupt` for the active single Worker;
  - Artifact proxy links for playable/retrievable MP4;
  - Run records under `var/h3-studio/runs/<run_id>/run.json` containing workflow/API snapshot, profile, runtime/model identity, seed/input hashes, status/history and artifacts.
- `config/` manifests pin runtime, approved assets and the R2-proven Balanced profile.
- `workflows/comfy-api/` stores native ComfyUI API templates used by Guided Mode.
- `workflows/comfy-ui/` stores native ComfyUI workflows for Advanced Canvas loading.
- `scripts/prepare_r3_distribution.py` clones/pins ComfyUI and RH nodes into ignored `var/runtimes/r3-single-worker-product/`, installs the pinned stack, copies sidecars to `models/diffusers/MiniMax-H3`, and symlinks flat weights to `models/MiniMax-H3`.
- `scripts/start_r3_single_worker.py` starts the single GPU-bound Worker and Studio product entry.
- `scripts/verify_r3_no_gpu.py` performs mock/no-GPU config, workflow and Run traceability validation.
- `scripts/run_r3_product_e2e.py` submits real T2VA/FL2VA through the Studio product API and validates returned media.
- `docs/operations/r3-single-worker-product.md`, `README.md`, `.env.example` document reproducible start and validation.

## Automated Verification

Commands passed:

```bash
python3 -m py_compile h3_studio/*.py scripts/prepare_r3_distribution.py scripts/start_r3_single_worker.py scripts/verify_r3_no_gpu.py scripts/run_r3_product_e2e.py
python3 scripts/verify_r3_no_gpu.py
H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT python3 scripts/prepare_r3_distribution.py --skip-install --compute-sha
H3_MODEL_ROOT=$EXTERNAL_MINIMAX_H3_MODEL_ROOT python3 scripts/prepare_r3_distribution.py
mkdir -p var/tmp/r3-single-worker-product
curl -fsS http://127.0.0.1:30210/ >var/tmp/r3-single-worker-product/r3-index.html && grep -q 'Guided Mode' var/tmp/r3-single-worker-product/r3-index.html
curl -fsS 'http://127.0.0.1:30210/api/assets/check?sha256=1'
python3 scripts/run_r3_product_e2e.py --ffmpeg var/cache/tools/ffprobe-static-extracted/ffmpeg --ffprobe var/cache/tools/ffprobe-static-extracted/ffprobe --timeout 4200 --out var/logs/r3-single-worker-product/product-e2e-result-3.json
git diff --check
python3 scripts/verify_rebaseline_docs.py
```

Real product E2E PASS:

| Kind | Run ID | Status | Artifact | Media gate |
|---|---|---|---|---|
| T2VA | `run-095dd8bc232d` | completed | `run-095dd8bc232d_00001_.mp4` | H.264 video, AAC stereo audio, 864×480, 124 frames, full decode, no black segment, no silence segment |
| FL2VA first-frame | `run-53dc7aac3d0c` | completed | `run-53dc7aac3d0c_00001_.mp4` | H.264 video, AAC stereo audio, 864×480, 124 frames, full decode, no black segment, no silence segment |

Ignored raw evidence:

- Product E2E JSON: `var/logs/r3-single-worker-product/product-e2e-result-3.json`
- Contact sheet: `var/logs/r3-single-worker-product/frames-result-3/contact-sheet.jpg`
- Frame stats: `var/logs/r3-single-worker-product/frames-result-3/frame-stats.json`
- Run metadata: `var/h3-studio/runs/run-095dd8bc232d/run.json`, `var/h3-studio/runs/run-53dc7aac3d0c/run.json`
- Runtime manifest: `var/manifests/r3-distribution.json`

Contact sheet was visually inspected by Builder and shows coherent rain-lit gutter / paper boat scenes for both T2VA and FL2VA, not black/noise/corrupt.

## Cleanup / Git Boundary

- Killed only R3-launched wrapper/Studio/ComfyUI PIDs.
- Post-run `nvidia-smi --query-compute-apps` produced no compute process rows.
- Ports `30210` and `30211` closed after cleanup.
- `git check-ignore -v` confirmed runtime logs, outputs, ComfyUI runtime and Run records are ignored by `/var/*`.
- Candidate committed files contain no host absolute model/runtime path; absolute paths are limited to ignored runtime evidence and the non-candidate `.git` worktree pointer.

## Review Findings Disposition

Independent per-round review was rerun after initial P2 cleanup and returned P1=2, P2=1. Dispositions in progress:

- P1 portability: fixed by replacing host-absolute model-root command examples in this work log with `$EXTERNAL_MINIMAX_H3_MODEL_ROOT`.
- P1 sidecar manifest: fixed by assigning a deterministic FL2VA sidecar tree SHA-256 in `config/asset-manifest.json` and changing `scripts/prepare_r3_distribution.py` to copy only manifest-declared sidecar directories instead of all non-weight sidecars.
- P2 dependency lock: fixed for R3 by adding `config/python-lock-r3.txt` from the prepared venv and applying it as a pip constraints file in `scripts/prepare_r3_distribution.py` while retaining pinned ComfyUI/RH source commits.

## Anti-Drift Check

1. Reuses ComfyUI semantics: yes.
2. Introduces WorkflowDocument/DAG/node registry/queue/canvas: no.
3. Control Plane becoming graph executor: no; it submits native ComfyUI prompts and records Runs/Artifacts only.
4. Replica Execution vs Single-Request Multi-GPU conflated: no; R3 is single Worker only.
5. Optimization presented as reference/lossless: no; INT8 ConvRot profile is disclosed.
6. Community claim used as target-host evidence: no; target-host product E2E evidence recorded.
7. Failed multi-GPU blocks R3: no.
8. Review proportional: independent R3 review requested after automated verification.
9. Superseded docs regain authority: no.

## Known Limits / P2 Candidates

- R3 product E2E is through the Studio product HTTP API and browser-served Guided Mode page; no Playwright/browser automation is added.
- Cancellation uses ComfyUI `/interrupt` and is single-Worker scoped.
- The Studio server uses Python stdlib `cgi` multipart parsing under Python 3.12; this is acceptable for local R3 but should be replaced before Python 3.13.
- R3 is intentionally single Worker; fair scheduling, stale leases and multi-Worker recovery are R4.

## Independent Review

Independent review artifact: `operations/reviews/r3-single-worker-product-review.md`.

Review decision: pass
Findings: P0=0 P1=0 P2=0
Candidate immutable: yes
Unresolved P0: 0
Unresolved P1: 0

Earlier P2/P1 findings were fixed and regression-verified as recorded in the review artifact.

## Final Integrated Review

Final integrated review artifact: `operations/reviews/2026-08-28-r3-final-integrated-review.md`.

Review decision: pass
Findings: P0=0 P1=0 P2=0

Subagent final re-review confirmed the ComfyUI-first boundary, native workflow/API usage, Advanced Canvas as pinned ComfyUI frontend, traceable Runs/Artifacts, asset/dependency hashes, ignored runtime boundary, and no committed host absolute path leakage in R3 scope.

## Next

Perform pre-commit gate, scoped R3 checkpoint commit and post-commit verification. Next checkpoint after accepted commit: R4 — Multi-Worker MVP.
