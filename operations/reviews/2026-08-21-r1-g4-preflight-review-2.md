Review mode=spawned_pi_process

## P0

None.

## P1

1. **The fixed probe is not fully fail-closed against request or output drift.**
   `scripts/run_r1_h3_attempt.py::parse_official_request` verifies only the prompt hash and preserves additional fields from the external request source. A same-prompt edit could introduce sampler/cache controls such as `enable_cache_dit`. `scripts/verify_r1.py` checks task, seed, and target, but not the exact normalized request, 50 steps, flow shifts, conditions, output count, or absence of approximation fields. It also does not require successful G4 media to remain 1344×768 with the expected duration alignment.
   **Required fix:** construct or hash an allowlisted canonical request and verify it at launch and runtime; reject extra approximation fields and gate successful G4 geometry/duration.

2. **Static verification does not independently pin the complete reviewed G4 contract.**
   `scripts/verify_r1.py::verify_static` checks selected argv sequences, but not the exact complete argv, executable, attention/offload/compile/warmup settings, all paths, prompt hash, or model fingerprint values. The runner compares invocation to the mutable manifest, so certain manifest drift could redefine the contract while static verification still passes.
   **Required fix:** compare the complete G4 contract against an independently fixed canonical structure or digest, including exact argv, paths, environment, controls, provenance values, and request digest.

## P2

1. **The single-probe comparison metric remains undefined.**
   Define first-output rate explicitly, for example media duration divided by submit-to-terminal elapsed time, with load time reported separately. Pair G4 media checks with C3 and label the result as a cold, single-probe comparison—not warm throughput, stability, or sustained scaling.

## Qualification assessment

- Owner authorization, GPUs 0–3 of five, and legal TP4×U1 topology are explicit.
- Lock 2, native `--backend sglang`, clean source commit, existing model path, and offline execution are enforced.
- Smoke evidence supports `NCCL_P2P_DISABLE=1`; world-2 and world-4 pass while default and cuMem-off time out. Degraded scaling risk is disclosed.
- Installed source does not show TP4 + `kitchen_int8` + encoder fold as known-invalid. TP/head/partition checks are compatible, and model initialization precedes health and request submission.
- The 230/235 GiB controls, fail-closed monitor, 3600-second bounds, four-GPU visibility, unique G4 output directory, and project-local media tools are present.
- The current argv excludes TP2/U2, lossless mode, Ref2VA, alternate weights, reduced requested resolution, approximate server cache flags, and GPU 4.

## Counts

- P0=0
- P1=2
- P2=1

Decision=changes_required
