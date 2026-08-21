# MiniMax H3 Workflow Studio 架构建议 v0

## 状态与目的

本文是 MVP 的第一版架构基线，服务于 `docs/specs/mvp-v0.md`。它定义边界和演进方向，不等同于已实现 contract。真实 H3 推理可行性验证完成后，才能冻结 workflow v1 和 H3 adapter 的具体字段。

## 设计原则

1. H3-first，而不是通用 diffusion-first
2. 推理服务与 orchestration 进程隔离
3. 语义 graph 与画布 UI 数据隔离
4. Workflow 与 Run 分离
5. 单机简单路径优先，保留明确扩展点
6. 所有运行数据项目内聚
7. 不信任任意第三方节点代码
8. 先用真实推理证据决定部署方式

## 系统上下文

```text
Browser
  │  REST + SSE
  ▼
Frontend ──────────────► Backend API
                           │
                           ├── Workflow / Node Registry
                           ├── Validator / Compiler
                           ├── SQLite-backed Queue / Executor
                           ├── Artifact Store ─────► ./var/
                           │
                           └── H3Backend Adapter
                                   │
                                   ▼
                              SGLang Service
                                   │
                                   ▼
                           External local model snapshot
```

模型权重位于仓库外；应用数据库、运行快照、缓存、上传和输出位于仓库内 `var/`。

## 建议技术栈

### Backend

- Python 3.12
- FastAPI
- Pydantic
- SQLite
- 独立 worker 命令，但与 API 共用代码包和 SQLite queue

### Frontend

- React
- TypeScript
- Vite
- `@xyflow/react`
- 由后端 node schema 驱动通用参数表单

### H3 Runtime

- 首选 SGLang 独立服务
- 与 backend 使用不同的项目内 Python 虚拟环境
- 本地模型路径通过 `.env.local` 提供
- 真实部署参数由 Phase 1 可行性测试决定

## 建议目录

```text
backend/
├── pyproject.toml
├── src/h3_workflow/
│   ├── api/
│   ├── domain/
│   ├── execution/
│   ├── nodes/
│   │   ├── builtin/
│   │   └── registry.py
│   ├── inference/
│   │   ├── base.py
│   │   ├── mock.py
│   │   └── sglang.py
│   └── storage/
└── tests/

frontend/
├── package.json
└── src/
    ├── api/
    ├── components/nodes/
    └── features/
        ├── workflow/
        └── runs/

contracts/
├── workflow/v1.schema.json
└── node/v1.schema.json

workflows/examples/
configs/examples/
var/
```

这些业务目录按阶段创建，不在 Phase 0 一次性生成空骨架。

## Workflow / Graph 数据模型

### WorkflowDocument

建议的持久语义：

```text
schemaVersion
id
name
revision
nodes[]
  id
  type
  nodeVersion
  params
edges[]
  id
  from: nodeId + port
  to: nodeId + port
outputs[]
ui
  positions
  groups
  viewport
```

约束：

- `node.id` 在 workflow 内唯一
- `type + nodeVersion` 必须能在 registry 中解析
- 边只连接声明的 output/input port
- 类型必须兼容
- MVP 禁止有向环
- `ui` 可缺省，不参与 execution plan
- Workflow 运行时必须创建 revision 快照，不能直接引用可变草稿

### ExecutionPlan

后端将 WorkflowDocument 校验并编译为不可变 ExecutionPlan：

- 解析节点版本
- 解析输入来源和常量
- 完成拓扑排序
- 标记 output nodes
- 计算 capability 和资源需求
- 拒绝未知节点、端口错误、缺失输入和环路

前端不能直接提交任意可执行 Python 名称。

### RunRecord

Run 独立于 Workflow：

```text
runId
workflowId
workflowRevision
status
queuePosition
backend
createdAt / startedAt / finishedAt
nodeRuns[]
artifacts[]
error
```

状态建议：

```text
queued -> preparing -> running -> succeeded
                            ├── failed
                            ├── cancelling -> cancelled
                            └── interrupted
```

服务重启时，未明确完成的 `preparing/running/cancelling` 标记为 `interrupted`，不自动重跑。

## 节点扩展机制

### Node Definition

节点定义至少包含：

- 稳定 `type`
- 语义 `version`
- display name、category、description
- typed input/output ports
- 参数 JSON Schema
- capability/resource hints
- async execute contract

概念接口：

```text
execute(context, inputs, params) -> NodeResult
```

`context` 提供：

- run/node identity
- structured logger
- cancellation token
- artifact store
- configured H3 backend
- progress reporter

### MVP 策略

- 只允许显式注册内置节点
- 节点 metadata 可暴露给前端
- 不扫描任意目录
- 不允许 workflow 指定 import path
- 不运行任意 shell

### Phase 3

在内置接口稳定后，通过 Python entry point 和 allowlist 开放可信插件。插件隔离、签名、独立环境或市场不在 MVP 中。

## MiniMax-H3 推理接入层

### H3Backend

建议能力：

```text
health()
capabilities()
submit(request)
get_status(job_id)
cancel(job_id)
get_result(job_id)
```

统一请求应表达业务语义，不直接泄漏某个 provider 的原始 JSON：

- task：t2va / fl2va
- prompt
- conditions
- target
- seed
- output policy

adapter 负责转换为 SGLang API。

### 实现顺序

1. `MockH3Backend`
2. `SGLangH3Backend`
3. 可选 MiniMax hosted API backend
4. 只有实测需要时才评估 ComfyUI backend

### Variant

- `fl2va` 服务覆盖 T2VA 和 FL2VA
- `ref2va` 独立 variant 后置
- MVP 不同时常驻两个大型 variant

### Prompt

Prompt Builder 仅做透明、可编辑的结构化拼装。建议输出包括：

- integrated multimodal description / shot descriptions
- overall soundscape
- non-diegetic music

Builder 结果必须写入 RunSnapshot，并允许用户在提交前检查。

## 前后端边界

### Frontend 负责

- 画布交互
- 节点搜索、增删和连线
- 参数编辑
- Workflow 保存/加载操作
- Run 状态、进度和产物展示

### Backend 负责

- 权威 node registry
- Workflow schema 和语义校验
- ExecutionPlan 编译
- 队列、状态机和取消
- H3 adapter
- 文件边界和 artifact 管理
- 持久化与审计信息

### API 草案

```text
GET    /api/nodes
POST   /api/workflows/validate
GET    /api/workflows
POST   /api/workflows
GET    /api/workflows/{id}
POST   /api/runs
GET    /api/runs
GET    /api/runs/{id}
POST   /api/runs/{id}/cancel
GET    /api/runs/{id}/events
GET    /api/artifacts/{id}
DELETE /api/runs/{id}
```

事件流首选 SSE；只有出现真实双向需求时再引入 WebSocket。

## 存储与压缩

### SQLite

保存需要查询和排序的字段：

- workflow/revision 索引
- run/node run 状态
- queue order
- artifact metadata
- 时间和错误摘要

### 文件系统

```text
var/runs/<run-id>/
├── snapshot.json.gz
├── execution.log.gz
├── metadata.json
└── outputs/
    └── result.mp4
```

策略：

- JSON/日志超过阈值后压缩
- MVP 优先使用标准库 gzip
- MP4、JPEG、PNG 等已压缩媒体不二次压缩
- 压缩格式、原始大小、存储大小和 checksum 写入 metadata
- 删除 Run 时按 artifact 引用关系清理文件

## 配置与运行边界

项目内：

```text
.env.example   # 可提交
.env.local     # 不提交
.venv/         # 不提交，backend
.venv-h3/      # 不提交，H3 runtime
var/           # 除说明文件外不提交
```

关键变量：

```text
APP_HOST
APP_PORT
APP_DATA_DIR
DATABASE_URL
H3_BACKEND
H3_MODEL_PATH
H3_FL2VA_URL
H3_REF2VA_URL
H3_MAX_CONCURRENCY
HF_HOME
TORCH_HOME
XDG_CACHE_HOME
TMPDIR
```

启动入口应显式将缓存和临时目录导向 `var/`，避免默认写入用户主目录。

## 安全边界

- 默认 bind `127.0.0.1`
- 通过 SSH tunnel 访问
- 不提供任意文件路径浏览
- 上传文件生成内部 artifact id
- 不信任 workflow 中的 class/import 字段
- 不加载第三方 Python 节点
- 对输出路径做规范化，禁止逃逸 `var/`

## ComfyUI 的使用边界

保留其有效设计思想：类型化端口、服务端校验、拓扑执行、异步反馈。

明确不依赖：

- ComfyUI workflow JSON
- ComfyUI prompt JSON
- `NODE_CLASS_MAPPINGS`
- `custom_nodes` 扫描
- ComfyUI 前端扩展机制
- ComfyUI 全模型生态

未来若确有迁移需求，应使用独立、有限、单向的 importer，而不是改变核心 WorkflowDocument。

## 关键架构决策

| 决策 | 当前选择 | 复审时点 |
|---|---|---|
| 产品形态 | 独立 H3 Workflow Studio | MVP 后 |
| 推理边界 | 独立 H3Backend | 保持 |
| 首选后端 | SGLang，先实测 | Phase 1 spike 后 |
| Graph | 独立版本化 DAG contract | contracts 实现时 |
| 存储 | SQLite + 项目内文件系统 | 团队化时 |
| 并发 | 单 H3 run | 硬件基线后 |
| 插件 | 内置 registry only | Phase 3 |
| 网络 | loopback + SSH tunnel | 团队化时 |
| 容器 | MVP 不强制 | 可复现环境稳定后 |
| Review | 验证后的 `spawned_pi_process`，否则明确降级 | 每轮记录 |
