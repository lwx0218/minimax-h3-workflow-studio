# Phase 0 P1 修复第二次独立只读审阅报告

- **Review mode**：`spawned_pi_process`
- **审阅性质**：独立、只读
- **P0**：0
- **未关闭 P1**：1
- **Decision**：`changes_required`

## Files reviewed

### 合同文件

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

### 修复与验证证据

- `operations/reviews/2026-08-20-phase-0-baseline-review.md`
- `operations/reviews/phase-0-verification.md`
- `operations/planning/r1-h3-feasibility-matrix.md`
- `operations/work_logs/2026-08-20-phase-0-initialization.md`

### Portability 与项目治理文件

- `.gitignore`
- `.env.example`
- `var/README.md`
- `.pi/settings.json`
- `.pi/agents/README.md`
- `.pi/prompt-templates/governance-loop.md`
- `.pi/skills/governance-loop-entry/SKILL.md`
- `.pi/skills/grill-me/SKILL.md`
- `.pi/skills/grill-with-docs/SKILL.md`
- `.pi/skills/grilling/SKILL.md`
- `.git/HEAD`
- `.git/config`

## 原 findings disposition

### P1-01：Definition of Done 与 acceptance commit 顺序循环

**Disposition：已关闭。**

`docs/development/process.md` 已明确状态转换：

`Pre-Commit Acceptance Gate -> Work Log + Ledger accepted candidate -> Acceptance Commit -> Post-Commit Verify -> accepted effective`

同时明确：

- acceptance commit 只要求先通过 Pre-Commit Gate，不再要求先完成包含 commit 的 DoD；
- Ledger 中的 `accepted` 在提交前仅为 candidate；
- commit 或 post-commit 检查失败时必须恢复为 `in_progress`。

`AGENTS.md`、`Harness_manual.md` 和 `operations/planning/initialization-plan.md` 与该顺序一致，原循环合同已消除。

### P1-02：R1 可行性实验没有硬边界

**Disposition：已关闭。**

`operations/planning/r1-h3-feasibility-matrix.md` 已提供：

- 最多 2 组依赖锁定组合；
- 最多 3 个 profile、每个最多 2 次、合计最多 6 次 generation attempt；
- 单次加载和生成各 60 分钟上限；
- 235 GiB 主存安全线及 100 GiB 新增磁盘上限；
- 固定 probe、允许参数范围和第二次 attempt 的调整限制；
- T2VA、MP4、视频流、音频流及可解码性成功标准；
- `feasible`、`feasible_with_constraints`、`blocked` 收敛条件；
- blocked 后禁止自动新增 R1D 或其他实验分支。

原隐性范围膨胀风险已被充分封顶。

### P1-03：Phase 0 验证证据不完整

**Disposition：部分修复，未关闭。**

已补充：

- Git、ignore、model snapshot 和 GPU 检查命令；
- staged candidate 数量及 `git diff --cached --check` 结果；
- ignore 命中、GPU 型号、显存、driver 和 topology 摘要；
- work log 对验证结果和未验证范围的引用。

但以下证据仍不可完整复验：

1. 宿主机绝对路径、Markdown 链接和尾随空格检查仅描述为“执行 Python repository scan”，未记录实际可执行命令或脚本。
2. staged candidates 只记录“24 个文件”，未保存 `git diff --cached --name-only` 或等价文件清单。
3. 多项检查仅记录结果摘要，未明确记录命令退出状态。

这仍未完全满足首次 required change 中“记录实际命令、结果及可复验结果”，也未满足 `review-checklist.md` 的“验证证据完整”通过条件。

## New findings

### P0

无。

### P1

无新增 P1；保留原 `P1-03` 为未关闭项。

### P2

无。

## Required changes

1. 在 `operations/reviews/phase-0-verification.md` 中记录文档扫描的完整可执行命令或提交对应检查脚本。
2. 补充 staged candidate 文件清单及关键命令退出状态。
3. 复验后再次执行独立只读 Review。

## Decision

**`changes_required`**

`P1-01`、`P1-02` 已关闭，未发现修复引入的新 P0/P1；但 `P1-03` 尚未完全关闭。Phase 0 当前不得创建 acceptance baseline commit，也不得使 Ledger `accepted` 生效。
