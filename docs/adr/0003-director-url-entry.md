# Director URL 入口复用原生编辑器

## Metadata

- Project: minimax-h3-workflow
- Document type: other
- Status: active
- Owner: project owner
- Last updated: 2026-09-15
- Source of truth: AGENTS.md; Owner approved bounded task

## 决策与范围

Owner 已批准更新 Director 至 `eb9d274f707012346f23d20a3372fbd4cbc7a9f8`，新增自动载入项目原生图、隐藏节点画布并可返回的最小专用入口。实现留待 reviewer、ponytail 与父 session 的 live browser/deploy 检查，不将历史采样视为本次通过。

原生 Focus Mode 仅隐藏菜单，仍显示画布；上游无独立 Director 页面。选择项目独立 Comfy extension，只在 `/?director=1` 将已存在的 Director 编辑器 DOM 放进非模态全屏容器，返回归还原 DOM。非模态保留上游附加到 body 的提示词引用菜单交互；图已清理时只移除入口，不复活已销毁编辑器。图、事件、序列化、Run 与执行全部来自原生 ComfyUI/Director，不 fork 或 vendor 上游，不引入第二应用、画布或 workflow 格式。

等原生恢复结束后，恢复中的项目 T2V 图直接复用，否则调用原生无文件名的新临时标签加载。用户从原生 Save / Save As 保存，适配器不写用户存储。固定 HTTP 资产接口返回项目原生 T2V JSON，不接收动态路径。

## 后果与验证

私有 editor DOM 和固定前端启动状态是有意的有界依赖；上游变更必须重新浏览器验证，不能宣称通用跨版本支持。普通 `/` 保持不变。安装仅通过 prepare 链接，启动显式 allowlist；新增 `--code-only` 保证本轮部署不执行模型转换或依赖操作。

Python/Node 行为测试验证加载与返回合同、固定资产路径、安全幂等链接和 allowlist；真实 DOM、上游弹窗、保存恢复和无自动排队由父 session 在部署后验证。具体 URL、操作与局限见 [运行说明](../director-single-gpu.md#director-专用入口本次增量待部署后浏览器复核)。
