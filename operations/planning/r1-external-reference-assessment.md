> **SUPERSEDED future-plan notice:** This assessment is retained as historical R1 reference evidence. Its recommendation to preserve an independent `H3Backend`, defer ComfyUI, or gate on 4-GPU SGLang is superseded by [`rebaseline-plan-v1.md`](rebaseline-plan-v1.md). It is not an execution instruction.

# R1 External MiniMax-H3 Reference Assessment

- Date：2026-08-21
- Purpose：评估 Owner 提供的 4 个 GitHub references，决定是否调整本项目的实现顺序
- Boundary：只读取 source/docs/sample media；clone 位于 ignored `var/cache/r1-references/`；未安装其依赖、未执行第三方节点、未下载新权重

## Sources Pinned

| Source | Reviewed commit | Role | Trust level |
|---|---|---|---|
| [neng320/minimax-h3-local-deployment](https://github.com/neng320/minimax-h3-local-deployment) | `9cc731ce1c99bd5849f65ce4a69930dbec8858f4` | 4060 Ti/ComfyUI 实操和 benchmark | community evidence；需复验 |
| [modelscope/DiffSynth-Studio](https://github.com/modelscope/DiffSynth-Studio) | `fed7b18fac2ed4cb802796eec91970e7659bccde` | Python pipeline、NF4/INT8、disk/CPU offload | mature framework reference |
| [HM-RunningHub/ComfyUI_RH_MinMaxH3](https://github.com/HM-RunningHub/ComfyUI_RH_MinMaxH3) | `d6c5f7b0d4e03936ac4a9834be63ecc6b5637dad` | direct ComfyUI runtime、INT8/offload/sampler | focused implementation reference |
| [wildminder/awesome-minimax-H3](https://github.com/wildminder/awesome-minimax-H3) | `5db296685ff7343bb149e351c6f43d1569138bd5` | ecosystem index/performance digest | secondary index；not acceptance evidence |

Commit pins are the review baseline；future upstream changes require re-review。

## Independent Checks

### neng320 deployment guide

Repository includes two sample MP4s。Project-local static ffprobe independently confirmed both have H.264 video + AAC stereo 32 kHz audio：

- v1 sample：640×640，5.167 s，922309 bytes，SHA-256 `83444f06382b56216599a935dc2c34e7522e71809fc6c41b3661e3eed6b6edff`
- v2 sample：640×640，5.166667 s，1369389 bytes，SHA-256 `e6515cdf780e097098491f59e4c1eaa9e88161a77e09d47b47b5ffadb90561b4`

Useful：

- draft/final resolution tiers
- cold/warm timing separation
- media QC and failure notes
- explicit warning that aggressive TE-Speed can damage text/structure

Caveats：

- Benchmarks are Windows + RTX 4060 Ti + ComfyUI，not Linux A5000/SGLang。
- Most claimed speedups combine different resolution、steps、Turbo LoRA、SageAttention and converted/pruned weights；they cannot be compared directly to the R1 fixed 768p/50-step probe。
- Documentation is internally inconsistent：README says v1 has no Turbo LoRA / workflow JSON has no LoRA node，but both inspected v1/v2 workflow JSON files contain a Turbo LoRA node。
- Repository root has no detected license file at the reviewed commit despite README text saying MIT；do not copy source/workflows into this project without license clarification。

Decision：borrow test design and operational lessons，not performance claims or code。

### DiffSynth-Studio

Reviewed docs and low-VRAM scripts show explicit model-component loading and `vram_limit`。NF4 and INT8 examples use CPU/disk offload and independently write video/audio。

Useful：

- clean Python inference entrypoint
- explicit component `ModelConfig`
- configurable CPU/disk offload and VRAM ceiling
- NF4/INT8 alternatives and tiled VAE controls
- possible future backend adapter because output is ordinary `(video, audio)` data

Caveats：

- “minimum 7G VRAM” uses separate NF4 model artifacts and aggressive disk offload；it is not evidence for current official snapshot or acceptable throughput。
- Reviewed inference examples are single-GPU；training uses ZeRO-3，but that does not establish 4-GPU inference.
- Adopting it requires a new dependency lock/backend and potentially new quantized weights；outside the corrected C3 retry。

Decision：retain as strongest non-SGLang fallback candidate if SGLang remains blocked；do not switch before corrected C3 and 4-GPU SGLang disposition。

### ComfyUI_RH_MinMaxH3

Useful implementation ideas：

- typed/fingerprinted component contracts
- shape-aware activation reserve and fail-fast capacity tiers
- layerwise offload with explicit residency policy
- per-stage telemetry and media sidecar
- baseline `euler/50` versus `res_multistep/21` as separate quality/performance profiles
- approximate cache profiles default off

Caveats：

- It is a ComfyUI in-process plugin，not a multi-GPU service。
- It relies on converted INT8 component files in addition to release configuration；those files are not the current R1 dependency set。
- The stated 20-forward `res_multistep` quality result is project-provided benchmark evidence，not yet reproduced on A5000 or against this project's fixed prompt。
- Third-party node execution remains outside MVP security boundary；architecture ideas may be reimplemented behind `H3Backend` without workflow compatibility。

Decision：borrow telemetry/contracts/quality-tier design；keep it as a single-card fallback implementation candidate, not current default。

### awesome-minimax-H3

Useful as discovery index for quantization、samplers、attention and benchmark links。Many values aggregate community reports with different hardware/models/steps/resolutions。

Decision：use it to locate primary sources only；never use aggregated claims as acceptance evidence。

## Plan Impact

### Immediate R1 path

1. Harden existing runner/verifier before another GPU run：resource monitor fail-closed、exact argv checks、manifest ID uniqueness、request prompt re-hash。
2. Execute the Owner-authorized corrected single-card C3 using the already installed lock 2 and official `kitchen_int8` path。
3. Keep fixed 768 short-edge、5 s、50-step、seed 0 probe so C3 is directly comparable to C2。
4. Require succeeded status、retained MP4、checksum、independent ffprobe video+audio and decode。

External references do not change this minimal path；C2 already reached denoise/mux and is closer to success than introducing another backend。

### Four-GPU path after C3

- Use 4 of 5 GPUs；5-way is illegal for H3's 56 heads / 64 packed partitions。
- Run dependency/NCCL topology smoke before model loading。
- Start capacity-first with legal `TP4 × Ulysses1`; consider `TP2 × Ulysses2` only as the bounded throughput comparison after host-memory analysis。
- Compare cold load、first output、warm output、GPU/host peaks and output media quality against C3。
- Keep the same model/seed/target for baseline comparison；do not mix Turbo LoRA、reduced resolution or approximate cache into the 4-GPU baseline。

### Development plan acceleration

- Preserve the provider-neutral `H3Backend` contract；do not couple WorkflowDocument to SGLang or ComfyUI JSON。
- Add explicit runtime capability/quality metadata so future profiles can distinguish `baseline`, `quantized`, `draft` and `final` without silently changing quality。
- R7 performance evidence must separate cold start、warm latency、throughput and quality；every optimized profile retains a baseline comparator。
- After the lossless/official-step baseline exists，evaluate in order：
  1. `res_multistep` or equivalent reduced-forward sampler
  2. attention backend such as Sage/Sol only with A5000 support evidence
  3. Turbo/cache only as an opt-in draft profile with visual/audio regression evidence
- Do not adopt TE-Speed as default；the reviewed source itself records structural/text quality failures。
- Do not download NF4/GGUF/pruned/ConvRot component sets until SGLang 4-GPU is dispositioned or Owner explicitly selects a fallback backend。

## Outcome And Updated Recommendation

Corrected SGLang C3 succeeded。The legal TP4 kitchen_int8 follow-up then failed because four workers duplicated transformer CPU staging and crossed the host safety line；the proposed AdaLN-online mitigation was rejected before launch because installed source requires unquantized weights。

Current recommendation：Owner first chooses one bounded unquantized TP4 + AdaLN-online SGLang test if single-request 4-way latency and maximum baseline quality are mandatory。If the real priority is aggregate output throughput，switch the next spike to DiffSynth-Studio or ComfyUI_RH converted low-memory weights and design independent GPU worker replicas behind the provider-neutral `H3Backend`；that is a backend/weights/single-concurrency plan change and must not be introduced silently。
