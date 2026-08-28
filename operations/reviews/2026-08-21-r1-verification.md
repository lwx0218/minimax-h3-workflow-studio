# R1 Automated And Regression Verification

- Date：2026-08-21
- Round：R1
- Round status：`blocked`（4-GPU route decision required）
- Local feasibility：`feasible_with_constraints`（valid C3）
- Command：`python3 scripts/verify_r1.py --runtime-evidence`
- Exit：0
- Full output：`operations/reviews/r1-verification-output.txt`

## Static Checks

- HEAD contains baseline `aa2c2b1`
- `git diff --check`
- candidate/ignore/path/media/weight/database policy passes
- exactly 2 dependency locks
- runner/verifier/media verifier/hardening tests compile and pass
- Ledger/report/work log consistently record `blocked` round status and constrained single-card feasibility
- B1 236.91 GiB and G4 235.87 GiB hard-line breaches are explicitly disclosed

## Hardening Checks

- duplicate manifest IDs and evidence overwrite rejected
- exact argv plus independently pinned complete G4 contract digests
- native SGLang backend、source commit/clean tree、model config fingerprints
- canonical allowlisted request digest；external source cannot inject sampler/cache fields
- contract-sensitive inherited environment rejected
- resource monitor setup/sampling/thread/late failure fail closed
- session-wide worker cleanup and post-stop GPU gating
- independent media command/tool/checksum provenance

## Runtime Accounting

- 9 runtime execution records：6 original profile slots + 1 dependency preflight + C3 + initial G4
- generation submissions：3（C1、C2、C3）；G4 submitted none
- C3 Owner exception retained as slot 3；not rewritten into original matrix
- G4 AdaLN proposal retained as `preflight_rejected` and correctly has no runtime directory
- lock IDs remain only 1/2
- disk delta approximately 15.16 GiB < 100 GiB

## C3 Valid Probe

- terminal `completed`、content HTTP 200、retained 1097858-byte MP4
- SHA-256 `bc7e0ad866d69fac5edc595fe7cb744007f278bff4816ddb18fc417739a26d27`
- H.264 1344×768/24fps/124 frames + AAC LC stereo 32kHz
- full decode passes；independent command provenance passes
- load 265.110 s；generation 1841.575 s
- GPU 23881 MiB；host 181.88 GiB；72°C；no safety/monitor error

## Four-GPU Disposition

- Lock-2 default and CUMEM-off collectives timed out；P2P-disabled 2/4-rank all-reduce passes
- `G4-TP4Q` reaches native model loading but duplicated transformer CPU staging triggers 230 GiB abort
- observed host peak 235.87 GiB，actual hard-line breach；no health/request/media
- delayed retained cleanup snapshot confirms no residual process and 1 MiB/GPU
- proposed quantized AdaLN-online correction is statically recognized as installed-source incompatible and is accepted only in `preflight_rejected` state

## Interpretation

Automated verification proves the evidence and control decision，not 4-GPU success。Single-card local T2VA is valid with constraints；the new 4-GPU requirement remains blocked pending Owner route selection。
