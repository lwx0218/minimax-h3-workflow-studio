# License Inventory — MiniMax H3 Studio MVP

Status: R4 candidate inventory for local single-user MVP. This is engineering evidence, not legal advice.

| Component | Role | Identity | License / posture |
|---|---|---|---|
| Project-owned `h3_studio/`, scripts, docs, configs | Thin Control Plane, Guided Mode, operations evidence | repository candidate | Project-owned unless otherwise declared by Owner |
| ComfyUI backend/frontend | Authoritative graph, node, queue, execution, progress and Advanced Canvas foundation | ComfyUI `v0.34.2` / `169fcf35a2fc163fec31338b816503ddac0d3fcf`; frontend package `1.49.6` | GPLv3 upstream; local internal use is accepted for MVP; external distribution of modified ComfyUI components requires dedicated review |
| ComfyUI_RH_MinMaxH3 | Approved MiniMax-H3 custom nodes | `d6c5f7b0d4e03936ac4a9834be63ecc6b5637dad` | Third-party custom node; included only as pinned approved node for local MVP |
| PyTorch/CUDA wheel stack | Runtime compute | `torch 2.14.0+cu130`, `torchvision 0.29.0+cu130`, `torchaudio 2.11.0+cu130`, CUDA wheel packages | Third-party binary/runtime licenses; locked in `config/python-lock-r3.txt` |
| H3 runtime Python packages | H3 execution dependencies | `comfy-kitchen 0.2.31`, `comfy-aimdo 0.4.15`, `transformers 5.8.1`, `accelerate 1.14.0`, `av 18.1.0` | Third-party package licenses; locked in `config/python-lock-r3.txt` |
| MiniMax-H3 model assets | External weights/sidecars | external `H3_MODEL_ROOT`; manifest hashes in `config/asset-manifest.json` | Model/provider license remains with upstream/model owner; weights are not committed or redistributed by this repository |
| ffmpeg/ffprobe tools | Media validation evidence | project-local ignored tools under `var/cache/tools/` when available | Third-party tools used for validation; not committed |

## Boundary decisions

- No arbitrary third-party node market is enabled by default.
- No model weights, generated media, runtime logs, cache, databases or virtual environments are committed.
- Default services bind `127.0.0.1` for local single-user operation.
- Any external packaging or redistribution must re-open license review before shipment, especially because ComfyUI/frontend are GPL components.
