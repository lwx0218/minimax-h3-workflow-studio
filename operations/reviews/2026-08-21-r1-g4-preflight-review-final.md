Review mode=spawned_pi_process

## P0

None.

## P1

None.

## P2

None.

## Assessment

- Owner authorization is explicit. `G4-TP4Q` is limited to GPUs 0–3 with legal `TP4 × Ulysses1`; GPU 4 and TP2/U2 are excluded.
- Launch is pinned to lock 2, native `--backend sglang`, clean source commit `44806dc507835746b67abebad041726c422030ea`, existing model fingerprints, and offline operation. No backend, weights, source patch, or system modification is introduced.
- Smoke evidence supports the exact `NCCL_P2P_DISABLE=1` fallback: default and cuMem-off world-2 collectives timed out, while P2P-disabled world-2 and world-4 completed. Host-routed communication and degraded scaling risk are disclosed.
- Installed source does not identify TP4 + `kitchen_int8` + encoder fold as invalid. TP dimensions and local quantization partitions are validated during model construction; explicit fold support exists. Failure occurs before health/request submission if initialization is incompatible.
- The manifest-backed runner enforces the canonical request, complete server argv, environment, provenance, 230/235 GiB controls, fail-closed monitoring, 3600-second bounds, project-local tools, and isolated G4 output paths.
- Existing G4 evidence cannot overwrite C3 or silently change topology, model variant, quantization, resolution, steps, sampler/cache behavior, or GPU visibility.
- The retained fixed probe supports `media duration / submit-to-terminal elapsed` first-output rate, separate load timing, C3 generation-speed ratio, and direct quality comparison. Documentation correctly limits claims to a cold single-probe comparison.
- Retained verification reports `RESULT PASS`.

## Required pre-launch fixes

None. This authorizes only the reviewed `G4-TP4Q` preflight launch and does not constitute R1 acceptance.

## Counts

- P0=0
- P1=0
- P2=0

Decision=safe_to_execute
