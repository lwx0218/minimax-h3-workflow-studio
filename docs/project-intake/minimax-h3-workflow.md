# 项目 Intake：MiniMax H3 Workflow Studio

## Metadata

- Project：MiniMax H3 Workflow Studio
- Project slug：`minimax-h3-workflow`
- Source of truth：本仓库
- Governance mode：external-first、PI-native、按需进入 Plan
- Project root：`.`
- Governance entry：`AGENTS.md`、`.pi/`
- PI readiness：`runtime-ready`
- Application readiness：`bootstrap-ready`
- 当前阶段：Phase 0（需求澄清与目录约定）
- 目标部署地区：中国
- 首版目标用户：单机、单用户；保留后续产品化边界

## 项目目标

构建一个以 MiniMax-H3 为核心的视频与音频生成工作流编排项目。产品形态参考 ComfyUI 的节点画布、类型化连线、工作流保存和异步执行体验，但采用本项目自己的 workflow contract、节点接口和运行时边界，不 fork ComfyUI，也不承诺兼容其 workflow 或 custom nodes。

第一版 MVP 聚焦：

- 本地 MiniMax-H3 推理
- T2VA 与 FL2VA
- 基础 DAG 编辑闭环
- 单用户任务队列
- 可追踪的运行快照与项目内产物管理

## Source of Truth

按优先级排序：

1. 本仓库中的 intake、MVP spec、架构文档和版本化 contracts
2. MiniMax-H3 官方仓库、模型卡、官方部署文档与许可证
3. 实际锁定的 SGLang/H3 运行时版本及其 API 行为
4. ComfyUI：仅作为产品和架构参考，不作为本项目 contract

已调研的参考基线：

- MiniMax-H3 upstream commit：`d21241f0a4b3acbb34c97dae47fa417b7065e438`
- ComfyUI upstream commit：`5ab2f7a2d676c1fb7b410c22e82e2ed8f217b56c`

后续实现不应静默跟随上游变化；升级参考版本时需要记录影响。

## 当前环境基线

- 本地已有约 465G 的 MiniMax-H3 模型快照
- 5 × NVIDIA RTX A5000，每张约 24 GiB 显存
- NVIDIA driver：`580.173.02`
- 系统内存：约 251 GiB
- GPU 间主要通过 PCIe 通信，当前拓扑未显示 NVLink
- 当前尚未安装项目专用 SGLang、Diffusers 或 vLLM 环境

A5000 不是当前官方文档明确验证的 H3 拓扑，因此“可发现模型文件”不等于“推理可用”。正式开发 UI 前必须先完成真实 T2VA 推理可行性测试。

## 本地模型使用方式

- 通过本地未提交文件 `.env.local` 中的 `H3_MODEL_PATH` 指向模型快照根目录
- 快照根目录应包含 repository-level `model_index.json` 以及 `FL2VA/`、`Ref2VA/` 等组件
- 不在已提交文档、脚本或源码中硬编码宿主机绝对路径
- 不复制模型到仓库，不提交权重、checkpoint、ONNX、GGUF 或模型缓存
- H3 推理运行时与轻量 orchestration 后端使用两个独立的项目内虚拟环境
- 首选将 H3 作为独立 SGLang 服务运行，应用后端通过 adapter 调用

H3 首次接入顺序：

1. 真实本地 T2VA 推理验证
2. T2VA adapter
3. 首帧、尾帧和首尾帧 FL2VA
4. Ref2VA 后置

## H3 能力边界

当前开源权重主要覆盖 H3-Base 768p：

- `t2va`：文本到带音频视频
- `fl2va`：首帧/尾帧条件到带音频视频
- `ref2va`：图片、视频、音频参考到带音频视频

H3-Context-IR 与 H3-Regenerate-2K 当前不是本地开源模块。MVP 提供：

- 原始 H3 Prompt 输入
- 简单本地 Prompt Builder

本地 Builder 不得宣称等价于官方 Context-IR。官方 Context-IR 和 2K API 仅作为后续可选节点，不构成本地 MVP 的强依赖。

## ComfyUI 参考范围

借鉴：

- 节点画布和类型化端口
- Workflow JSON 保存、加载和分享思路
- 服务端节点注册、图校验和 DAG 执行
- 异步队列、进度、取消和产物预览

不照搬：

- 不 fork 或复制 ComfyUI GPL 代码
- 不使用 ComfyUI 内部 prompt/execution JSON 作为持久 contract
- 不承载完整 diffusion 模型、采样器和加载器生态
- MVP 不扫描或执行任意第三方 Python 节点
- 不承诺 ComfyUI workflow/custom nodes 兼容
- 不让画布 UI 数据直接决定后端执行语义

## 约束条件

### 运行与存储

- MVP 为单机、单用户应用
- Web 服务默认只监听 `127.0.0.1`，通过 SSH 端口转发访问
- H3 同时只执行一个任务，其余任务按 FIFO 排队
- Workflow 与运行元数据存 SQLite
- 上传、输出、缓存、日志和临时文件统一位于项目内 `var/`
- 大型 JSON 快照和日志按阈值压缩；已压缩媒体不重复压缩
- 运行快照需记录 workflow、节点版本、参数、最终 prompt、seed、模型标识、后端参数、耗时和错误

### 版本控制与可移植性

- 模型权重和运行产物不得进入 Git
- `.env.local`、虚拟环境、数据库、缓存和媒体产物不得进入 Git
- 提交内容优先使用相对路径
- 不把运行数据写散到系统盘或用户主目录缓存
- 驱动、CUDA 和现有外部模型目录属于明确例外

### 许可证

当前目标部署地区为中国；按已阅读的 MiniMax H3 Community License 文本，中国不属于 Excluded Territories。正式发布或部署前仍需重新核验最新许可证、Acceptable Use Policy 和适用法律。该记录不构成法律意见。

项目近期不公开发布，暂不添加项目级开源许可证。公开前需进行依赖和许可证审查。

## MVP 不包含

- Ref2VA
- 官方 Context-IR 或 2K 的强制依赖
- ComfyUI workflow 兼容
- 第三方插件安装和插件市场
- 登录、多用户、多租户或公网部署
- 子图、循环、条件分支和批处理矩阵
- 分布式队列或按 GPU 拆分并发任务

## 开发与质量模式

当前 MVP 固定为 R1–R7，详细 Round Ledger 见 `operations/planning/initialization-plan.md`。

每轮由 Builder 执行实现，由自动测试提供机械验证，并在 checkpoint commit 前执行 Independent Review。Bug、Review 和复验保留在原 round；只有 Owner 批准的 Goal/Spec 变化才能重新基线。

Owner 不负责逐项发起 Review 或 Bug Fix，只在技术路线阻塞、范围变化、危险操作和最终体验验收时介入。项目操作、compact 和 session handoff 见 `Harness_manual.md`。

## 主要风险与待验证项

1. 5×A5000 上 H3 的显存、主存和推理速度是否可接受
2. SGLang 在该拓扑上的最佳 TP/Ulysses/offload 配置
3. 运行中任务取消的实际后端能力
4. 本地 Prompt Builder 与官方 Context-IR 的质量差距
5. MiniMax-H3、SGLang 和 ComfyUI 上游接口仍在快速演进

## Durable Outputs

- 项目驾驭手册：`Harness_manual.md`
- MVP spec：`docs/specs/mvp-v0.md`
- 架构建议：`docs/architecture/architecture-v0.md`
- 开发质量合同：`docs/development/process.md`
- Master Plan：`operations/planning/initialization-plan.md`
- 工作记录：`operations/work_logs/`
- Review evidence：`operations/reviews/`

## 下一步

先完成真实本地 T2VA 技术验证，再冻结 workflow v1 和节点执行 contract。不要在推理可行性未知时先大规模开发工作流 UI。
