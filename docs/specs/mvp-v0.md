# MiniMax H3 Workflow Studio MVP Spec v0

## 状态

- 状态：需求 grilling 后确认
- 路由：`spec-then-plan`
- 目标：定义首个可交付、可验证的单用户 MVP
- 非目标：一次性实现接近 ComfyUI 的通用平台

## 产品定义

一个在单台服务器上运行、通过 SSH 端口转发访问的 MiniMax-H3 节点工作流工具。用户可以构建基础 DAG，使用本地 H3 完成 T2VA 和 FL2VA，查看运行进度，并在项目目录内管理可追踪的生成产物。

长期可以产品化，但 MVP 严格按照单机、单用户设计。

## 已确认决策

1. 首个技术里程碑是真实本地 T2VA，不先做完整 UI
2. ComfyUI 仅作产品形态参考，不兼容其 workflow contract
3. MVP 支持 T2VA + FL2VA；Ref2VA 后置
4. 支持 Raw H3 Prompt 和简单本地 Prompt Builder
5. 官方 Context-IR 后续作为可选节点
6. 编辑器支持基础 DAG 的增删、拖拽、连线、参数编辑、保存、加载和执行
7. SGLang 先做限界可行性测试，失败时再依据数据评估其他后端
8. MVP 定义节点扩展接口，但不开放第三方插件安装
9. SQLite 保存结构化元数据，媒体保存在本地文件系统
10. 所有项目运行数据统一位于 `var/`
11. Web 服务仅监听 `127.0.0.1`，不实现账号系统
12. H3 单并发执行，其余任务 FIFO 排队
13. 保存完整运行快照与产物元数据，大数据按阈值压缩
14. 项目近期不公开发布，许可证后续决定
15. 后端和 H3 推理使用两个项目内独立 Python 虚拟环境

## 目标用户

### MVP 用户

- 单个开发者/创作者
- 能够通过 SSH 使用远程 GPU 服务器
- 愿意先使用本地、实验性的 H3 工作流

### 暂不支持

- 局域网多人共享
- 公网匿名用户
- 多租户和商业 SaaS 用户

## 核心用户路径

### 路径 1：技术可行性

1. 配置本地模型路径
2. 启动 H3 FL2VA variant 服务
3. 提交 T2VA 请求
4. 查询状态
5. 下载带音频 MP4
6. 记录启动参数、显存、内存和耗时

### 路径 2：创建并执行 T2VA Workflow

1. 打开节点编辑器
2. 添加 Prompt 节点
3. 添加 H3 T2VA 节点
4. 添加 Artifact Output 节点
5. 连接类型化端口
6. 服务端校验并提交运行
7. 查看排队和节点进度
8. 预览、下载或删除产物

### 路径 3：创建并执行 FL2VA Workflow

在路径 2 基础上增加首帧、尾帧或二者，并由服务端验证素材和参数。

## 功能需求

### FR-001 Workflow Graph

- 支持版本化 Workflow Document
- 支持节点和有向边
- 支持类型化输入/输出端口
- 支持 UI 坐标、分组和 viewport，但 UI 数据不参与执行语义
- MVP 仅允许 DAG
- 服务端校验节点类型、版本、端口、必填输入和环路

### FR-002 Node Registry

- 节点具备稳定 `type` 和 `version`
- 节点声明输入、输出和参数 schema
- 节点执行通过统一 context 获取日志、取消信号、artifact store 和 backend
- MVP 仅显式注册内置节点

首批节点候选：

- `TextInput`
- `RawH3Prompt`
- `H3PromptBuilder`
- `ImageInput`
- `H3GenerateT2VA`
- `H3GenerateFL2VA`
- `ArtifactOutput`

### FR-003 Prompt

- Raw 模式允许直接填写 H3 结构化 prompt
- Builder 至少覆盖镜头描述、整体声景和非叙事音乐
- Builder 输出对用户可见、可编辑、可记录
- UI 和文档明确 Builder 不等价于官方 Context-IR

### FR-004 H3 Inference

- 通过 `H3Backend` adapter 隔离具体推理实现
- 首个真实实现目标为 SGLang
- backend 至少提供 health、capabilities、submit、status、cancel、result
- MVP 覆盖 T2VA、首帧、尾帧和首尾帧 FL2VA
- 提供 Mock backend 以支持无 GPU 开发和自动测试

### FR-005 Queue and Runs

- 同一时间最多一个运行中 H3 任务
- 其他任务 FIFO 排队
- 可查看 queued/running/succeeded/failed/cancelled/interrupted 状态
- 可取消排队任务
- 尽可能向推理后端传播运行中取消
- 服务重启后不自动重跑状态不明确的运行中任务

### FR-006 Persistence and Artifacts

- SQLite 保存 Workflow、revision、run、node run 和 artifact 索引
- 媒体及完整快照保存在 `var/`
- 支持预览、下载和显式删除
- 删除运行时清理关联产物，失败时保留可诊断记录

建议布局：

```text
var/
├── db/
├── uploads/
├── outputs/
├── runs/
├── cache/
├── logs/
└── tmp/
```

### FR-007 Run Snapshot

每个运行至少记录：

- Workflow revision 快照
- 节点类型和版本
- 节点参数与解析后的输入
- 最终 H3 prompt
- seed、task、分辨率、时长和宽高比
- backend、模型标识和服务启动参数
- 开始/结束时间、耗时和错误
- 输出媒体元数据

大型 JSON 和日志按阈值压缩。SQLite 检索字段不压缩，MP4 等媒体不重复压缩。

### FR-008 UI and Access

- 前端支持基础 DAG 编辑闭环
- 后端和前端默认只监听 loopback
- 通过 SSH 端口转发访问
- MVP 不实现身份认证

## 非功能需求

### NFR-001 Portability

- 已提交文件不包含宿主机绝对路径
- 机器差异通过 `.env.local` 承接
- 项目运行数据不散落到用户主目录或系统缓存目录

### NFR-002 Version Control Safety

以下内容必须忽略：

- 模型权重和 checkpoint
- ONNX、GGUF、TensorRT engine
- 虚拟环境和 Node 依赖
- `.env.local`
- SQLite、日志、缓存、上传和生成媒体

### NFR-003 Traceability

从产物能够反查 run、workflow revision、prompt、seed、节点版本和 backend 配置。

### NFR-004 Security

- 默认不监听公网或局域网地址
- Workflow 不允许执行任意 Python 或 shell
- MVP 不动态加载第三方节点
- 文件访问限制在显式素材和项目运行目录

### NFR-005 Testability

- 图校验、执行状态机和 storage 使用单元测试
- 常规测试默认使用 Mock backend
- 真实 H3 测试独立标记，不进入快速测试套件

## MVP 验收标准

1. 可启动本地 H3 服务、后端和前端
2. 可构建、保存并重新加载基础 DAG
3. 支持 Raw Prompt 和本地 Prompt Builder
4. 支持真实 T2VA 和 FL2VA
5. 任务支持 FIFO、状态查询和取消
6. 能生成并预览带音频 MP4
7. SQLite 中存在完整可查询的运行索引
8. 运行目录包含可追踪快照和媒体元数据
9. 所有运行数据位于项目 `var/`
10. Mock backend 可完成自动化端到端测试
11. 模型和运行产物不会出现在 Git 状态中
12. README 包含运行方式和已知限制

## 明确不在 MVP 中

- Ref2VA
- H3-Regenerate-2K
- 官方 Context-IR 强依赖
- ComfyUI workflow/custom node 兼容
- 第三方插件安装、市场和沙箱
- 登录、多用户、配额和权限
- 高级控制流、子图和批处理
- 多任务 GPU 并发调度

## 固定交付 Gate

这里的 round 是一个包含实现、验证、独立 Review、修复、复验和 checkpoint 的交付 gate，不是单条聊天消息。

MVP 在 Phase 0 后固定为 R1–R7：

1. R1：H3 本地真实 T2VA 可行性
2. R2：Workflow/Node contracts 与 DAG 校验
3. R3：SQLite、FIFO Queue、Executor、Artifact Store、Mock API
4. R4：基础画布与 Mock 端到端
5. R5：SGLang Adapter 与真实 T2VA 垂直闭环
6. R6：FL2VA、素材、Prompt Builder、取消和压缩
7. R7：全量回归、安全、文档、性能基线和 MVP 验收

Bug Fix 和 Review 不新增字母 round；原 round 保持打开直到 accepted 或 blocked。Phase 3 是 MVP 后 backlog。

## Quality Acceptance

每个 round 必须满足 `docs/development/process.md` 的 Definition of Done：自动验证、Review artifact、P0/P1 清零、work log 和 checkpoint commit 缺一不可。

## 技术验证后再决定

- A5000 的具体 SGLang 并行与 offload 参数
- 可接受的 5 秒 768p 生成基线
- 是否需要 ComfyUI backend 作为硬件适配备选
- 是否采用 gzip 之外的 zstd
- 运行中任务可达到的取消粒度
