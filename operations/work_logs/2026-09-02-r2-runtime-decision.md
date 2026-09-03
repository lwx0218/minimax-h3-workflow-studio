# Work Log：R2 Runtime Decision

- Date：2026-09-02
- Checkpoint：R2 — Runtime Decision
- Status：`accepted_candidate_before_commit`
- Route：Owner-approved checkpoint / Class A runtime + GPU safety
- Candidate worktree：`r2-runtime-decision`（从 `a8b8b7d` 创建的隔离 git worktree）

## Scope Boundary

Candidate scope：

- R2 bounded ComfyUI MiniMax-H3 runtime probe tooling：`scripts/run_r2_h3_comfy_probe.py`
- 本 work log、R2 review artifact、Checkpoint Ledger 状态更新（closeout 时）

Context scope：`CONTEXT.md`、ADR-0001、rebaseline plan、orchestration、ledger、MVP spec、architecture、development process、`AGENTS.md`、`Harness_manual.md`、Baseline Reset work log/review、历史 R1 evidence。

Environment / dirty-worktree scope：主工作目录在本 session 开始时已有未提交治理层变化（`.pi` packages、`harness-flow` disable、治理文档更新等）。R2 candidate 使用隔离 git worktree（runtime logs 记录宿主机具体路径；提交文档保持相对/变量化），不修改、不提交主工作目录治理层 dirty changes。

## Rehydrate

- Branch / HEAD：`r2-runtime-decision` at `a8b8b7d8f94f76962b879399f5f9aa7103745c2d` (`docs: align checkpoints with session handoff`)。
- 主仓库状态：`main...origin/main [ahead 2]`，含预先 dirty governance changes；作为 environment scope 记录。
- GPU：5 × NVIDIA RTX A5000，单卡 24564 MiB；R2 probe 仅绑定 `CUDA_VISIBLE_DEVICES=0`。
- RAM：251 GiB；R2 hard line 235 GiB used，abort threshold 230 GiB used。
- Disk：root filesystem 1.8T，总可用约 1.4T；R2 runtime/cache/log/output 全部在 ignored `var/`。
- Python / Node：Python 3.12.9（conda base interpreter through venv）、Node v24.19.0、npm 11.17.0、Pi 0.84.4。
- Existing ComfyUI：未发现已安装可用 ComfyUI；R2 在 `var/runtimes/r2-runtime-decision/ComfyUI` project-local clone。

## DoR / Safety Bounds

- 不修改 system driver、kernel、system CUDA toolkit 或硬件拓扑。
- 只安装 project-local runtime：ComfyUI、ComfyUI_RH_MinMaxH3、Python venv、SwarmUI、本地 `.dotnet`；全部 under ignored `var/`。
- 不下载新模型家族；发现 Owner-provided FL2VA flat weight file存在但 safetensors header 无效后，使用本机已有 ModelScope cache 中同名 valid file 作为一次 model-asset correction。
- Runtime ports：ComfyUI probe `127.0.0.1:30122`；SwarmUI spike `127.0.0.1:30185`；ComfyUI discovery backend `127.0.0.1:30134`。
- Output roots：`var/outputs/r2-runtime-decision/`；temp roots：`var/tmp/r2-runtime-decision/`；logs：`var/logs/r2-runtime-decision/`。
- Cleanup：只终止本脚本启动并记录的 PIDs；post-run `nvidia-smi --query-compute-apps` 为空。

## Installed / Pinned Runtime

- ComfyUI：tag `v0.34.2` / commit `169fcf35a2fc163fec31338b816503ddac0d3fcf`。
- ComfyUI frontend package：`1.49.6`（ComfyUI requirements pinned）。
- ComfyUI workflow templates：`0.11.50`。
- ComfyUI_RH_MinMaxH3：commit `d6c5f7b0d4e03936ac4a9834be63ecc6b5637dad`。
- Python venv：`var/runtimes/r2-runtime-decision/venv`。
- Torch stack：`torch 2.14.0+cu130`、`torchvision 0.29.0+cu130`、`torchaudio 2.11.0+cu130`、CUDA runtime 13.0 wheel packages、`triton 3.8.0`。
- H3 runtime packages：`comfy-kitchen 0.2.31`、`comfy-aimdo 0.4.15`、`transformers 5.8.1`、`accelerate 1.14.0`、`av 18.1.0`。
- Media tools：project-local static `ffmpeg/ffprobe 7.0.2-static` from historical R1 cache, exposed on process `PATH` via ignored symlink.

## Model Asset Identity

Owner-provided model root：`$H3_MODEL_ROOT`（本机外置模型目录；具体宿主机绝对路径仅出现在 ignored runtime logs / session prompt，不写入提交文档）。

Validated assets used by the successful probe：

| Component | Source | SHA-256 | Notes |
|---|---|---|---|
| DiT FL2VA INT8 ConvRot | local ModelScope cache same model repo | `4e464ae3d21ff81ef51efced3420cbf2d6139a5ec1ccc6f9793b43b158ebf738` | Owner-provided path copy had invalid safetensors header (`a62cec...`) and was not used |
| Qwen3-VL text encoder INT8 ConvRot | Owner-provided root | `e9d0a5cc9df09c99882bf0fffd82a71d16e9247338cc3990f7d332a969c53203` | safetensors OK |
| Video VAE | Owner-provided root | `aa4a9ffb89cced1fa9f2a8e0dbd72853f8c01e2f08be9c4a0915fc9d1ecabbfa` | safetensors OK |
| Audio VAE | Owner-provided root | `37dddc2f3e6d5d5139d823d5ea283bbf304dadcb885b1ccda818aa13dade5ea2` | safetensors OK |
| FL2VA model_index | Owner-provided root | `d1113e0f123c69f79cd0de35ca1771606ebc3ec924270d257b771f96f584aa6b` | sidecar OK |

Sidecar config/tokenizer/processor files were copied (excluding `*.safetensors`) into ignored ComfyUI `models/diffusers/MiniMax-H3/` because the RH plugin rejects partition symlinks resolving outside selected model root. Large weights remained external symlinks; no weights copied into Git.

## Primary ComfyUI H3 Probe

Command wrapper：

```bash
var/runtimes/r2-runtime-decision/venv/bin/python scripts/run_r2_h3_comfy_probe.py \
  --repo "$PWD" \
  --comfy "$PWD/var/runtimes/r2-runtime-decision/ComfyUI" \
  --python "$PWD/var/runtimes/r2-runtime-decision/venv/bin/python" \
  --ffmpeg "$PWD/var/cache/tools/ffprobe-static-extracted/ffmpeg" \
  --ffprobe "$PWD/var/cache/tools/ffprobe-static-extracted/ffprobe" \
  --gpu 0 --port 30122 \
  --width 864 --height 480 --duration 5.0 --sigma-points 21 --seed 42 \
  --load-timeout 900 --generation-timeout 3600 \
  --host-abort-gib 230 --host-hard-gib 235 --max-temp-c 84
```

Profile：T2VA through FL2VA partition；explicit `864×480`；requested 5.0 s；resolved 124 frames @ 24 fps；`sigma_points=21` (`res_multistep`, 20 DiT forwards)；`accel=off`；prompt asks for rain-lit gutter, paper boat, passing train and synchronized rain/wheel noise.

Raw evidence retained in ignored runtime paths：

- Result：`var/logs/r2-runtime-decision/probe-20260902T022149Z/result.json`
- Server log：`var/logs/r2-runtime-decision/probe-20260902T022149Z/comfyui-server.log`
- Resource samples：`var/logs/r2-runtime-decision/probe-20260902T022149Z/resource-samples.jsonl`
- Media：`var/outputs/r2-runtime-decision/probe-20260902T022149Z/r2_probe/cold_00001_.mp4` and `warm_00001_.mp4`
- Frame sheet：`var/outputs/r2-runtime-decision/probe-20260902T022149Z/frames/r2-cold-warm-contact-sheet.jpg`

Results：

| Phase | Terminal | Submit→terminal | Server prompt time | Cached nodes | SHA-256 | Media |
|---|---:|---:|---:|---|---|---|
| cold | success | 285.242 s | 280.73 s | `[]` | `32f28b8e9dd03b43fd04ade8d3d51e124803ed0ecf882c2bb6ad260b173d787e` | 864×480 H.264, 124 frames, AAC stereo |
| warm | success | 260.240 s | 256.51 s | `[]` (`--cache-none`) | `db041a4161f6299b12b89feb4d56da83463f4b6606ad5ee38a77fa782d47b0f4` | 864×480 H.264, 124 frames, AAC stereo |

Resource peaks over the successful cold+warm session：

- host used：55.062 GiB（below 230 GiB abort / 235 GiB hard line）
- process RSS：72717.0 MiB
- GPU0 VRAM：22963 MiB used peak
- GPU0 temperature：71°C peak
- GPUs 1–4 remained idle (1 MiB reported used)
- resource violations：none
- cleanup：post-run compute process list empty

Media validation：

- `ffprobe` confirmed one H.264 video stream and one AAC LC stereo audio stream (`32000 Hz`, 2 channels).
- Full `ffmpeg -v error -i ... -f null -` decode passed for both cold and warm media.
- `blackdetect=d=0.5` and `silencedetect=n=-50dB:d=0.5` found no black/silence segments.
- Representative first/middle/last frames extracted for both cold and warm. Visual contact sheet shows coherent low-angle night gutter scene with paper boat, wet reflections, street/train lights; not black, pure noise, or corrupt.

Initial failed/corrected attempts：

1. Running the wrapper via `./scripts/...` resolved the venv symlink to the base conda Python; fixed by invoking with venv Python and preserving venv path in child server command.
2. First Comfy prompt failed because RH plugin rejected symlinked sidecar partition directories resolving outside selected model root; fixed by copying sidecar non-weight files into ignored ComfyUI model root.
3. Second Comfy prompt failed because Owner-provided FL2VA `.safetensors` was invalid (`Error while deserializing header: header too large`); fixed by relinking to valid same-file ModelScope cache. This is the single model-asset correction used.
4. One apparent warm run was invalid as evidence because ComfyUI cached upstream nodes; final accepted run starts server with `--cache-none`, and both phases report `cached=[]`.

## SwarmUI Controller Spike

Pinned SwarmUI：commit `b4602b99d32bfaaf31b834ad4f8949e652676bf3` (`SwarmUI v0.9.8.2`) in ignored `var/runtimes/r2-runtime-decision/SwarmUI`.

Local `.NET` installed under ignored `SwarmUI/.dotnet` only: SDK `10.0.400` and `8.0.424`; runtimes `10.0.11` and `8.0.30`. Build succeeded with 0 warnings / 0 errors.

Spike evidence：`var/logs/r2-runtime-decision/swarmui-controller-spike-4/`.

Validated positive behavior:

- SwarmUI starts on `127.0.0.1` with isolated `data_dir`.
- `/API/GetNewSession` works.
- `/API/ListBackendTypes` exposes `comfyui_api` (`ComfyUI API By URL`), `comfyui_selfstart`, and `swarmswarmbackend`.
- A valid existing ComfyUI API backend (`127.0.0.1:30134`) can be added/edited and reaches `status: running`.
- An invalid ComfyUI URL reaches `status: errored`, and `/API/GetCurrentStatus` reports backend error state.

Disposition / fail reasons for adopting SwarmUI as R2 controller:

- SwarmUI proves backend discovery/status/failure reporting at a basic level, but the bounded spike did **not** prove robust H3 workflow submission/progress/artifact correlation for the project’s accepted RH-plugin ComfyUI path.
- SwarmUI’s own H3 support is oriented around its Comfy backend extra nodes / model registry and separate Comfy-Org model names; adopting it now would change the already-proven runtime path and likely require new model placement/download/pinning work outside this R2 bounded correction.
- Its documentation for Custom Comfy Workflows is currently a placeholder, while its multi-GPU Comfy workflow guidance explicitly warns that direct Comfy-tab outputs can replace each other and current frontend may ignore status updates after one backend finishes. That does not meet R2/R4 needs for reliable per-Run progress and artifact correlation.
- API docs for `EditBackend` omit the actual required top-level `settings` shape; this was discovered during the spike and increases integration risk.

Controller decision：`build_thin_control_plane` using ComfyUI HTTP/WebSocket contracts in R3/R4. The Control Plane must remain thin: Worker discovery, assignment, progress/artifact correlation, failure/cancel/restart boundaries only; no second graph executor.

## Verification

Executed:

```bash
python3 -m py_compile scripts/run_r2_h3_comfy_probe.py
# successful full probe command shown above
git check-ignore -v var/logs/r2-runtime-decision/probe-20260902T022149Z/result.json \
  var/outputs/r2-runtime-decision/probe-20260902T022149Z/r2_probe/cold_00001_.mp4 \
  var/runtimes/r2-runtime-decision/ComfyUI/main.py \
  var/tmp/r2-runtime-decision/swarm-data6/Settings.fds
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory --format=csv,noheader,nounits
```

Results：

- Probe：PASS（cold + warm valid media, no resource violations）。
- `python3 -m py_compile scripts/run_r2_h3_comfy_probe.py` and venv `python -m py_compile`：PASS。
- `python3 scripts/verify_rebaseline_docs.py`：PASS。
- `git diff --check`：PASS。
- Runtime outputs/cache/logs：ignored by `/var/*`.
- GPU cleanup：PASS（no compute apps after probe/spike）。
- `git status --short -- var`：clean（ignored runtime only）。
- Committed docs/scripts checked for host absolute path leakage：PASS。
- No system driver/kernel/CUDA toolkit changes.

## Anti-Drift Check

1. Reuses ComfyUI semantics：yes.
2. Introduces WorkflowDocument/DAG/node registry/queue/canvas：no.
3. Control Plane becoming graph executor：no; decision is future thin coordination only.
4. Replica Execution vs Single-Request Multi-GPU conflated：no.
5. Optimization presented as reference/lossless：no; INT8/res_multistep are disclosed runtime decision evidence only.
6. Community claim used as target-host evidence：no; target-host A5000 cold/warm evidence recorded.
7. Failed multi-GPU blocks R2：no.
8. Review proportional：Class A independent review required before acceptance.
9. Superseded docs regain authority：no.

## Known Limits / P2 Candidates

- The successful R2 route uses one corrected local ModelScope cache FL2VA safetensors because the Owner-provided path copy is corrupt. R3 should normalize approved asset placement and avoid ambiguous duplicate local copies.
- R2 validates T2VA through FL2VA partition only, not FL2VA keyframe/image input; R3 must package both T2VA/FL2VA templates.
- R2 media evidence is backend/API engineering evidence, not Functional MVP frontend acceptance.
- Warm timing is a single immediate second prompt in the same server process with ComfyUI node cache disabled; it is not sustained throughput or final profile acceptance.
- SwarmUI is not adopted for controller, but can remain a future reference/backlog item if Owner later accepts its UX/status/artifact constraints.

## Independent Review / Final Integrated Review

Independent review artifact：`operations/reviews/2026-08-28-r2-runtime-decision-review.md`。

- Reviewer：Pi `reviewer` subagent run `d6a51c62-3799-419a-9a20-2cf1c741dae3`。
- Decision：`pass` / OK with notes。
- Findings：P0=0、P1=0、P2=1。
- P2 disposition：accepted non-blocking limitation。Reviewer 指出 `scripts/run_r2_h3_comfy_probe.py` 的 automatic pass predicate 弱于完整 media gate；当前 R2 evidence 和 review 已显式验证 stereo、resolution、frame count、decode、black/silence、frame extraction 和人工 contact sheet。R3 若复用该脚本，应补强自动断言。

Final integrated review artifact：`operations/reviews/2026-08-28-r2-final-integrated-review.md`；Decision `pass_to_commit`。

## Next

Create scoped R2 checkpoint commit and run post-commit verification. Next product checkpoint after accepted commit：R3 — Single-Worker Product。
