# Director 更新与直达入口部署

## Metadata

- Project: minimax-h3-workflow
- Task: Deploy approved Director update and URL entry
- Timestamp (UTC): 2026-09-16T06:41:32Z
- Owner: project owner
- Route: direct-execute
- Source of truth: AGENTS.md; docs/adr/0003-director-url-entry.md; Owner 本轮要求部署并提供地址

## Changes

接续此前暂停记录 `2026-09-15-director-url-entry.md`。Owner 本轮要求部署；父 session 明确说明保留真实页面待验证，不启用无沙箱浏览器。复查两个上游 checkout 干净、旧服务身份正确及 running/pending 队列为空后，正常停止旧启动器和 child。

执行 `python3 scripts/prepare_runtime.py --code-only`：Director 从 `52f8fb7` 升至 `eb9d274f707012346f23d20a3372fbd4cbc7a9f8`，ComfyUI 保持原 pin，链接项目适配器。无依赖安装、模型下载或转换。

按原 `.env.local` 启动 `python3 scripts/start.py --wait-ready 180`，单 GPU 0、原绑定和端口不变。启动器 PID 1968908，ComfyUI PID 1968952；PID 仅为本次证据，后续停止必须重新核实身份。

## Validation

- 旧 child 正常退出后，首次临时 bind 检查未设 SO_REUSEADDR，因端口 TIME_WAIT 报 Address already in use；`ss` 确认无监听，两个旧 PID 均不存在。改用与现有启动器一致的 SO_REUSEADDR 检查后继续，无强杀、无重复服务。
- `/object_info`：908 个节点，包含 MiniMaxH3Director。
- `/extensions`：包含 H3_Director_Entry/director-entry.js。
- `/`、`/?director=1`、适配器 JS 与 `/h3-director/workflow`：均 HTTP 200；JS 包含已修正的 Escape 判断及非模态层样式。
- 启动后 `/queue` running/pending 均空；没有提交生成任务。
- runtime Git HEAD 与锁目标一致。仍为 CUDA_VISIBLE_DEVICES=0。

## Decision / Residual Risks

部署及服务重启完成。导演台地址为现有服务地址加 `/?director=1`，普通 `/` 保留。真实浏览器交互仍未验证（Owner 拒绝无沙箱方案），HTTP 成功不代替页面验收；新 pin 的真实生成也未执行。原生引用菜单、时间线、返回画布、保存恢复需在正常浏览器确认。不声称全功能通过；未 commit/push。
