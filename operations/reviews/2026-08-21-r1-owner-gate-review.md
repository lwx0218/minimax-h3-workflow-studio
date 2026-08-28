Review mode=spawned_pi_process

## P0

None.

## P1

None.

All historical P1 findings are fixed or safely dispositioned. The incompatible `kitchen_int8 + AdaLN-online` contract remains `preflight_rejected`, has no runtime directory, and is rejected by the verifier in any executable state.

## P2

1. `operations/reviews/2026-08-21-r1-feasibility-report.md` still says R1 remains `in_progress` after C3. This is stale chronology; current authoritative status is `blocked`.
2. The report’s Budget Accounting calls the AdaLN correction “pending”; it is actually `preflight_rejected` and was not executed.
3. The Resource Summary says every attempt ended without residual GPU processes, but G4’s immediate snapshot found four terminating workers. Qualify this as immediate residuals followed by a clean delayed snapshot.

These documentation inconsistencies do not overturn the primary evidence:

- C3 is a valid constrained local T2VA probe; media/decode/resource evidence supports `feasible_with_constraints` without subjective-quality acceptance.
- G4 explicitly breached the 235 GiB hard line and submitted no request.
- External references are correctly separated from local acceptance evidence and do not authorize a silent backend switch.
- The four Owner routes are technically meaningful, with any new execution requiring a fresh source-supported contract and preflight.
- R1 must remain blocked; no acceptance commit and no R2 before Owner decision.

## Counts

- P0=0
- P1=0
- P2=3

Decision=blocked_owner_decision

Recommendation: Owner selects the route; then correct the three stale report statements and require fresh preflight before any further GPU execution.
