# Independent Review 与 Round Scope 标准

- Status：active governance standard
- Source：Owner 请求将 `/home/superuser/dev/Harness_Workspace` 的轻量治理更新最小化同步到本项目
- Applies to：所有 active task、checkpoint、Round、review bundle 和 closeout

## 1. 目的

Independent Review 的职责是判断当前 active task / Round 的 candidate 是否满足批准合同，而不是审计整个仓库、修复治理工具，或把所有 dirty/untracked 路径纳入当前验收。

本标准固定三类 scope，并规定非当前任务问题的分类方式。

## 2. 三类 Scope

### 2.1 `candidate scope`

`candidate scope` 是当前任务 / Round 请求验收的实际变更。

- 只有 candidate scope 内的问题可以成为当前 candidate 的 P0/P1/P2 finding。
- P0/P1 必须留在当前任务 / Round 修复并复验。
- P2 必须由 Builder disposition 后才能 closeout。
- candidate scope 必须来自批准合同、Plan、Round section、Owner 明确授权或本任务直接交付物。

### 2.2 `context scope`

`context scope` 是 reviewer 判断 candidate 所需的只读材料，包括合同、Plan、spec、source、tests、baseline、历史事实和相关架构文档。

- 进入 context 不等于成为 candidate。
- context scope 的问题只能在影响当前 candidate 判断时形成 finding。
- 历史/归档/superseded 文档如只作为事实证据，不恢复 normative authority。

### 2.3 `environment / dirty-worktree scope`

`environment / dirty-worktree scope` 包括 Git dirty/untracked、pre-existing local files、工具目录、运行环境残留、ignored runtime path 和本任务外的本地状态。

- 只用于透明记录、candidate immutability、污染风险判断和复现边界说明。
- 不自动成为当前 candidate。
- 不得仅因为路径出现在 `git status` 或 review bundle 中，就把它列为当前产品 Round / task 的验收范围。

## 3. 固定规则

> 进入 review bundle 不等于进入 candidate scope。
>
> Git changed/untracked paths 不自动进入当前产品 Round / task 的验收范围。

Reviewer 必须在 artifact 中说明 candidate scope、context scope 和 environment / dirty-worktree scope。Builder 必须在 work log 或 review artifact 中记录 pre-existing dirty baseline，避免把用户或环境残留误归因给当前 candidate。

## 4. 非当前任务问题分类

如果 review 发现非当前任务问题，应分类为以下之一：

1. **当前产品阻塞**：虽不属于 candidate 变更本身，但直接导致当前产品验收或必要安全门禁无法成立。
2. **review evidence limitation**：review 能力、证据范围、工具权限或读取边界造成的不确定性；需说明是否影响当前结论。
3. **governance maintenance issue**：治理文档、`.pi/`、harness、handoff/review tooling、skill、prompt、settings 等问题；默认另行记录和排期。
4. **非当前 task / Round backlog**：真实问题但不影响当前 candidate 验收，应进入后续 backlog，不在当前 Round 自动修。

不得把 governance / harness / `.pi/` 问题当成产品 candidate P1 去修，除非它们直接让当前必要门禁完全无法成立；即便如此，也必须作为单独 governance maintenance 记录。

## 5. Builder 与 Reviewer 分工

- Reviewer 只读检查，不写 candidate 文件，不写 durable artifact。
- Builder 负责运行相称自动验证；只有 Owner 明确批准 formal mode、fixed Round 或当前有效计划要求 Independent Review 时，才调用 Independent Review、记录 review capability evidence、写 durable review artifact、disposition P2，并修复 candidate 内 P0/P1。
- Bug/Fix/Review 留在当前 task / Round；不创建隐藏 acceptance unit、Phase acceptance、字母子 Round 或非 Owner 批准的 scope expansion。

## 6. `.pi/` / Harness 边界

`.pi/`、harness-flow、extensions、skills、prompts、settings、session handoff/review tooling 都属于治理层。

- 项目开发过程中不得擅自修改。
- 发现问题时默认记录为 governance maintenance issue 或 review evidence limitation。
- 不进入当前产品 candidate。
- 不阻塞当前产品验收，除非它让必要门禁完全无法成立。
- 不自动修 harness。
- 不重复 reload / re-review 来修治理工具。
- 只有严重恶性 bug 导致项目无法继续，并且 Owner 明确授权后，才允许修改相关文件。

严重阻断例子：无法生成任何 review evidence、无法保护 candidate immutability、工具会错误修改项目文件、handoff / review gate 完全不可用。

## 7. Artifact 最小要求

每份 Independent Review artifact 至少记录：

- current task / Round ID；
- approved contract / Plan path；
- candidate scope；
- context scope；
- environment / dirty-worktree scope；
- validation evidence；
- reviewer mode 和 capability evidence；
- P0/P1/P2 findings；
- 非当前任务问题分类；
- P2 disposition；
- decision。
