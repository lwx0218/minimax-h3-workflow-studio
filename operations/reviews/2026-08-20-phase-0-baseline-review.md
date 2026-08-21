# Phase 0 Baseline 独立审阅报告

- **Review mode**：`spawned_pi_process`
- **审阅性质**：独立、只读
- **审阅范围**：Phase 0 Goal、Spec、Architecture、Plan、治理流程及其验证证据

## Files reviewed

### 强制合同文件

- `AGENTS.md`
- `README.md`
- `Harness_manual.md`
- `docs/project-intake/minimax-h3-workflow.md`
- `docs/specs/mvp-v0.md`
- `docs/architecture/architecture-v0.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/reviews/review-checklist.md`
- `operations/reviews/phase-0-review-prompt.md`

### 补充证据

- `operations/work_logs/2026-08-20-phase-0-initialization.md`
- `.gitignore`
- `.env.example`
- `var/README.md`
- `.pi/settings.json`
- `.pi/agents/README.md`
- `.pi/prompt-templates/governance-loop.md`
- `.git/HEAD`
- `.git/config`

### Pi 行为参考

- Pi `README.md`
- Pi `docs/compaction.md`
- Pi `docs/sessions.md`

## 审阅结论摘要

- Goal、MVP 范围、Architecture 和 R1–R7 总体方向基本一致。
- 未发现实际新增的字母子阶段；Phase 3 已明确排除在 MVP 收线之外。
- Compact、`/new`、`/resume`、`pi -c`、`pi -r`、`--session` 及有损摘要说明与当前 Pi 文档一致。
- `.env.example` 使用相对路径和 loopback 默认值，`var/`、本地环境及主要模型格式已有 ignore 规则。
- 但交付状态转换存在循环合同，R1 实验范围尚未真正 bounded，Phase 0 验证证据也不足以满足 checklist 的 pass 条件。

## P0 findings

无。

## P1 findings

### P1-01：Definition of Done 与 acceptance commit 顺序循环且相互矛盾

**证据：**

- `docs/development/process.md` 的 Definition of Done 将“创建 acceptance checkpoint commit”和“Round Ledger 更新为 accepted”列为完成条件。
- 同文件 Git Policy 又规定 R1–R7“只在 Definition of Done 后创建 acceptance commit”。
- `operations/planning/initialization-plan.md` 的 Quality Loop 使用：
  `Work Log -> Round Accepted -> Checkpoint Commit`。
- `AGENTS.md` 和 Round Lifecycle 则倾向：
  `Work Log -> Checkpoint Commit`。

这形成不可执行的循环：必须先达到 DoD 才能 commit，但 DoD 又要求 commit 已存在；同时无法确定 Ledger 应在 commit 前还是后进入 `accepted`。

**影响：**

Builder 无法按照唯一、可验证的状态转换完成 round，可能出现“已 accepted 但没有 checkpoint”或“无法合法创建 checkpoint”的情况，违反固定交付合同。

### P1-02：R1 可行性实验没有可执行的硬边界

**证据：**

- `operations/planning/initialization-plan.md` 仅写“有限实验矩阵”，但没有规定最大配置数、最大尝试数、时间预算或允许调整的参数集合。
- “多 GPU、offload 和必要的量化路径”中的“必要”没有判定规则。
- `feasible`、`feasible_with_constraints`、`blocked` 缺少可测量的分界条件。
- 同文件将实验矩阵检查推迟到 R1 重型依赖安装前，说明当前 baseline 尚未完成范围封顶。

**影响：**

R1 虽然没有字母子阶段，但仍可能通过不断增加拓扑、offload、量化和版本组合发生隐性范围膨胀，不满足“R1–R7 bounded”的审阅目标。

### P1-03：Phase 0 验证证据不完整

**证据：**

`operations/work_logs/2026-08-20-phase-0-initialization.md` 声明已经验证：

- ignore 规则
- 可提交文件不存在宿主机绝对路径
- Markdown 链接
- 尾随空格
- 模型 snapshot
- GPU 状态

但未记录实际验证命令、关键输出、退出状态或可复验结果。当前只读检查能够确认配置文本和文档链接布局，但不能替代以下 Git/环境事实的机械证据：

- `.env.local`、模型和运行产物的实际 ignore 结果
- Git 候选文件集合及状态
- 模型 snapshot 探测结果
- GPU 探测结果

这不满足 `review-checklist.md` 的“验证证据完整”通过条件，也不满足 `docs/development/process.md` 对 work log 记录命令和结果的要求。

## P2 findings

无。

## Required changes

1. 统一 acceptance 状态转换，例如：
   `Regression Verify -> Final Review Decision -> Work Log -> 准备 Ledger accepted 更新 -> Acceptance Commit -> 验证 commit 成功 -> Round accepted`。
   同步修正 `docs/development/process.md`、`operations/planning/initialization-plan.md` 和相关手册，消除 DoD/commit 循环。
2. 在进入 R1 重型安装前形成 durable、可审阅的实验矩阵，至少明确：
   - 最大配置或尝试次数
   - 时间/资源预算
   - 允许调整的参数集合及顺序
   - T2VA、视频流、音频流的成功标准
   - 三种 Stop Decision 的客观判定条件
3. 补充 Phase 0 验证证据，记录实际命令、结果及失败/限制，至少覆盖：
   - `git status` 与候选提交文件
   - `git check-ignore` 或等效 ignore 验证
   - 宿主机绝对路径检查
   - Markdown 链接检查
   - 模型 snapshot 与 GPU 基线检查
4. 修复后重新执行独立只读 Review；P1 清零后才能创建 Phase 0 acceptance baseline commit 并将 Ledger 更新为 `accepted`。

## Decision

**`changes_required`**

当前存在 3 项 P1 finding，且验证证据不完整。Phase 0 baseline 不得判定为 pass 或 accepted。
