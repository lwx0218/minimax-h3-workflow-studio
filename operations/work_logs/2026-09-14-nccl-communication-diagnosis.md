# NCCL 有界通信排障：四卡共享内存绕行通过

## Metadata

- Project: minimax-h3-workflow
- Task: nccl-communication-diagnosis
- Timestamp (UTC): 2026-09-14T10:50:32Z
- Owner: project owner
- Route: direct-execute
- Source of truth: operations/planning/2026-09-14-h3-director-migration.md；Owner 对有界通信诊断的明确授权

## Goal / Summary

原 Director round 因项目环境 NCCL 初始化段错误暂停。Owner 授权主会话做有界通信诊断；开发 session 保持暂停，没有新增产品 round。

**已找到并验证进程级绕行：项目原有环境同时设置 NCCL_IB_DISABLE=1 和 NCCL_P2P_DISABLE=1。四卡连续两次通过数值校验，包括 all-reduce、all-gather、all-to-all、broadcast 和 Gloo 对象广播。**

这解除当前小规模通信前置阻塞，不代表 Director、H3 模型兼容、真实视频质量或四卡端到端加速已验收。底层 IB/RoCE 路径段错误和 P2P 不通的具体根因仍未确定；没有更改驱动、CUDA、内核、BIOS 或包版本。

## Scope / Changes

- 主会话仅创建临时探针与原始日志，随后保留到 ignored `var/h3-nccl-diagnostic-20260914/`，并新增本文。
- 未改业务代码、配置、现有环境或模型；未下载、安装、提交或 push。
- 原项目环境：Torch 2.11.0+cu130、NCCL 2.28.9。
- 独立 dsbi 对照：Torch 2.7.1+cu126、NCCL 2.26.2。整个进程使用对应解释器，没有将 dsbi 库注入项目环境。
- 旧 runtime venv 的 Torch 是指向项目环境的链接，不作为独立栈对照。

## Validation

### 测试矩阵

每组均为新子进程，rank 按物理 GPU 号仅可见一张卡。先验证 CUDA 小张量建立和同步，然后初始化通信组并执行 collective。以下墙钟包含 Python/Torch 启动、初始化、断言与销毁，**不是模型性能或通信带宽基准**。

| case | 环境 / 变量 | 卡数 | 结果 | 墙钟秒 |
| --- | --- | --- | --- | ---: |
| project-lazy | 项目；不传 device_id | 2 | 创建组后首次 all-reduce 双 rank SIGSEGV(-11) | 4.481 |
| dsbi-eager | dsbi；默认 P2P/IB | 2 | 初始化通过，P2P/CUMEM all-reduce 超时，双 rank SIGABRT(-6) | 26.412 |
| dsbi-eager-no-p2p | dsbi；禁 P2P | 2 | all-reduce/all-gather 三轮数值校验通过，退出0/0 | 3.480 |
| project-eager-no-p2p-no-ib | 项目；禁 P2P 和 IB | 2 | 同上通过，退出0/0 | 3.490 |
| project-eager-no-p2p-control | 项目；仅禁 P2P | 2 | 双 rank SIGSEGV(-11)，复现原失败 | 4.482 |
| project-eager-no-ib-control | 项目；仅禁 IB | 2 | 初始化通过，P2P/CUMEM 首次 all-reduce 超时；55秒父截止后 SIGTERM 回收 | 55.266 |
| project-4gpu-shm-collectives | 项目；禁 P2P 和 IB | 4 | 扩展通信集合全部通过，四 rank 退出0 | 5.401 |
| project-4gpu-shm-repeat | 同上，独立新进程重复 | 4 | 再次全部通过，四 rank 退出0 | 5.000 |

四卡扩展探针先建立 NCCL 组及 Gloo 控制组，检查对象广播；随后分别以 4096 和 1048576 个 FP32 元素（每 rank 基础输入约16KiB和4MiB），每尺寸执行三轮 all-reduce、all-gather、all-to-all-single、broadcast 并同步/断言。all-to-all 的输入按源rank/目标rank编码，接收逐元素比较，避免只用常量掩盖路由错误。PyTorch记录的单rank峰值allocated约36MiB，不含CUDA上下文，不能当整卡显存峰值。

探针均设置进程组20秒超时、父进程55秒总截止、终止后3秒kill宽限，并wait回收所有rank。设置RLIMIT_CORE=0，不留下core dump。仅禁IB的失败组watchdog20秒报错后仍未完全退出，由父截止回收；不能把55秒写成NCCL配置超时。

### 判断

- 不传 device_id 仅延迟崩溃到第一次 collective，不能作为修复。
- 在同一项目环境、同一探针、P2P均禁用的对照中，添加 IB_DISABLE 后由段错误变为通过，证明该变量是当前有效绕行条件；没有native崩溃栈，不能进一步断言具体NCCL、verbs或驱动缺陷。
- 仅禁IB后日志显示P2P/CUMEM链路，通信仍超时；dsbi 默认P2P也超时，禁P2P后通过。不能仅凭peer capability=True宣称P2P真实可用，也不据此要求改BIOS。
- 成功四卡日志显示 NET/Socket 和 SHM/direct/direct 通道，GPU仍参与运算，卡间数据通过主机共享内存路径传递；不是改用CPU执行H3。相较直连可能有性能代价，必须后续真实工作负载比较。
- 不需要为解决本次小通信故障降级Torch或更换模型；保持项目环境优先原则。

### 有效参数与复验

已验证的子进程环境包含：

```text
NCCL_IB_DISABLE=1
NCCL_P2P_DISABLE=1
NCCL_SOCKET_IFNAME=lo
GLOO_SOCKET_IFNAME=lo
TORCH_NCCL_ASYNC_ERROR_HANDLING=1
```

前两个是本次A/B新增的关键变量；其余是所有探针共有的单机回环/错误处理设置。设置仅限测试子进程，没有写进系统或现有 .env.local。生产集成应使用相同作用域，在原ComfyUI及其GPU子进程一致生效，不安装替代通信引擎。

本机复验需设置解释器变量为项目环境位置，再用未使用过的label（探针拒绝覆盖旧证据）：

```bash
python3 -B var/h3-nccl-diagnostic-20260914/probe.py \
  --python "$H3_DIAGNOSTIC_PYTHON" --label project-four-gpu-new-check \
  --mode eager --world 4 --p2p-disable --ib-disable
```

- `probe-initial.py`：两卡基础A/B探针，SHA256 `5df812160bf87601ba354105c73718281e29bb2ba9ec2cf078584063e399ee2a`。
- `probe.py`：四卡扩展探针，SHA256 `bb1809f265cca3ad14f56dbd19404bcdae85bcb4dfef18589c391adee171ac0c`。
- 每个case目录含result.json和rank日志。原运行发生于临时目录，日志保留原路径，ignored归档副本不篡改原文。初始两次基础测试早于探针增加P2P/IB开关字段，JSON不含该字段，CLI与日志为准；计算和断言逻辑未变。

### 回归与清理

- python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py：通过。
- python3 -m unittest -v：17 tests，15.771秒，OK；原始输出在ignored诊断目录unittest.txt，仍只覆盖旧项目。
- 全部8组探针的20个rank PID均已消失，GPU compute apps为空；旧Studio/worker及8188端口无监听。没有启动ComfyUI，不声称整机没有其他服务。
- tracked diff与原基线补丁字节相等，分支h3-director、HEAD未变。

## Decision / Next Steps

结论：**communication workaround validated，产品未交付**。主会话直接复核探针断言、逐rank退出码、失败栈、成功SHM路径和重复结果；本次local-only probe不另加开发round或重复review流程，不能称为新的独立reviewer审批。

将证据交还原开发session。其可在原批准计划内采用进程级参数，恢复模型格式/单卡/两卡/四卡真实视频验证，之后继续fresh reviewer与ponytail产品准入。不能跳过模型兼容或据小张量通信估算视频加速；不得把其他所有插件组合视为已测试。

Fleet入站request仍被禁用，notify仅表示消息送达，不触发空闲session执行；本报告不宣称开发已自动恢复。原失败work log/review是历史时间点证据，保留不重写。
