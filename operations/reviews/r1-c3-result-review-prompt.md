# R1 C3 Result Independent Review Prompt

You are an independent reviewer in a spawned PI process. Read only; do not edit files or execute generation.

Review whether Owner-authorized `C3-owner-exception` is a valid local MiniMax-H3 T2VA probe and whether its evidence honestly supports `feasible_with_constraints`. This is not full R1 acceptance because the Owner also requires a 4-GPU follow-up.

Read:

- `AGENTS.md`
- `Harness_manual.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/planning/r1-h3-feasibility-matrix.md`
- `operations/reviews/2026-08-21-r1-feasibility-report.md`
- `operations/reviews/2026-08-21-r1-c3-preflight-review-1.md`
- `operations/reviews/2026-08-21-r1-c3-preflight-review-final.md`
- `operations/reviews/2026-08-21-r1-verification.md`
- `operations/reviews/r1-verification-output.txt`
- `operations/reviews/r1-attempt-manifest.json`
- `operations/work_logs/2026-08-21-r1-h3-feasibility.md`
- `scripts/run_r1_h3_attempt.py`
- `scripts/verify_r1.py`
- `scripts/test_r1_hardening.py`
- `var/outputs/r1-feasibility/C3-owner-exception/metadata.json`
- `var/outputs/r1-feasibility/C3-owner-exception/request.json`
- `var/outputs/r1-feasibility/C3-owner-exception/submit-response.json`
- `var/outputs/r1-feasibility/C3-owner-exception/status.ndjson`
- `var/outputs/r1-feasibility/C3-owner-exception/ffprobe.json`
- `var/outputs/r1-feasibility/C3-owner-exception/ffprobe-independent.json`
- `var/outputs/r1-feasibility/C3-owner-exception/decode.stderr.txt`
- `var/outputs/r1-feasibility/C3-owner-exception/audio-astats.txt`
- `var/outputs/r1-feasibility/C3-owner-exception/blackdetect.txt`
- `var/outputs/r1-feasibility/C3-owner-exception/silencedetect.txt`
- `var/outputs/r1-feasibility/C3-owner-exception/contact-sheet.jpg`
- `var/outputs/r1-feasibility/C3-owner-exception/server.log`
- `var/outputs/r1-feasibility/C3-owner-exception/resources.csv`

Check:

1. exact authorization/lock/GPU/quantization/fixed-probe compliance
2. completed API status, content response, retained media and checksum consistency
3. independent ffprobe video+audio, duration/frame/audio properties and full decode evidence
4. host/GPU peaks, abort/hard-line status, monitor health, errors/Xid and cleanup claims
5. output location, ignore/Git and disk budget boundaries
6. whether visual/audio claims are bounded and do not overstate subjective quality
7. whether `feasible_with_constraints` is the right conclusion
8. whether 4-GPU remains pending rather than being misrepresented as proven

Output:

- `Review mode=spawned_pi_process`
- Findings grouped P0/P1/P2
- counts
- Decision exactly `valid_probe` or `changes_required`
- constraints and required fixes

P0/P1 must be zero for `valid_probe`.
