# Director 单卡候选复核：未准入

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-single-gpu
- Timestamp (UTC): 2026-09-15T02:03:09Z
- Owner: project owner
- Route: review-only
- Source of truth: operations/planning/2026-09-14-h3-director-single-gpu.md

## Decision

Fresh 项目 reviewer：**`return_to_planning` / `boundedFixes=false`**。Ponytail 认可最小性方向，但**代码及产品准入不通过**。父 session 接受结论，保留未提交候选，不启动产品、安装依赖或裁切模型。

模型独立副本裁尾的控制门返回 false；不经自动修复、loader 绕过或更换模型/精度替代授权。这不是宣布项目永久取消。准备/启动等普通缺口仍属原任务范围，不因此新增产品需求；当前模型硬阻塞未解除，未进入自动 fix。

## Findings / Disposition

- **P1 模型/授权阻塞**：FL2VA 源文件 SHA 与上游列表相符，但比张量覆盖末端多72字节。932个张量长度及连续offset正确，200个I8权重均有quant，尾部为文本标记。原件保持 `.part`；合法目标文件尚不存在，真实 prepare 已失败，不能声称成功。safe_open错误由builder报告和格式诊断支持，reviewer未见独立保存的原始错误输出。
- **P1 依赖不可安全复建**：`--install-deps` 使用无精确CUDA构建身份/来源哈希的普通版本清单，`--no-deps` 不能防止显式Torch项漂移；同时记录两个共享cv2的OpenCV provider。**不要执行此安装分支作为已验复建流程。** 后续需禁用不可信安装路径或fail closed、保留观察清单、收敛单一OpenCV provider，不能重装当前Torch/CUDA试错。
- **P1 真机闭环缺失**：未测T2V重复、I2V/首尾帧、有效音视频、Director导入提交播放和真实ready/stop/restart；耗时/RAM/VRAM缺测。原生图存在、Qwen字节一致和单测通过均不替代这些条件。
- **P2 readiness误导**：启动器只测 `/system_stats` 却称Director ready；应收窄为ComfyUI HTTP ready，或检查必需节点再声明产品就绪。尚未修复。
- **P2 生命周期测试不足**：假HTTP child写标记早于监听，测试可能没走成功ready；未证明端口关闭、PID消失、重启及关键失败分支。尚未修复，不能把20项单测当真机启停验收。

正面结果：prepare/start共用项目 `.venv`，默认只起一个回环单GPU Director child；旧Studio须显式选择；删除dsbi第三方fallback。Qwen转换副本保留payload和350份quant，原件未改。无多卡插件、推理数学补丁或新调度框架。

## Evidence / Parent Checks

- 候选10文件：`scripts/start.py`、`scripts/prepare_runtime.py`、`config/runtime-lock.json`、`config/requirements-lock.txt`、`tests/test_start.py`、`workflows/comfy-ui/director-single-t2v.json`、`README.md`、`docs/adr/0002-director-single-service-multigpu.md`、`docs/director-single-gpu.md`、`operations/work_logs/2026-09-15-h3-director-single-gpu.md`。本文为父session另存复核摘要；治理与历史不纳入产品diff。
- Workflow：`29a6e16a-b59f-4dbb-90e6-090f74d30c1c`；builder：`76489eeb-60ba-4cc0-b901-7c2e0d5be004`；reviewer：`6ad415af-4229-4e0e-806b-72544e62ff18`。执行完成不是验收通过。
- 绑定的 `single-gpu-browser-ready/reviewer.md` 实际为空，不能称其是完整审查artifact。父session读取runtime `structured-output` 的 `output.json`，完整原样备份至ignored `var/h3-director-single-20260914/reviewer-structured.json`；该JSON有verdict、boundedFixes及完整report。准确runtime宿主路径已通过Fleet交接，不写机器路径入本文。
- 父session独立重跑py_compile与20项unittest，均exit0；测试输出 `var/h3-director-single-20260914/parent-unittest.txt`。未运行GPU推理或安装。
- `git diff --check`通过，无暂存/提交/push；候选SHA256独立复算为 `ccc22ea87831fc09e5816208f9aa35e1b9760a6d32da1c5268c05831c97c88b8`，审前快照保留不覆盖。
- 父session最终检查GPU compute-app为空，30210–30215及8188无监听；builder已关闭专用浏览器。无产品URL/PID，不声称整机无其他服务。
- torchcodec共享库、Qwen历史析构TypeError、完整模型许可证未独立取得等风险保留；不分发权重。

## Related Files

- [单卡执行记录](../work_logs/2026-09-15-h3-director-single-gpu.md)
- [候选运行边界](../../docs/director-single-gpu.md)
- ignored原始证据：`var/h3-director-single-20260914/`（历史目录日期，实际本次执行为UTC09-15）。
