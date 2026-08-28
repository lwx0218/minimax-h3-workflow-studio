# MiniMax H3 Studio Functional MVP v0

## Status

- Status：rebaselined baseline
- Product foundation：pinned upstream ComfyUI backend + frontend
- Delivery source：[`operations/planning/rebaseline-plan-v1.md`](../../operations/planning/rebaseline-plan-v1.md)
- Historical R1：`accepted / feasible_with_constraints`

## Product Definition

H3 Studio 是运行在单台服务器上的本地单用户产品。用户从 Guided Mode 配置 H3 生成，或从完整 ComfyUI Advanced Canvas 编辑原生 Workflow；用户能观察执行并取得带立体声音频的可播放视频。ComfyUI 提供 graph、node、queue、execution 和 progress 语义，项目只在受控产品边界提供 H3 profiles、模板、入口和 Worker coordination。

## In Scope

- Guided Mode：常用 H3 输入、Generation Profile、提交、进度、取消（在 runtime 支持范围内）、预览和 Artifact retrieval。
- Advanced Canvas：完整 pinned ComfyUI frontend；原生 H3 workflow/API 的保存、加载、编辑和提交。
- H3：T2VA 与 FL2VA；模板、approved nodes/extensions 和 profile identity 可追踪。
- Runs/Artifacts：记录 workflow/API snapshot、profile、model/runtime identity、seed、timing、status、errors 和 media artifacts。
- Replica Execution：至少两个隔离 ComfyUI Workers 可同时执行独立 Runs；五张 A5000 可在测得安全并发上限下参与 queued work。
- Controlled Distribution：pinned upstream identities、dependency/asset manifest、allowlist、ignored runtime paths 和 reproducible start/recovery docs。

## Out Of Scope

- 独立 WorkflowDocument、Node Registry、ExecutionPlan、DAG Executor 或 proprietary executable graph format；
- 新建或 fork 的 graph canvas；
- ComfyUI 之外的平行 queue/execution semantics；
- 任意第三方节点安装或不受信任 workflow code/import/shell 字段；
- authentication、multi-tenancy、公网部署；
- Single-Request Multi-GPU 作为 MVP gate；它属于可选 Track X。

## Acceptance Criteria

1. 用户从 Guided Mode 可配置并提交 H3，看到 status/progress，并预览或取回最终 media。
2. 用户从 Advanced Canvas 可保存、加载、编辑、提交原生 ComfyUI H3 Workflow。
3. 至少一个 T2VA 和一个 FL2VA Run 从产品 frontend 发起，并生成可播放视频和 stereo audio。
4. 至少两个 Worker 同时完成两个独立有效 Runs；这不是一个请求跨 GPU 拆分。
5. 五个 A5000 都可通过 queued work 被寻址，实际并发受 measured host-RAM safety limit 约束。
6. 每个 Run 可反查其 snapshot、profile、model/runtime identity、seed、timing、status 和 Artifacts。
7. 取消、失败、清理、重启恢复和 no-worker fail-closed 行为有证据并记录边界。
8. Draft/Balanced/Final profiles 有分别的质量、资源和性能证据；优化不被写成 lossless 等价。
9. 默认不暴露任意第三方节点、任意文件路径、secret 或可执行字段。
10. runtime data、weights、secrets、cache、logs、database 和 media 不进入 Git；README 提供 start/recovery/known-limit 文档。

Backend CLI/API generation 是 supporting engineering evidence，不能替代 criteria 1–3。

## Runtime Boundary

- ComfyUI Workflow/API 是 graph execution 的 source of truth。
- Control Plane 只协调 Workers、Runs、progress 和 Artifacts，不实现第二套 graph executor。
- Worker 是绑定到一个 GPU 或明确 GPU group 的隔离 ComfyUI execution service。
- Replica Execution 与 Single-Request Multi-GPU 分别记录、分别验收。
- 默认服务 bind `127.0.0.1`；模型外置，项目运行数据在 `var/`。

## Superseded Legacy Clauses

本文件原先关于独立 workflow/node/DAG/canvas、单并发 FIFO 和“ComfyUI 仅为参考”的 future-plan 条款已由 [`operations/planning/rebaseline-plan-v1.md`](../../operations/planning/rebaseline-plan-v1.md) **SUPERSEDED**。旧文档不再定义未来实现；历史 R1 证据仍保留。
