Review mode=spawned_pi_process

## P0

None.

## P1

1. **`G4-TP4Q-adaln` is incompatible with the pinned `kitchen_int8` quantization.**
   - The manifest combines `--quantization kitchen_int8` with `--minimax-h3-adaln-online true`.
   - `TransformerLoader` passes both the resolved runtime quantization config and `adaln_weight_files` into `MiniMaxH3DiTModel`.
   - `MiniMaxH3DiTModel.__init__` explicitly raises when AdaLN weight files are used with any non-null quantization config: `MiniMax H3 AdaLN cache is only compatible with unquantized weights`.
   - The installed CLI help independently states that online AdaLN rebuild “Requires unquantized weights.”

   Therefore this contract is known to fail during model construction, before health or request submission. The TP-sharded rebuild itself excludes AdaLN weights and preserves unquantized projection semantics, but it cannot justify this `kitchen_int8` attempt.

   **Required before execution:** do not launch this contract. Mark the correction blocked, or obtain Owner authorization for a source-supported contract change and repeat preflight. The verifier should also reject this incompatible flag combination.

## P2

None.

## Assessment

- Initial G4 evidence honestly records the 230 GiB abort, 235.87 GiB hard-line breach, and no request/generation.
- Apart from the invalid flag combination, the correction changes only the AdaLN flag, output ID/path, and abort threshold to 220 GiB.
- Session-wide cleanup, post-stop success gating, and the one-correction limit are present.

## Counts

- P0=0
- P1=1
- P2=0

Decision=changes_required
