# MiniMax H3 Studio

MiniMax H3 Studio is a controlled, local environment for authoring and running MiniMax-H3 generation workflows. It reuses ComfyUI as its workflow foundation and adds an H3-specific product surface plus multi-GPU control.

## Product

**H3 Studio**:
The complete H3-focused product experienced by the user, including guided generation, advanced workflow editing, job execution, and generated artifacts.
_Avoid_: Independent Workflow Studio, ComfyUI clone

**ComfyUI Foundation**:
The pinned upstream ComfyUI backend and frontend that provide the authoritative graph, node, queue, and execution semantics for H3 Studio.
_Avoid_: Reference UI, optional backend, borrowed canvas

**H3 Distribution**:
The controlled combination of the ComfyUI Foundation, approved H3 model assets, workflow templates, extensions, configuration, and launch behavior shipped by this project.
_Avoid_: ComfyUI fork, custom frontend

**Guided Mode**:
The simplified H3 experience that exposes selected workflow inputs and outputs without requiring users to edit the full graph.
_Avoid_: Simple UI, basic mode

**Advanced Canvas**:
The full ComfyUI graph editor made available for inspecting and editing H3 Workflows.
_Avoid_: Custom canvas, Studio canvas

## Workflow And Generation

**H3 Workflow**:
A native ComfyUI workflow and its API representation, accompanied by Studio metadata when identification or product presentation requires it.
_Avoid_: WorkflowDocument, Studio DAG, proprietary workflow contract

**Generation Profile**:
A named, traceable quality and performance policy that selects compatible weights, precision, sampler, step count, attention, cache, resolution, and runtime behavior.
_Avoid_: Mode, preset, backend parameters

**Draft Profile**:
A Generation Profile optimized for iteration speed and allowed to use explicitly disclosed approximate acceleration.
_Avoid_: Fast mode, low-quality mode

**Balanced Profile**:
A Generation Profile intended for normal interactive use, balancing generation time and perceptual quality.
_Avoid_: Default mode, production mode

**Final Profile**:
A Generation Profile optimized for output quality and used as the product's high-quality path; it may take longer than interactive profiles.
_Avoid_: Lossless mode, full mode

**Run**:
One submitted execution of an H3 Workflow with an immutable snapshot of its inputs, Generation Profile, model identities, seed, runtime identity, and resulting artifacts.
_Avoid_: Prompt, task, session

**Artifact**:
A media file or diagnostic record produced by a Run and traceable back to that Run.
_Avoid_: Output, result file

## Compute

**Worker**:
An isolated ComfyUI execution service bound to one GPU or to one explicitly declared GPU group.
_Avoid_: Backend, instance, card

**Worker Pool**:
The set of Workers available to execute independent Runs concurrently.
_Avoid_: Multi-GPU, cluster

**Control Plane**:
The thin coordination boundary that discovers Workers, assigns Runs, observes progress, and records outcomes without redefining ComfyUI graph semantics.
_Avoid_: Orchestration backend, DAG executor, scheduler service

**Replica Execution**:
Using multiple Workers to execute independent Runs at the same time, increasing aggregate throughput.
_Avoid_: Multi-GPU inference, parallel workflow

**Single-Request Multi-GPU**:
Using more than one GPU for one H3 generation request through a model-parallel topology such as tensor or sequence parallelism.
_Avoid_: Worker Pool, multi-card mode

## Delivery

**Functional MVP**:
The first user-visible end-to-end H3 Studio release in which a user submits from Guided Mode or Advanced Canvas, observes execution, and receives a valid playable H3 video with stereo audio and traceable Artifacts; it also provides Replica Execution on at least two Workers. A backend-only CLI or API generation does not satisfy Functional MVP.
_Avoid_: Prototype, UI MVP

**Performance Acceptance**:
The final evidence gate that establishes measured Draft, Balanced, and Final Profile behavior on the target A5000 host.
_Avoid_: Feasibility, benchmark only

**Evidence Probe**:
A bounded, reproducible execution used to decide a runtime or deployment question; it is not automatically a product Generation Profile.
_Avoid_: Experiment, benchmark claim
