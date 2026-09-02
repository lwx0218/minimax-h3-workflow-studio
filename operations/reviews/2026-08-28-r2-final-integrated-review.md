# R2 Final Integrated Review

- Checkpoint：R2 — Runtime Decision
- Status：`accepted_candidate_before_commit`
- Basis：R2 work log、successful cold/warm ComfyUI H3 probe、SwarmUI controller spike、independent Class-A review
- Decision：`pass_to_commit`

## Acceptance Mapping

| R2 acceptance item | Evidence | Result |
|---|---|---|
| 至少一个 valid ComfyUI H3 output on A5000 | `var/logs/r2-runtime-decision/probe-20260902T022149Z/result.json` cold/warm phases | PASS |
| Stack identity and reproducible command recorded | `operations/work_logs/2026-09-02-r2-runtime-decision.md` Installed / Pinned Runtime + command | PASS |
| Cold/warm timing recorded | cold 285.242 s；warm 260.240 s；server prompt 280.73 s / 256.51 s | PASS |
| Media not black/noise/corrupt and has video+stereo audio | ffprobe/decode/blackdetect/silencedetect/frame sheet evidence | PASS |
| Resource safety and cleanup | peak host 55.062 GiB；GPU0 22963 MiB；71°C；no violations；post-run compute apps empty | PASS |
| Controller route decided | SwarmUI basic spike + negative disposition; decision `build_thin_control_plane` | PASS |
| No scope drift | No Guided Mode/Control Plane product code/Multi-Worker product code; no custom graph runtime | PASS |
| Runtime/weights/media excluded from Git | `/var/*` ignored; weights external; candidate files are docs + evidence tooling | PASS |

## Integrated Findings

- P0：0
- P1：0
- P2：1（script automatic media predicate should be strengthened if reused after R2; accepted as non-blocking because current R2 evidence and independent review explicitly validate the full media gate）

## Controller Decision

R2 chooses `build_thin_control_plane` for R3/R4. SwarmUI was not adopted because the bounded spike only validated backend discovery/status/failure reporting and did not prove reliable H3 workflow submission、progress、artifact correlation for the RH-plugin route. This decision remains inside the approved architecture: the future Control Plane may coordinate Workers/Runs/progress/artifacts only and must not become a second graph executor.

## Commit Gate

Proceed to scoped checkpoint commit after:

1. `git diff --check` PASS;
2. `python3 -m py_compile scripts/run_r2_h3_comfy_probe.py` PASS;
3. `git check-ignore` confirms `var/` runtime/log/output/media ignored;
4. staged diff contains only R2 candidate docs/evidence tooling and ledger update;
5. post-commit fast checks pass.
