# AGENTS.md

<!-- HARNESS:MANAGED:START -->
## Harness Managed Execution Contract

本分区由 Harness 管理（`harness.sh` 会整体替换）。项目产品、领域、安全和运行时规则请写在 `PROJECT:OWNED` 分区。

### Authority

- 本文件是模型执行合同；冲突时优先于 README、human manual、`.pi/` 和历史 evidence。
- `.pi/` 只是 capability layer，不是 policy authority。

### Owner-Facing Language

面向 Owner 的聊天总结、交付说明、状态报告和控制门提示默认使用中文。文件名、命令、代码标识、协议字段和必要原文引用可保留英文。

### 交付主线

1. **Orchestration session** — `pi --name "00-orchestration"`，澄清需求、收敛范围、切分开发 round。此阶段不写业务代码。
2. **pi-fleet 分发** — `/fleet` 为每个 round `session_spawn` 一个独立开发 session；round 间通过 `session_bus` 通信。
3. **Subagents 执行** — round 内分配 builder / reviewer（定义在 `.pi/agents/`）。builder 实现，reviewer 只读复核并给出 `approve` / `approve_with_follow_up` / `return_to_planning`。
4. **ponytail 门禁** — 新增代码由 ponytail 做准入判定。

**Owner 只在第 1 步介入**，确认规划与 round 划分。round 内的内容复核由 reviewer subagent 出结论，代码准入由 ponytail 判定。**不得把逐轮 review 结论推回 Owner**；只有 reviewer 与 ponytail 都无法结论、或结论与 round 目标冲突时，才升回 Orchestration session。

不存在需要 Owner 逐条批准的 formal mode、fixed Round ledger、independent review gate 或 session handoff 合同。历史 evidence 不激活任何旧流程。

### Round 的定义

round 是 Orchestration 阶段切出的**任务切分单位，不是验收单位**。不需要 ledger、固定编号规则或跨 round 状态机。

一个 round 说清楚四件事即可：目标、改动面、验证方式、完成判据。

### 默认模式

理解请求、必要时少量澄清、执行 bounded change、运行相称验证、用中文总结。复杂、跨文件或已有历史 evidence 不会自动加重流程。

Plan 用于澄清目标、范围、风险、验证和 round 切分，不产生额外审核义务。

### First Session

Greenfield 或无 baseline 的项目，首次从项目根运行：

```bash
pi --name "00-orchestration"
```

Owner 批准规划前只允许 read/infer/discuss 和 chat Plan Preview；不得修改业务 code/config、创建 durable evidence、安装依赖或执行破坏性操作。接受 recommended defaults 不等于批准规划。

### Routing

- `direct-execute`：清楚 bounded task。
- `plan`：目标、范围、风险、验证或 round 切分需要澄清。
- `review-only`：只要 findings。
- `needs-package`：确有能力缺口。

skills 和 domain modeling 是按需能力，不是默认关卡。

### 治理层边界

产品 round 不修改治理层（`.pi/`、`AGENTS.md`、Harness 下发的文件）。发现治理层问题时单独提出，不在产品 round 里顺手改。

`.pi/extensions/` 下不放 vendored extension 源码。能力通过 `.pi/settings.json` 的 `packages` 声明获得；已在全局装好的 package 不重复声明。

### Document And Evidence Governance

新增或实质更新 Markdown 时先判定承载位置：

- `docs/**`：长期说明、manual、reference、project intake 与导航；kebab-case 文件名和最小 Metadata。
- `operations/**`：事件型 durable evidence；`YYYY-MM-DD-<slug>.md` 日期前缀与任务型 Metadata。

只有进入 Plan、round 切分、合同/bootstrap 变更或需要保留 review trail 时，才写 durable evidence。详细格式见 `docs/manual/document-governance.md`。

### Evidence And Safety

高风险、破坏性、外部授权、scope 改变或验证失败时 fail closed 并询问 Owner。不自动 push。
<!-- HARNESS:MANAGED:END -->

<!-- PROJECT:OWNED:START -->
# AGENTS.md

给在这个仓库里工作的编码代理的说明。

## 读什么

1. `README.md` — 是什么、怎么跑
2. `docs/ARCHITECTURE.md` — 模块、Run 生命周期、网络
3. `docs/OPERATIONS.md` — 目标机器、并发上限、多卡路线
4. `config/*.json` — 所有可调参数都在这里，不在代码里

历史（R1–R4 的 review、work log、探针脚本）在 tag `v0.1-r4-mvp`，只在需要考古时看。

## 边界

- 不 fork ComfyUI，不写自己的画布 / 节点注册表 / DAG 执行器 / workflow 格式。Studio 只提交原生 ComfyUI API prompt。
- `h3_studio/` 只用标准库。
- 仓库里不出现宿主机 IP、绝对路径、权重、媒体、日志。机器相关配置走 `.env.local`。
- 不改系统驱动 / CUDA / 内核；需要时写进 OPERATIONS.md 让人来做。

## 改完必须做

```bash
python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py
python3 -m unittest -v
```

改了 UI 用 `python3 scripts/dev_fake_workers.py` 打开看一眼。改了和 worker 交互的逻辑，在 `tests/fake_comfy.py` 里补对应行为再写测试。

## 流程

通用开发流程遵循本文件的 `HARNESS:MANAGED` 分区，原有流程条款由该分区替代。大改动（新的 worker 形态、换节点、换调度策略）仍须先在 `docs/adr/` 写一页 ADR 再动手。
<!-- PROJECT:OWNED:END -->
