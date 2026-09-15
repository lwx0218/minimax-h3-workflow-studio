# minimax-h3-workflow Harness Manual

<!-- HARNESS:MANUAL:MANAGED:START -->
项目本地的人类操作入口。模型执行合同以 `AGENTS.md` 为准。

## 交付主线

| 环节 | 承担者 | 做什么 |
| --- | --- | --- |
| 1. 规划 | Orchestration session | 澄清需求、收敛范围、切分 round |
| 2. 分发 | `pi-fleet` | 每个 round 一个独立 Pi session |
| 3. 执行 | `pi-subagents` | round 内分配 builder / reviewer |
| 4. 门禁 | `ponytail` | 新增代码准入判定 |

**你只需要介入第 1 步**：确认规划与 round 划分。round 内的复核结论由 reviewer subagent 出，代码准入由 ponytail 判定。

## 第一次 session

```bash
pi --name "00-orchestration"
```

批准规划前保持 no-write：只读取、推断、讨论和展示 Plan Preview；不改业务文件、不写 durable evidence、不安装依赖、不执行破坏性操作。

Plan Preview 应让你能检查 goal、scope、non-goals、assumptions、risks、validation 和 round 划分。接受 recommended defaults 不等于批准规划。

## 分发 round

规划确认后，在 Orchestration session 里：

```
/fleet
```

为每个 round `session_spawn` 一个开发 session（名字用 round 标识），round 间通过 `session_bus` 同步状态。不要靠人工复制上下文交接。

需要终端复用器（tmux / Ghostty / Zellij）。配置在 `~/.pi/agent/pi-fleet.json`。

## 已有 baseline 后

清楚的 bounded task 直接执行并验证，不必每次都开 Orchestration。不要因为仓库里有历史 Plan 或 operations 目录就自动加重流程。

## Evidence

项目 evidence 默认保存在 `docs/project-intake/`、`operations/planning/`、`operations/work_logs/`、`operations/reviews/`。

普通 bounded task 不强制写 evidence。需要记录时写最小、可复验内容。新增 Markdown 前先按 `docs/manual/document-governance.md` 判断落位。

## 更新治理面

从 `Harness_Workspace` 根：

```bash
sh harness.sh <本项目目录>           # 预览
sh harness.sh <本项目目录> --apply   # 写入
```

它只管理 Harness 分区与 `.pi` capability surface，保留项目 owned 内容，会显示 manifest 和备份路径，不自动 commit 或 push。

## Safety

遇到破坏性操作、外部授权、scope 改变、无法验证或 managed/project 分区不清时停下来让 Owner 决策。不自动 push。
<!-- HARNESS:MANUAL:MANAGED:END -->

<!-- PROJECT:OWNED:START -->
## 项目操作说明

在这里写本项目特有的启动方式、环境要求、常用命令和注意事项。Harness 会保留本分区。
<!-- PROJECT:OWNED:END -->
