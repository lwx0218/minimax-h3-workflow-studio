# Agents

这个目录只保留最小 agent 说明，不预置重型角色矩阵。

当前默认协作面只有一条：

- 先读 `AGENTS.md`
- 再读 `.pi/skills/` 与 `.pi/prompt-templates/`
- 先过固定前置 gate，再决定是直接执行、进入 `Plan`，还是停在 starter 边界外

默认不要求 planner、coder、reviewer 角色全量出场。

如果后续需要更细的角色拆分，应在外部项目内按真实需求补充，而不是把 starter 扩展成通用运行时框架。
