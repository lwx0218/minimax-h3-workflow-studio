# Director 指定LAN绑定增量

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-lan
- Timestamp (UTC): 2026-09-15T06:45:22Z
- Owner: project owner
- Route: direct-execute
- Source of truth: operations/planning/2026-09-14-h3-director-single-gpu.md

## Change / Validation

沿已验单卡候选续作，仅增加 `H3_DIRECTOR_HOST`：默认回环，显式值限单个私网/回环IPv4，拒绝URL、非法值、通配和公网地址。监听、占端口检查、节点readiness与CLI显示共用WorkerSpec；本机探针使用无代理opener，不改全局代理。实际地址仅在ignored `.env.local`。

核实旧launcher/child父子身份及空队列后SIGTERM正常停止；指定网卡启动，确认必需Director节点与单可见GPU，再次核实空队列/身份，正常stop→同地址restart。两次均检查child消失、端口关闭和PIDfile删除。最终仅一个ComfyUI、只在指定地址监听，回环和其他worker端口未监听；准确URL/PID在ignored `final-state.json`。

浏览器首次Page.navigate、随后DOM.enable超时；doctor为7 pass。按控制门明确授权，仅close专用session并清除浏览器子进程代理环境，同CLI/session/no-sandbox重开一次成功，没有改系统代理或换工具。指定地址页面、既有视频/view访问正常；重启后加载既有Director图并截图，**未点击Run、未提交任何生成**。浏览器已close。保留首次失败，不能把恢复前状态算通过。

`py_compile`通过；`python3 -m unittest -v`：26 tests / 22.945s / OK。补默认/指定host、非法URL等拒绝、指定host占端口、假HTTP child同地址stop/restart和失效代理环境readiness回归。没有安装依赖、下载模型、修改权重/精度/Torch/CUDA或重跑四条视频。

## Evidence / Limits

增量相对已验单卡候选，只有start、test_start、运行说明及本文；`.env.local`另为ignored本机配置。既有治理、历史报告及其他dirty未清理或覆盖，无暂存/提交。

原始证据：`var/h3-director-lan-20260915/`，包括前置/停止queue与身份、两次监听/启动、最终隔离状态、browser失败与恢复、页面和既有媒体截图、测试及`lan-increment.diff`。

本机通过指定网卡地址的访问已验；未从另一台LAN客户端验证路由或防火墙，不宣称跨机器可达。ComfyUI无鉴权，仅应置于可信网络；未新增公网/全网卡监听。该LAN增量已获独立review `approve_with_follow_up`、ponytail准入通过；交付纠正：浏览器已关闭，但仍保留专用session配置文件。见[复核记录](../reviews/2026-09-15-h3-director-lan.md)。不覆盖原单卡review与其P2后续项。
