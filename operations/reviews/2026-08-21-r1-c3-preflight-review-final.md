# R1 C3 Preflight Independent Review Report

Review mode=spawned_pi_process

## Findings

### P0

None.

### P1

None.

### P2

None.

## Confirmed controls

- Owner authorization is recorded as the distinct `C3-owner-exception` slot; the six historical A1–C2 profile slots remain unchanged.
- Duplicate manifest IDs are rejected. C3 requires exact server argv, paths, controls, GPU selection, and authorization state. Existing attempt directories cannot be overwritten.
- The official request prompt is re-hashed from source before launch, and `verify_r1.py` independently re-hashes persisted request content.
- Resource-monitor setup, sampling, missing-GPU, thread-liveness, and late failures fail closed. The monitor must provide a first sample and be stopped, joined, and rechecked before success can be recorded.
- Host thresholds are fixed at 230 GiB abort and 235 GiB hard line.
- C3 is bound to lock 2, GPU 0 only, `kitchen_int8`, FlashAttention, the fixed 768p/5-second/50-step probe, project-local resolved ffmpeg/ffprobe, and `var/outputs/r1-feasibility/C3-owner-exception/`.
- External references do not authorize another backend, dependency lock, weight set, reduced-resolution probe, Turbo/cache, or approximate acceleration.
- C2 remains honestly recorded as terminal `failed`; historical absolute runtime paths remain confined to ignored evidence. The hardening verification reports `RESULT PASS`, with Git/runtime exclusions and disk budget intact.

## Counts

- P0=0
- P1=0

## Required fixes before generation

None. Execute at most the single manifest-authorized C3 through the hardened runner and exact launch contract.

Decision=safe_to_execute

This is C3 preflight clearance only, not R1 acceptance.
