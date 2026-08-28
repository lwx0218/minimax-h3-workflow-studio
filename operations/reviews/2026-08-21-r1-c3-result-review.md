Review mode=spawned_pi_process

## Findings

### P0

None.

### P1

None.

### P2

1. **Cleanup claim lacks a retained post-stop GPU/process snapshot.**
   `metadata.json` and `server.log` prove the server stopped, but do not independently prove the reported “no residual GPU process / 1 MiB used” state.

2. **Independent media diagnostics lack exact command provenance.**
   `ffprobe-independent.json`, audio/black/silence analyses, and the contact sheet support the reported properties, but their exact commands, exit codes, and input checksum are not retained together.

3. **FlashAttention wording should reflect component fallback.**
   The authorized `--attention-backend fa` configuration was used, but `server.log` reports that head size 72 cannot use FlashAttention and lists `torch_sdpa, fa` for the text encoder. Do not describe the entire execution as universally FlashAttention-backed.

## Counts

- P0=0
- P1=0
- P2=3

## Assessment

- Authorization and exact launch contract passed: distinct Owner exception, lock 2 executable, GPU 0 only, `kitchen_int8`, FA requested, fixed FL2VA/T2VA 768p/16:9/5-second/seed-0/50-step probe, and 230/235 GiB thresholds.
- API reached `completed`; content returned HTTP 200. Retained MP4 is 1,097,858 bytes, with checksum consistently recorded and verifier-confirmed against the media.
- Primary and independent ffprobe evidence agree: H.264 1344×768, 24 fps, 124 frames, 5.166667 seconds; AAC LC stereo, 32 kHz, 5.175 seconds. Full video+audio decode exited 0.
- Peaks are supported: 23,881 MiB GPU, 181.88 GiB host used, 173.78 GiB process RSS, 72°C. Neither abort nor hard line triggered; monitor failure, Xid, OOM, and fatal server-error evidence is absent.
- Output remained under `var/outputs/r1-feasibility/C3-owner-exception/`; ignore/candidate checks passed and disk delta remained about 15.16 GiB, below 100 GiB.
- Visual/audio statements are suitably bounded to sampled-frame coherence, black/silence detection, and signal statistics; they do not establish subjective quality or full prompt adherence.
- `feasible_with_constraints` is correct because only official `kitchen_int8` succeeded, inference took about 30.6 minutes, GPU headroom was narrow, and host offload was substantial.
- R1 remains `in_progress`; no evidence claims that a 4-GPU topology, rate, resource, or quality comparison has succeeded.

## Constraints

- Single A5000, official mixed `kitchen_int8` path only.
- Approximately 23.3 GiB GPU peak and 181.9 GiB host-used peak.
- Approximately 30.6-minute inference for 5.17 seconds of output.
- No subjective quality acceptance or stability/throughput series.
- Four-GPU follow-up remains mandatory and unproven.

## Required fixes

No C3 rerun is required. Before R1 closeout:

1. Retain and verify a post-cleanup `nvidia-smi` process/memory snapshot.
2. Record exact independent media-analysis commands, tool versions, exit codes, and input checksum.
3. Clarify the component-level FlashAttention fallback in the report and follow-up comparison.

Decision=valid_probe
