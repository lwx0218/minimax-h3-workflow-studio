# Director 指定网卡增量复核

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-lan
- Timestamp (UTC): 2026-09-15T06:51:28Z
- Owner: project owner
- Route: review-only
- Source of truth: operations/planning/2026-09-14-h3-director-single-gpu.md

## Decision / Finding

Fresh 项目 reviewer：**approve_with_follow_up**；无P0/P1阻塞，**ponytail代码准入通过**。父session接受本次指定网卡配置增量，不重新裁决已验单卡模型范围。

唯一P2：builder称浏览器session残留文件为空，但原始记录仍有专用 `.config`。交付说明现更正为：**浏览器已关闭，仍保留session配置文件**。配置文件不等于浏览器进程存活；不删除其他session，不改写原始报告。此文字纠正无需重新运行产品测试。

## Verified Scope

- `H3_DIRECTOR_HOST`默认回环，可配置单个私网/回环IPv4；拒绝URL、非法值、通配和公网。监听、占端口检查、节点readiness及显示URL同源；本机探针局部无代理，不改全局代理。
- 实际地址仅ignored `.env.local`，四文件LAN增量无机器IP；无防火墙、全网卡、公网、环境安装或模型变更。
- 旧实例及首次LAN实例均在确认空队列/进程身份后优雅停止；同指定地址重启通过。仅一个单GPU ComfyUI/Director，必需节点齐全，最终queue/history空。
- 指定地址实际浏览器页面、既有视频访问、重启后Director图加载通过，未提交新生成任务。首次CDP超时与一次获准同协议恢复证据保留。
- 测试覆盖默认/指定host、非法值、占端口、失效代理与同地址启停重启；builder原始26 tests通过。父session另行重跑py_compile、26项unittest及diff check均通过，日志 `var/h3-director-lan-20260915/parent-unittest.txt`。
- 父session无代理独立读取queue/object_info，确认队列空、Director节点存在；核对launcher/child身份及只在指定本机地址30210监听。未提交GPU任务、未再次重启。

## Artifacts / Limits

- 产品增量：`scripts/start.py`、`tests/test_start.py`、`docs/director-single-gpu.md`、`operations/work_logs/2026-09-15-h3-director-lan.md`；另有ignored `.env.local`。本文为父session交付摘要。
- 审前增量SHA256经父复算：`3490819663907c0471bdc0f7f31958da26601b25fc79a31e7361cde74bc47a14`；原快照保留不覆写。
- Workflow：`75ce23bb-56ae-4884-aa88-186acd5826bb`；builder：`80bb5051-5018-469d-bee6-b9bbd2a7f90b`；fresh reviewer：`743e994d-049e-4a28-9e55-2419c0f107cc`。
- Runtime绑定输出 `director-lan/builder.md`、`director-lan/reviewer.md` 已完整读取；准确宿主路径通过workflow receipt/Fleet交接。
- 原始证据 `var/h3-director-lan-20260915/`；实际URL、当前PID在本机交付消息与ignored状态中。服务继续保留，停止前再次确认队列空闲及PID身份，不盲用历史PID。
- 只验证本机经指定网卡访问，**未从另一台LAN客户端验证连通性**；ComfyUI无鉴权，仅适合获准可信网络。无提交或push，原单卡P2数值回归后续项及其他验证边界保持。
