# docs 目录说明

## Metadata

- Project: MiniMax H3 Studio
- Document type: index
- Status: active
- Owner: project Owner
- Last updated: 2026-08-28
- Source of truth: `AGENTS.md` / `operations/planning/rebaseline-plan-v1.md`

## Purpose

`docs/` 保存产品合同、研究事实基线、架构/spec/ADR 和长期参考材料。它不是运行时产物目录，也不是一次性 handoff 或临时 archive 的长期事实源。

## 文档语言标准

- 面向 Owner 的聊天总结、交付说明、状态报告默认中文。
- 新增或实质更新的项目文档正文默认中文。
- 文件名、代码标识、命令、协议字段、必要英文引用可以保留英文。
- 已批准或归档的英文历史证据不强制全文翻译；如需更新，优先补中文状态说明，避免破坏历史语境。

## 目录边界

- `docs/adr/`：已接受或候选架构决策记录。
- `docs/specs/`：产品合同、MVP 范围和验收标准。
- `docs/architecture/`：目标架构、边界和运行模型。
- `docs/development/`：开发流程、质量门禁和工程约定。
- `docs/project-intake/`：项目 intake 和治理入口事实。

`operations/` 保存 Plan、orchestration、work log、review 和 archive。临时 zip、一次性 handoff、runtime residue、模型、cache、logs、database 和 media 不作为长期事实源，也不应放入 Git。

## 当前有效来源

当前 source-of-truth precedence 见：

1. [`../CONTEXT.md`](../CONTEXT.md)
2. [`adr/0001-use-comfyui-as-studio-foundation.md`](adr/0001-use-comfyui-as-studio-foundation.md)
3. [`../operations/planning/rebaseline-plan-v1.md`](../operations/planning/rebaseline-plan-v1.md)
4. [`../operations/planning/orchestration-v1.md`](../operations/planning/orchestration-v1.md)
5. [`../operations/planning/initialization-plan.md`](../operations/planning/initialization-plan.md)

历史 R1/Phase 0 文档只证明已执行事实；其 future-plan clauses 已 superseded，不得恢复为当前标准。`.pi/` 是 capability layer，不是 policy authority；simple task 不因文档或工具存在而自动升级为 formal gate。
