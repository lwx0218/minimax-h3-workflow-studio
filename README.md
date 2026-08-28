# MiniMax H3 Workflow Studio

一个以 MiniMax-H3 为核心的本地音视频生成工作流项目。产品形态参考 ComfyUI 的节点画布和异步执行体验，但采用独立的 workflow contract、节点接口和运行时。

## 当前状态

Phase 0 治理基线已 accepted。R1 单卡 C3 已 valid，feasibility 为 `feasible_with_constraints`；4-GPU TP4 路线受 host staging/quantized AdaLN incompatibility 阻塞，R1 当前为 **blocked** control gate。

- PI/governance：`runtime-ready`
- 应用：`bootstrap-ready`
- H3 inference：单卡 official INT8 已完成有效 1344×768 T2VA（视频+立体声音频）；4-GPU 路线等待 Owner 选择 unquantized SGLang、fallback backend、延后或增加主存
- R1 evidence：[`operations/reviews/2026-08-21-r1-feasibility-report.md`](operations/reviews/2026-08-21-r1-feasibility-report.md)
- External reference assessment：[`operations/planning/r1-external-reference-assessment.md`](operations/planning/r1-external-reference-assessment.md)

## MVP

首版面向单机单用户，计划支持：

- 基础 DAG 节点编辑
- Raw H3 Prompt 和本地 Prompt Builder
- 本地 T2VA 和 FL2VA
- 单并发 FIFO 任务队列
- Workflow 保存/加载
- 运行进度、取消和产物预览
- SQLite 运行记录和可追踪快照
- Mock backend 自动测试

首版不包含 Ref2VA、ComfyUI workflow 兼容、第三方插件安装、登录、多用户和公网部署。

详见：

- [项目驾驭手册](Harness_manual.md)
- [项目 Intake](docs/project-intake/minimax-h3-workflow.md)
- [MVP Spec](docs/specs/mvp-v0.md)
- [架构建议](docs/architecture/architecture-v0.md)
- [开发与质量流程](docs/development/process.md)
- [Master Plan](operations/planning/initialization-plan.md)
- [Review Checklist](operations/reviews/review-checklist.md)

## 关键边界

- 不 fork 或复制 ComfyUI；仅参考产品和架构思想
- H3 推理服务与 orchestration 后端隔离
- 模型权重位于仓库外，通过 `.env.local` 引用
- 所有应用运行数据统一位于项目内 `var/`
- 权重、checkpoint、数据库、缓存、日志和生成媒体不得进入 Git
- Web 服务默认只监听 `127.0.0.1`，通过 SSH tunnel 访问

## 配置

可提交的变量模板：

```bash
cp .env.example .env.local
```

`.env.local` 是机器本地配置，不进入 Git。不要把 API token 或宿主机绝对路径写入已提交文件。

## 运行数据

运行数据统一放置在：

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

目录约定见 [var/README.md](var/README.md)。

## 固定交付路线

- Phase 0：治理基线
- Phase 1（R1–R4）：H3 feasibility、contracts、backend core、Mock UI
- Phase 2（R5–R7）：真实 T2VA、FL2VA、hardening 与 MVP 验收
- Phase 3：MVP 后 backlog，不参与当前收线

Review 和 Bug Fix 保留在原 round 内，不新增 R1B、R1C 等子阶段。当前不得进入 R2 或先开发 UI；下一步是 4-GPU 技术路线 Owner control decision。

## 许可证说明

MiniMax-H3 权重受 MiniMax H3 Community License Agreement 约束。目标部署地区当前为中国；正式发布或部署前应重新核验最新模型许可证和 Acceptable Use Policy。

本项目近期不公开发布，暂未选择项目级开源许可证。
