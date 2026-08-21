# MiniMax H3 Workflow Studio 驾驭手册

## 1. 这份手册解决什么问题

这份手册面向项目操作者，说明：

- 当前项目由谁做什么
- 如何判断一轮是否真的完成
- 你需要在什么情况下介入
- 如何跟踪计划、实现、验证和 Review
- 什么时候继续当前 session、手动 compact 或新建 session
- 新 session 如何恢复项目上下文

项目业务合同仍以以下文件为准：

- `AGENTS.md`
- `docs/project-intake/minimax-h3-workflow.md`
- `docs/specs/mvp-v0.md`
- `docs/architecture/architecture-v0.md`
- `operations/planning/initialization-plan.md`
- `docs/development/process.md`

## 2. 你需要做什么

### 默认需要你做的事

1. 确认 Goal、Spec 和重大范围变更
2. 在 Pi 无法自行继续新回合时发送：`继续主计划`
3. 对阻塞性决策做选择，例如本地 H3 不可行时是否更换 backend
4. 提供模型许可、账号、密钥或业务素材等只有你掌握的信息
5. 在 R7 做最终产品体验验收

### 默认不需要你做的事

你不需要每轮额外提示：

- “请 Review”
- “请修复 Review 问题”
- “请重新运行测试”
- “请更新 work log”
- “请提交 Git checkpoint”

这些属于每轮强制质量闭环，由 Builder 自动完成。只有出现阻塞、范围变化或高风险操作时才需要你介入。

## 3. 谁负责实现和质量

### Builder

当前主 Pi session：

- 阅读当前 round contract
- 实现最小必要变更
- 运行自动验证
- 修复阻塞问题
- 更新 work log

### Automated Verifier

项目测试与工具链：

- 单元测试和集成测试
- 类型检查、lint、构建
- Workflow contract 和状态机检查
- 路径、运行目录和 Git ignore 检查
- 真实 H3 golden workflow

### Independent Reviewer

项目选择 `spawned_pi_process` 作为目标独立审阅方式：

- Builder 在提交前启动新的只读 Pi 进程
- Reviewer 读取 spec、architecture、round contract 和改动
- Reviewer 不修改文件
- Review 结果写入 `operations/reviews/`
- P0/P1 finding 必须在同一 round 修复并重新审阅

若独立进程不可用，必须明确降级为 `same_session`，不能假装完成了独立 Review。

### 你（Owner）

你负责产品方向和最终接受，不负责替代自动测试或逐项驱动 Bug Fix。

## 4. 固定交付轮次

当前 MVP 只有七个后续 round：

| Round | 交付物 |
|---|---|
| R1 | H3 本地真实 T2VA 可行性 |
| R2 | Workflow contract、Node contract、DAG 校验 |
| R3 | SQLite、FIFO Queue、Executor、Artifact Store、Mock API |
| R4 | 基础画布与 Mock 端到端原型 |
| R5 | SGLang Adapter 与真实 T2VA 垂直闭环 |
| R6 | FL2VA、素材、Prompt Builder、取消和压缩 |
| R7 | 全量回归、安全、文档、性能基线和 MVP 验收 |

Bug Fix 和 Review 不创建 R4B、R4C 等新 round；原 round 保持打开，直到通过或明确 blocked。

Phase 3 是 MVP 后 backlog，不参与当前收线。

## 5. 如何查看项目状态

### 最权威的状态

```text
operations/planning/initialization-plan.md
```

查看其中 Round Ledger：

- `pending`
- `in_progress`
- `blocked`
- `accepted`

### 查看最近完成了什么

```text
operations/work_logs/
```

### 查看质量结论

```text
operations/reviews/
```

### 查看 Git checkpoint

```bash
git status --short
git log --oneline --decorate -10
```

只有同时具备验证证据、Review 通过、Ledger accepted candidate、成功的 Git checkpoint 和 post-commit 检查，accepted 状态才生效，才能称为一轮完成。

## 6. 常用操作指令

### 继续主计划

在新的用户消息中输入：

```text
继续主计划。读取项目合同和最新 work log，只执行 Round Ledger 中下一个未完成 round；在本轮内自动完成实现、验证、独立 Review、阻塞问题修复、复验和 checkpoint。仅在需要范围变更、危险操作或外部信息时暂停。
```

### 查询状态但不执行

```text
只汇报当前 Round Ledger、最近验证、未解决 Review finding 和下一个控制门，不修改文件。
```

### 要求重新审视范围

```text
先不要实现。使用 grill-with-docs 对当前 spec 和 plan 做一次范围审查，只问会改变验收或架构的关键问题。
```

### 查看当前 session

```text
/session
```

### 给 session 命名

```text
/name R1-h3-feasibility
```

## 7. Context 与 Compact

### 自动 compact

Pi 默认在以下条件附近自动 compact：

```text
contextTokens > contextWindow - reserveTokens
```

默认 `reserveTokens` 为 16384，默认保留最近约 20000 tokens。Compact 会将较早消息压缩成结构化摘要，完整原始消息仍留在 session JSONL 中，但发送给模型的上下文会变成摘要加近期消息。

Compact 是有损摘要，不等于 durable project memory。

### 当前 57.3% 怎么处理

57.3% 时通常不需要手动 compact。当前更好的做法是：

1. 完成本轮治理文件和 baseline commit
2. 将关键事实留在 spec、plan、work log 和 review 中
3. 为 R1 新建干净 session

这样比在长需求讨论后继续堆叠实现上下文更稳。

### 适合手动 compact 的情况

- 仍在同一个 round，目标没有变化
- 前面有大量调研或无关讨论
- durable docs 已经更新
- 即将进行一个较大的实现步骤，希望提前释放上下文
- context 已明显偏高，但仍需要近期工具结果

命令：

```text
/compact 保留当前 Goal、MVP 边界、Round 状态、关键决策、修改文件、测试结果、Review finding、阻塞项和下一步。
```

### 不适合立刻 compact 的情况

- 关键决策还只存在于对话里，尚未写入项目文档
- 当前正在依赖近期详细错误日志调试
- 只是因为看到 50%–60% 就焦虑
- 当前 round 已结束，此时新 session 通常更清楚

## 8. 什么时候新建 Session

推荐新建 session：

- 一个 round 已 accepted，即将进入下一个 round
- 从需求/治理转入重型实现
- Goal 或工作类型明显改变
- 已经历多次 compact，担心摘要漂移
- 需要 Independent Reviewer
- 当前上下文被大量无关试验占用

继续同一个 session：

- 当前 round 尚未完成
- 正在连续调试同一个失败
- 近期工具输出对下一步很重要
- context 仍健康且没有主题漂移

## 9. 如何新建或恢复 Session

### 在 Pi 内新建

```text
/new
/name R1-h3-feasibility
```

随后输入“新 Session 交接 Prompt”。

### 退出后继续最近 session

```bash
cd <project-root>
pi -c
```

### 浏览历史 session

```bash
cd <project-root>
pi -r
```

或者在 Pi 内：

```text
/resume
```

### 使用指定 session

先在原 session 查看：

```text
/session
```

然后：

```bash
pi --session <session-id>
```

### 新 Session 交接 Prompt

```text
这是 MiniMax H3 Workflow Studio 的新开发 session。
先读取 AGENTS.md、Harness_manual.md、README.md、docs/project-intake/、docs/specs/mvp-v0.md、docs/architecture/architecture-v0.md、docs/development/process.md、operations/planning/initialization-plan.md，以及最新 work log 和 review。

只执行 Round Ledger 中下一个未完成 round。先检查 Definition of Ready；随后在本轮内自动完成实现、自动验证、独立 Review、阻塞问题修复、复验、work log 和 Git checkpoint。不要扩展 MVP 范围；只有遇到计划定义的控制门时才暂停询问。
```

新 session 不会继承旧 session 的完整对话；它依靠项目 durable evidence 完成交接。因此每轮 closeout 不能省略 work log 和 review。

## 10. 最终如何收线

R7 必须产生：

- MVP acceptance report
- 全仓 Review report
- 自动测试和真实 H3 golden workflow 结果
- 性能基线
- 已知限制和恢复说明
- 无未解决 P0/P1 finding
- MVP Git checkpoint/tag 候选

最后由你确认一次 UI 和真实生成体验。此前任何单轮通过都不等于整个 MVP 完成。
