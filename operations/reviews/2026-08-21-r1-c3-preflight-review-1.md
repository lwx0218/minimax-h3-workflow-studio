# R1 C3 Preflight Independent Review

Review mode=spawned_pi_process

## Findings

### P0

None.

### P1

#### P1-1 — C3 is not bound to a reviewed, non-overwriting launch record

**Evidence**

- `operations/reviews/r1-attempt-manifest.json` ends at C2 and contains no C3 exception entry.
- `scripts/verify_r1.py` requires runtime IDs to equal the manifest IDs, so a new C3 would initially fail verification as an unknown execution.
- `scripts/run_r1_h3_attempt.py` uses `mkdir(exist_ok=True)` and truncating writes without rejecting an existing attempt ID. An incorrect ID could overwrite historical evidence.
- The runner does not pre-launch enforce C3’s exact lock-2 executable, one-GPU configuration, `kitchen_int8`, 230/235 GiB thresholds, canonical output root, or expected prompt hash.
- Tool preflight verifies a binary named `ffprobe`/`ffmpeg` is on `PATH`, but does not assert that `shutil.which()` resolves to the supplied project-local executable.

**Impact**

The documentation correctly authorizes C3 as a new exception, but the actual generation command remains operator-dependent and is not mechanically protected from historical-slot reuse or configuration drift. Therefore one bounded C3 cannot yet be independently proven before launch.

#### P1-2 — Resource monitoring is not completely fail-closed

**Evidence**

- In `ResourceMonitor.run()`, opening `resources.csv` and writing its header occur outside the exception handler. Failure there terminates the daemon thread without setting `monitor_failed`.
- The main thread checks monitor events but not monitor readiness/liveness, so such a failure can leave the attempt running without monitoring.
- After the final `monitor_failed` check, the runner sets `status="succeeded"` before stopping and joining the still-active monitor. A late sampling failure can therefore leave runner status successful and exit code zero, although the verifier would later reject the metadata.
- `scripts/test_r1_hardening.py` tests an in-loop sampler exception but not setup failure, monitor-thread death, or late failure before success finalization.

**Impact**

This does not fully satisfy the required pre-generation hardening that sampling failure cannot silently permit a successful run.

### P2

None.

## Confirmed controls

- Owner authorization is durably recorded as a C3 exception; historical A/B/C slots remain reported as exhausted rather than rewritten.
- Manifest duplicate-ID checking, argv-sequence matching, and request prompt content re-hashing are implemented for existing manifested executions.
- Runner defaults remain 230 GiB abort and 235 GiB hard limit.
- The fixed request builder specifies T2VA, 768 short edge, 16:9, five seconds, seed 0, and 50 inference steps.
- External references explicitly do not authorize new weights, backend, dependency lock, Turbo/cache, or approximate acceleration.
- Existing C2 failure, legacy output deviation, runtime absolute paths, ignored artifacts, and Git boundary are reported honestly.
- This review is only a C3 preflight, not R1 acceptance.

## Counts

- P0=0
- P1=2

## Required fixes before generation

1. Add a distinct C3 launch authorization/manifest record without changing C1/C2, and reject existing attempt directories before any write.
2. Pre-launch validate C3’s exact lock-2 command, one GPU, official `kitchen_int8`/FA configuration, fixed prompt hash/probe, exact 230/235 GiB thresholds, canonical output paths, and resolved project-local media tools.
3. Make the complete monitor lifecycle fail-closed: catch setup failures, require readiness/first sample, detect unexpected thread death, stop/join it before declaring success, then recheck monitor and safety events.
4. Add regression tests for setup failure, late monitor failure, nonzero/failed attempt result, and historical attempt-ID reuse; rerun verification and independent preflight review.

Decision=changes_required
