# Director 更新与直达入口：候选已准备，部署暂停

## Metadata

- Project: minimax-h3-workflow
- Task: Director upstream update and native editor URL entry
- Timestamp (UTC): 2026-09-15T09:55:00Z
- Owner: project owner
- Route: direct-execute
- Source of truth: AGENTS.md; docs/adr/0003-director-url-entry.md; 本次 Owner 聊天确认

## Scope / Changes

Owner 批准上游更新、最小原生导演台直达入口及验证后重启。目标锁由 `52f8fb7` 改为 `eb9d274f707012346f23d20a3372fbd4cbc7a9f8`，上游只增加默认关闭的二采前显存清理选项，没有依赖更新。实际 runtime 尚未 checkout 新版本。

新增项目 Comfy extension `comfy_extensions/H3_Director_Entry`，固定工作流接口及 opt-in `/?director=1`；复用原生图加载、Director DOM、运行和保存。增加 `prepare_runtime.py --code-only` 及启动白名单，不下载/转换模型，不安装依赖，不改系统或 GPU/网络配置。

## Review / Corrections

工作流 `0dfa4b1c-d711-4569-981c-148f79ec7f8a`：builder `24a44933-e5c0-410e-ba98-74b466f2992a`，fresh reviewer `88c03608-202f-47f8-a2eb-743f857ab059`。

初次复核发现 HTML modal 阻挡 body 引用菜单、图销毁后清理可能复活旧编辑器。父 session 改成非模态 section，并检查 editor/root/graph 身份，使用 finally 清理；添加销毁先于 hook 和 flush 抛错测试。

保留 reviewer 续审 `2af28429-6ba2-48f6-8dce-2df644b3364c`：`approve_with_follow_up`，允许部署后验证，ponytail gate 通过，不代表 live 验收。其 P3 建议是尊重子控件已处理的 Escape；父 session 已补 `!event.defaultPrevented` 和行为测试并重跑全套测试。

## Validation

- `python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py comfy_extensions/H3_Director_Entry/__init__.py`：通过。
- `node --check comfy_extensions/H3_Director_Entry/web/director-entry.js`：通过。
- `python3 -m unittest -v`：29 tests，22.922s，OK；包括执行 JS 模块的模拟 DOM 行为测试。不是实际浏览器布局证明。
- `git diff --check`：通过。
- 部署前只读快照：当前服务 PID 身份与项目一致，GPU 0，queue running/pending 均为空。停止时仍需再次检查，不能复用此快照。
- Chrome 页面验证启动失败：`No usable sandbox!`；没有获得任何本轮真实浏览器验收结果。

## Decision / Next Steps

Owner 拒绝使用临时 `--no-sandbox` 浏览器；未使用该参数、未修改系统安全设置。后续“部署并重启且页面由 Owner 确认”选择没有收到明确答复，因此保持 fail closed：**未部署、未重启、未提交采样任务，现有服务保持旧版本运行。**

候选改动保留在工作区，未 commit/push。继续前需可用的带沙箱浏览器验证路径，或 Owner 明确批准以真实页面待人工确认的状态部署。部署时先复查队列和 PID，正常停止，再执行 code-only 准备和原配置启动；仍需 HTTP/节点/队列检查及真实页面的编辑、引用菜单、返回画布、保存恢复验证。新 pin 采样未验证，不复用历史结果。
