Review mode=spawned_pi_process

## P0

None.

## P1

1. **Backend is not fail-closed to native SGLang.**
   `operations/reviews/r1-attempt-manifest.json` omits `--backend sglang`. Installed `ServerArgs` defaults to `Backend.AUTO`, documented as allowing Diffusers fallback. This violates the no-backend-expansion boundary. Add `--backend sglang` to the exact argv and required-token checks.

2. **The launch environment permits contract-sensitive inherited drift.**
   `scripts/run_r1_h3_attempt.py` copies the full parent environment and validates only keys listed in the manifest. Extra variables such as `SGLANG_CACHE_DIT_ENABLED`, `NCCL_CUMEM_ENABLE`, or kitchen tuning variables remain possible, allowing approximate cache or transport/rate drift. Reject or explicitly pin all contract-sensitive variables and add regression coverage.

3. **The verifier cannot accept a successful G4 result.**
   `scripts/verify_r1.py` currently requires every retained MP4 to be under `C3-owner-exception/`; a valid `G4-TP4Q/probe.mp4` would fail verification. It also does not statically validate G4’s complete topology, environment, backend, controls, and paths. Update verifier/tests before launch to recognize exactly C3 plus the authorized G4 artifact and verify its contract/result.

4. **Lock-2 source and model identity are not enforced at launch.**
   Lock 2 is an editable install mapped to `var/cache/sglang-src`; the runner does not verify commit `44806dc507835746b67abebad041726c422030ea` plus a clean tracked tree. Likewise, the model alias is resolved dynamically without a C3-comparable snapshot fingerprint. Add fail-closed source provenance and lightweight model/request fingerprints so patched source, repointed weights, or request drift cannot pass the same argv.

## P2

1. **Cleanup evidence is captured but not enforced for G4.**
   The runner records a post-stop GPU snapshot but does not fail success on residual compute processes or elevated GPU memory. Add G4 verifier checks analogous to the retained C3 cleanup checks.

2. **Define the single-probe rate calculation explicitly.**
   Existing timing and media fields can support `output_duration / first-output elapsed`, but the comparison should be labeled cold/single-probe only and must not claim warm throughput or stability.

## Qualification assessment

- Owner authorization, GPUs `0,1,2,3`, and legal `TP4 × Ulysses1` are explicit.
- Smoke evidence justifies `NCCL_P2P_DISABLE=1`: default and cuMem-off timed out, while P2P-disabled world-2 and world-4 all-reduce completed. Degraded scaling risk is disclosed.
- Installed source does not show TP4+kitchen INT8+encoder-fold as known-invalid: H3 validates TP divisibility, 56 heads yield 14 heads/rank, kitchen INT8 validates TP-local partitions, and explicit fold supports pure TP replicas. Model initialization occurs before any request, providing fail-fast behavior for incompatibility.
- The 230/235 GiB limits, fail-closed monitor, 3600-second bounds, fixed probe fields, four-GPU visibility, unique output directory, and project-local media tools are otherwise present.

## Counts

- P0=0
- P1=4
- P2=2

Decision=changes_required
