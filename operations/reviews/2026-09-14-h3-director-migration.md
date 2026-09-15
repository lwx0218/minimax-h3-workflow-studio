# H3 Director 迁移复核与处置

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-migration
- Timestamp (UTC): 2026-09-14T10:40:11Z
- Owner: project owner
- Route: review-only
- Source of truth: operations/planning/2026-09-14-h3-director-migration.md

## Findings / Decision

项目 fresh-context 只读 reviewer 结论：**`return_to_planning`**。迁移未交付，不因旧 Studio 回归通过而宣称完成。

- **P1 通信前置失败**：两次两卡探针的每个 rank 均在 NCCL 初始化时返回 -11，禁 P2P 未消除失败。支持停止迁移，不足以确定根因、硬件永久不支持或插件必然失败。处置：停止部署、下载及环境切换；通信栈修复需独立有界任务。
- **P1 验收缺口**：未验证单卡→两卡→四卡视频、同条件收益、单服务四卡同任务、音画、Director 浏览器、Qwen/FL2VA/VAE 推理兼容。处置：全部保留为未验证，不降级验收。第五卡未接入已披露。
- **P2 清理措辞过宽**：原 work log 的“没有外网服务”不能由清理快照支持。父 session 已将其修正为“本轮未新增外网监听服务”，明确既有监听不在范围内；未关闭范围外服务。仅文字收窄，不需重新运行 GPU 探针，未声称 reviewer 对修后文本另作复核。

## Ponytail 准入

Reviewer 判定：**通过文档候选的最小性准入，不通过产品迁移完成准入**。没有新引擎、调度平台、启动框架或无法验收的工作流胶水，未发现应删除的实质冗余代码。仅保留 ADR、失败证据及本审查摘要；原环境和业务代码保持不变。

## Evidence / Final Checks

- Workflow：`047d7b77-9618-4164-84b5-8e7dd1726ff5`。
- Builder：`4267f366-31bd-46a2-838d-adbbb302a3a8`；reviewer：`0f10299c-e5c2-49db-9071-d435d94f6e8d`。两 child 均完成；执行完成不是产品验收通过。
- Runtime 绑定输出：`h3-director/builder.md`、`h3-director/reviewer.md`；准确宿主位置见 workflow receipt 的 output references，不将机器绝对路径写入本文。
- Reviewer 已读原始探针源码、rank 日志、result.json、候选全文、回归及清理日志；未运行 shell。RAM 为整机稀疏采样最大值，不是进程 RSS 或精确峰值。
- 父 session 独立复算审前 `candidate.diff` SHA256：`17aa8fec28a8d05e5f1a21c1084c04f8a0aa17f34648f15b8d9b83fbd86031a6`。该快照保留不覆写，之后仅上述 P2/结论更新及本摘要。
- 父 session 重跑 `python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py`：exit 0；`python3 -m unittest -v`：exit 0，17 tests，15.274 s，OK。输出在 ignored `var/h3-director-validation-20260914/parent-unittest.txt`。
- 父 session 确认 tracked diff 与 ignored 基线补丁字节相等、`git diff --check` 通过、无 staged 文件。既有治理修复不计本轮产品改动；无 commit/push。
- 最终只读进程检查：四探针 PID 不存在，GPU compute-app 列表为空，旧 Studio/worker 与 ComfyUI 默认端口无监听。本轮未部署服务，无新增访问入口；不据此声称整机无其他服务。

## Related Files

- [执行证据](../work_logs/2026-09-14-h3-director-migration.md)
- [架构决策](../../docs/adr/0002-director-single-service-multigpu.md)
- ignored 本机原始证据：`var/h3-director-validation-20260914/`
