# MiniMax H3 Studio Architecture v0

## Status And Authority

本文描述 rebaselined target architecture，不代表产品代码已经实现。权威顺序见 [`CONTEXT.md`](../../CONTEXT.md) 和 [`operations/planning/rebaseline-plan-v1.md`](../../operations/planning/rebaseline-plan-v1.md)。

## Core Decision

Pinned upstream ComfyUI backend and frontend provide the authoritative graph editor, node system, workflow/API format, queue, execution engine, progress protocol and memory/runtime semantics. H3 Studio customizes through approved templates, Generation Profiles, Guided Mode, supported settings/extensions and a thin coordination boundary; it does not recreate those semantics.

## System Context

```text
User -> Guided Mode or Advanced Canvas -> pinned ComfyUI Foundation
                                      -> thin Control Plane
                                      -> Worker Pool (isolated ComfyUI Workers)
                                      -> Artifacts / Run metadata
```

- Guided Mode is the common path.
- Advanced Canvas is the complete pinned ComfyUI frontend, not a project-owned canvas.
- Control Plane discovers Workers, assigns independent Runs, observes progress, correlates Artifacts and handles supported recovery.
- A Worker is isolated by GPU binding, port, temp/output namespace, logs and process lifecycle.

## Native Workflow Boundary

H3 Workflow is native ComfyUI workflow JSON plus API representation and only the minimum Studio metadata needed for profile/run presentation. The project does not define a parallel executable graph model, node registry, compiler, topology executor or application FIFO. ComfyUI remains responsible for node resolution, validation, graph execution and queue behavior.

Studio-owned records are operational, not a replacement execution contract:

```text
Run = immutable snapshot of native Workflow/API + inputs + profile + model/runtime identity + seed + artifacts
Artifact = media or diagnostic record traceable to one Run
```

## Runtime And Compute

### Worker Pool

- stable Worker identity and explicit GPU binding;
- health/capability discovery;
- independent Run assignment and progress/artifact correlation;
- safe concurrency based on measured host RAM and runtime behavior;
- isolated ports, temporary paths, logs and output namespaces;
- stale lease/process cleanup, cancellation and fail-closed no-worker behavior.

### Two Different Multi-GPU Concepts

**Replica Execution** uses multiple Workers for independent Runs and is required by Functional MVP. **Single-Request Multi-GPU** uses a model-parallel topology for one Run and is optional Track X. They have separate evidence, safety limits and acceptance claims.

### Profiles

Draft, Balanced and Final are hypotheses until Runtime Decision and Multi-Worker evidence. Quantization, pruning, Turbo, cache and approximate attention must be explicitly disclosed and compared with a quality/reference route; community claims never substitute for target-host evidence.

## Product Layers

1. **ComfyUI Foundation** — pinned upstream server/frontend and native workflow/API semantics.
2. **H3 Distribution** — approved model assets, templates, profiles, settings, extensions and reproducible launch behavior.
3. **Guided Mode** — constrained presentation of approved workflow inputs/outputs.
4. **Control Plane** — Worker discovery, Run assignment, status/progress, artifact correlation and recovery only.
5. **Evidence/Operations** — immutable Run snapshots, model/runtime identity, logs and media validation.

No layer may introduce arbitrary node installation, workflow import execution, shell/import fields or a second graph runtime.

## Security And Portability

- default bind is `127.0.0.1`;
- only approved nodes/extensions are enabled;
- workflow fields cannot select arbitrary Python/import/shell execution;
- model weights, runtime data, caches, databases, logs and media remain outside Git;
- project paths are relative or environment-driven; outputs and temp data remain under project `var/` where project-owned;
- GPL components and model/third-party licenses receive a dedicated inventory before distribution.

## Delivery Boundaries

- Baseline Reset: documentation and source-of-truth alignment only.
- Runtime Decision: one bounded A5000 ComfyUI H3 profile plus SwarmUI/thin Control Plane disposition.
- Single-Worker Product: controlled distribution and one user-visible vertical slice.
- Multi-Worker MVP: Replica Execution, five-GPU pool operations and final acceptance.

No product implementation starts before Baseline Reset commit and post-commit verification. Track X cannot delay these checkpoints.

## Superseded Legacy Clauses

The former independent WorkflowDocument/Node Registry/ExecutionPlan/DAG/canvas architecture, separate H3Backend-first runtime, ComfyUI-reference-only boundary, and single-concurrency FIFO future model are **SUPERSEDED** by [`docs/adr/0001-use-comfyui-as-studio-foundation.md`](../adr/0001-use-comfyui-as-studio-foundation.md) and [`operations/planning/rebaseline-plan-v1.md`](../../operations/planning/rebaseline-plan-v1.md). Historical documents retain facts but no future authority.
