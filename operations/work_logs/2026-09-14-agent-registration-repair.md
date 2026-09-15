# 项目代理注册修复

## Metadata

- Project: minimax-h3-workflow
- Task: agent-registration-repair
- Timestamp (UTC): 2026-09-14T10:27:17Z
- Owner: project owner
- Route: direct-execute
- Source of truth: AGENTS.md；Owner 本会话对独立治理小修的明确确认

## Goal / Summary

H3 Director round 在 capability preflight 阶段阻塞：项目角色文件没有 YAML frontmatter，pi-subagents 忽略这些文件。未产生子代理 run，状态 preflight-blocked，而非 ComfyUI/GPU 验证失败。

Owner 授权 orchestration 单独修复两个角色文件，不扩大产品 round，不修改全局设置或 Fleet 请求权限。开发 session 在此期间保持暂停。

## Scope / Changes

- .pi/agents/builder.md：新增 name、description、tools、systemPromptMode、inheritProjectContext、inheritSkills、acceptanceRole。允许实现所需读写工具和 supervisor 通信。
- .pi/agents/reviewer.md：新增对应字段，工具仅 read/grep/find/ls/contact_supervisor，无 bash/edit/write；defaultContext 为 fresh，acceptanceRole 为 read-only。
- 保留两文件原职责正文，不新增依赖、扩展或额外开发 round。
- 不修改 AGENTS.md、Harness managed 内容、planner.md、业务代码、模型、虚拟环境或 Fleet 权限。

## Validation

- 修复前 subagent list capabilities=true（含 project scope）仅显示 builtins。
- 已安装 pi-subagents 的 agents.ts 中 loadAgentsFromDefinitionFiles 对缺少 frontmatter.name 或 frontmatter.description 的文件直接 continue，确认根因。
- 修复后 subagent list capabilities=true, agentScope=project 明确显示 builder (project) 和 reviewer (project, context: fresh)，工具权限与设计一致，项目 reviewer 覆盖 builtin。
- python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py：通过。
- python3 -m unittest -v：17 tests，15.276s，OK。此为既有项目回归检查，不代表 Director 或多卡已验证。
- ponytail：只补必要元数据并保留正文，无新抽象、运行时代码或依赖；无需为两份声明配置新增测试框架。

## Decision / Next Steps

注册层阻塞已修复，尚未证明 child 真实启动成功；开发 session 恢复后必须重新做自身 capability preflight，再使用原计划的单个 async workflow 启动 builder 和 fresh reviewer。

另查明 Fleet 的 requests_disabled 是默认入站请求权限，不是连接故障；notify 正常但不触发模型执行。本次未绕过或更改该权限。向开发 session 发送恢复通知不等于已恢复执行；空闲 session 需 Owner 输入继续，或 Owner 通过 Fleet UI 明确启用请求后使用受许可 request。

当前分支 h3-director，HEAD 保持 389e550f97b57d320e088f50b74d2ed36d19818d；原有 dirty/untracked 内容保留。本治理小修应与产品候选分开归属，开发 session 不应将其算作业务实现。
