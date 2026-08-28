---
status: accepted
date: 2026-08-28
---

# Use ComfyUI as the Studio foundation

MiniMax H3 Studio will use pinned upstream ComfyUI backend and frontend releases as its authoritative graph, node, queue, and execution foundation. We will customize that foundation through approved H3 workflow templates, model profiles, App/Guided Mode, and extensions, because the product goal is to reuse ComfyUI's mature workflow capability and avoid rebuilding a canvas, node registry, DAG executor, queue, and their client-server integration.

## Considered options

- Build an independent Workflow Studio with a proprietary WorkflowDocument and a custom frontend.
- Fork and immediately remove unrelated ComfyUI functionality.
- Reuse complete, pinned ComfyUI releases and keep project-specific code at the extension and control-plane boundaries.

The third option was selected. The first duplicates mature functionality and had already caused the development plan to spend effort on contracts and UI work that were not part of the owner's actual goal. The second creates a large GPL-maintenance and upstream-merge burden before product usage proves that a fork is needed.

## Consequences

- Native ComfyUI workflow/API JSON is the MVP workflow source of truth. The project will not create a parallel executable graph contract.
- The project will not build its own canvas, node registry, DAG executor, or single-process queue for the MVP.
- The initial product surface will use Guided Mode for common H3 generation and expose the full ComfyUI canvas for advanced editing.
- Only approved model assets, templates, nodes, and extensions are included in the controlled H3 Distribution. Arbitrary third-party node installation remains outside the MVP.
- Multi-GPU throughput is implemented with isolated ComfyUI Workers plus a thin Control Plane or a proven existing controller. Single-request model parallelism remains a bounded deployment experiment.
- The prior SGLang feasibility evidence is retained as evidence and as a quality/reference route, but the historical 30.6-minute C3 probe is not the default interactive product baseline.
- ComfyUI backend and frontend are GPLv3. Local internal use is compatible with the present goal; any future distribution of modified ComfyUI components requires a dedicated license-compliance review. This record is not legal advice.
