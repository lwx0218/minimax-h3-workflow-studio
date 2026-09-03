# Governance Maintenance Backlog

- Status：active backlog
- Source：Owner 请求将 `/home/superuser/dev/Harness_Workspace` 的轻量治理更新最小化同步到本项目
- Scope：记录 `.pi/` / harness / extension / skill / prompt / settings / handoff / review tooling 等治理层问题

## 1. 使用规则

项目开发过程中，`.pi/` / harness 治理层问题不得被擅自修改。发现问题时默认记录在本 backlog，或在当前 review artifact 中标为 `review evidence limitation`。

治理层问题不进入当前产品 candidate，不阻塞当前产品验收，除非它直接导致必要门禁完全无法成立。只要不直接阻断产品开发或验收判断，就继续当前产品 task / Round。

不得为了修治理工具而自动修改 `.pi/`、harness-flow、extensions、skills、prompts、settings、session handoff/review tooling，也不得重复 reload / re-review 来修治理工具。

## 2. 允许修改治理层的条件

只有同时满足以下条件，才允许修改 `.pi/` / harness 相关文件：

1. 严重恶性 bug 导致项目无法继续；
2. Owner 明确授权单独治理维护任务；
3. 问题被记录为 governance maintenance issue；
4. 该维护任务与产品 Round / task candidate 分离；
5. 修改后有独立验证和 review evidence。

严重阻断例子：

- 无法生成任何 review evidence；
- 无法保护 candidate immutability；
- 工具会错误修改项目文件；
- handoff / review gate 完全不可用。

## 3. Backlog 记录格式

```md
### GM-YYYYMMDD-NN — <短标题>

- Status：`open` | `authorized` | `in_progress` | `resolved` | `wontfix`
- Source：<work log / review / session>
- Classification：`governance maintenance issue` | `review evidence limitation`
- Affected layer：`.pi` | `harness-flow` | `extension` | `skill` | `prompt` | `settings` | `handoff/review tooling`
- Current product impact：`none` | `limitation` | `blocking gate`
- Owner authorization：`none` | `<date / evidence>`
- Disposition：<处理方式>
```

## 4. 当前记录

暂无 active governance maintenance issue。后续若 formal fixed-Round tooling 出现阻断，再按本 backlog 格式单独记录。
