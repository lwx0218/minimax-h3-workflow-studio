# Governance Loop Template

先过固定前置 gate，再按需展开。

## Gate

- Project: `MiniMax H3 Workflow Studio`
- Goal:
- Source of truth:
- Entry points:
- Constraints:
- Outputs:
- Route: `trivial` | `plan` | `needs-extension`

## Trivial Shortcut

当 `Route = trivial` 时，优先使用这组简写，而不是强行展开完整闭环：

- Execute:
- Verify:
- Result:
- Next step:

## Expanded Plan

当 `Route = plan` 时，再补齐以下内容：

### Plan

- Scope for this round:
- Files expected to change:
- Validation level:

### Execute

- Planned implementation notes:

### Verify

- Commands or checks run:
- Result:
- Known gaps:

### Closeout

- Files changed:
- User-visible outcome:
- Next step:

### Portability

- Relative-path assumptions:
- Local-only config:
- Absolute-path risks removed or deferred:

## Needs Extension

当 `Route = needs-extension` 时，记录：

- Missing capability:
- Why the starter boundary is reached:
- Suggested next action:
