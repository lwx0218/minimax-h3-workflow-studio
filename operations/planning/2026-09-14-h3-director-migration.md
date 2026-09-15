# H3 Director 单轮迁移计划

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-migration
- Timestamp (UTC): 2026-09-14T10:58:39Z
- Owner: project owner
- Route: plan
- Source of truth: AGENTS.md；本会话 Owner 已批准的 Plan Preview；Owner 本次批准的依赖隔离修订

## Goal / Summary

Owner 明确批准：通过 Pi Fleet 分发一个 round，由开发 session 自行完成 builder 实现、只读 reviewer 复核、ponytail 准入及验证，不逐项要求 Owner 审核。目标是原生 ComfyUI + AIMixer Director + 现成多卡推理插件，不再扩建旧 Studio。

只启动一个 ComfyUI 服务和界面；允许内部 GPU 推理子进程。多卡协作生成同一条视频，接受四卡采样，第五卡仅在兼容时承担编码或解码，不要求五卡同时满载。

## Scope / Changes

### 唯一 round：h3-director

- 目标：验证并交付单服务 Director 多卡生成的最短可行路径。
- 改动面：新的启动/停止与必要准备脚本、运行时/模型配置、原生示例工作流、最小测试、说明文档、一页 ADR，以及 ignored 本机环境和模型链接。
- 完成判据：见 Validation；若硬件或现成插件使目标不可达，停止迁移、保留旧方案和证据，明确报告 blocker，不能冒充完成。

### 分支与工作区

已从 cleanup 非破坏性建立 h3-director 分支，HEAD 仍为 389e550f97b57d320e088f50b74d2ed36d19818d。继续使用该分支与原开发 session，不再新建 round 或 Fleet session。

已有无关改动必须保留：AGENTS.md、README.md 已修改；.pi/、Harness_manual.md、docs/manual/、docs/project-intake/、operations/ 及 docs 中一个 zip 为既有未跟踪内容。本计划初次保存后，另有 Owner 授权的代理注册修复及通信诊断记录；应按各自证据归属，不计为产品实现。不得 reset/clean/stash 掩盖这些改动，不自动提交无关内容，不 push。

开发 session 接管后为此 cwd 唯一 writer；orchestration 只读协调。此次 Owner 授权主会话更新计划，开发 session 保持暂停；更新完成后仍须等待 Owner 明确让下游继续。原基线已保存于 ignored 目录，续作先核对新增治理/诊断内容，不得覆盖。产品 round 不能修改 .pi/、AGENTS.md 或 Harness managed 分区。

### 环境

- **运行时仅使用项目 .venv，不允许向 dsbi 自动回退第三方包。** 本修订替代此前“缺包时复用 dsbi”可能产生的运行时回退解释。
- 将 .venv-h3 迁移为 .venv，保留已有有效依赖，修复入口/shebang/激活脚本引用，并验证 python、pip 和启动命令。检查 Git 忽略规则，环境不纳入版本控制。
- 新 ComfyUI 服务和全部推理子进程必须使用同一 .venv 解释器。保持 include-system-site-packages=false，不通过 PYTHONPATH、.pth、包软链接或旧启动钩子将 dsbi/site-packages 注入其中；不再沿用 var/runtime/venv 的三层包回退机制。允许继续使用 dsbi 提供的基础 Python 解释器及标准库，这与继承其第三方包是不同边界，无需为此重装 Python。
- **准备时复用资源，而不是运行时混包：** 优先保留项目已有兼容包，其次使用本机兼容 wheel/安装缓存安装到 .venv；dsbi 可用于版本清点和独立对照，不作为运行时第三方包来源。仅有 dsbi 已安装目录、不具备可验证安装包时，不直接复制或链接它来绕过依赖解析。
- Torch、torchvision、torchaudio、Triton、NCCL、CUDA 用户态库及依赖它们的编译扩展按同一兼容集合验证，任何一个都不得跨环境自动回退；普通纯 Python 包也要检查版本约束。缺包明确报错，不悄悄换解释器或库路径。
- 确实缺少的依赖使用阿里 PyPI 源下载到项目环境。包不在源中时报告，不悄悄切换来源或安装系统组件。不修改 dsbi 或全局环境。
- config/requirements-lock.txt 和 runtime-lock.json 与实装版本有漂移：当前项目 Torch 2.11.0+cu130 / NCCL 2.28.9，原锁文件写 Torch 2.14.0+cu130 / NCCL 2.30.7。不得盲目按旧锁重装或仅修改版本号假装兼容；先验证选定集合，再更新为实际可复验的依赖记录。
- 模型仅从 ModelScope 直连下载，禁用代理，包括 7890；模型根使用 Owner 指定目录，具体绝对路径只进入 .env.local 或本机运行参数，不写入受版本控制文件。
- 不改驱动、CUDA、内核、BIOS；不删除已有权重、备份或媒体。

### 模型与现成集成

- 原生 ComfyUI + AIMixer/ComfyUI_MiniMaxH3_Director；不 fork ComfyUI，不重写画布、DAG、workflow 格式或多卡引擎。
- 优先验证 buqi-code/buqi-minimax-h3-multigpu 的四卡协作路径。其内部子进程是允许形态，不是五套 ComfyUI。不得把上游 Blackwell 测速当作本机 A5000 结果。
- 本地 Qwen3-VL-32B INT8 ConvRot 已存在，优先保留原件并验证最小格式转换；目前仅做过文件头级检查，原生 detect_te_model 误认 8B，键名前缀归一化后才识别 32B。识别通过不等于推理通过。
- 本地 FL2VA INT8 为旧 RH 使用版本，注意 QKV 布局，不能只改文件名或以加载成功证明正确。优先评估 Abiray/Minimax-H3-nvfp4-INT4-INT8-Convrot 的剪枝 INT8 FL2VA（约 19.53 GiB）。
- 两个已有 VAE 的关键结构与原生加载器匹配，先复用并验证。
- Ref2VA 主权重本地缺失，目录只有 sidecar；仅需参考主体/视频编辑功能时补齐，不整包下载。
- Abiray README 推荐 INT8 Qwen，但调研时实际仓库不存在 text_encoders，下载路径 404，不能把 README 当作文件可下载证明。
- 暂不叠加 Turbo、二采、放大或提示词增强模型；不要求再下载通用 embedding 模型。

### 通信诊断结论与适用边界

主会话有界诊断已在原项目环境找到进程级绕行，见 [通信诊断记录](../work_logs/2026-09-14-nccl-communication-diagnosis.md)：

```text
NCCL_IB_DISABLE=1
NCCL_P2P_DISABLE=1
NCCL_SOCKET_IFNAME=lo
GLOO_SOCKET_IFNAME=lo
TORCH_NCCL_ASYNC_ERROR_HANDLING=1
```

前两项是关键 A/B 变量，其余是已测单机回环/错误处理设置。两卡通过，四卡两次通过 all-reduce/all-gather/all-to-all/broadcast 数值校验和 Gloo 对象广播；采用 SHM 主存中转，不能视为模型性能基准或硬件底层问题已修复。

恢复后仅在项目本地启动参数/ignored 配置中设置并传给服务及所有推理子进程，不修改系统级配置。迁移后的 .venv 要复验同类有界通信；暂不为绕过本次故障更换 Torch/NCCL。模型、视频、速度和 Director 界面仍未验证，原失败 work log/review 保留为历史记录。

## Validation

1. 已有 docs/adr/0002-director-single-service-multigpu.md；如需更新其环境/通信取舍，仅作最小修改，不重复创建 ADR。
2. 静态检查模型、依赖与插件契约及内存需求；确认唯一解释器、sys.path、关键模块 __file__、实际加载的 NCCL/CUDA 用户态库、pip check 和与关键编译扩展相称的 smoke test。排除 dsbi 第三方包路径和旧回退钩子后，再核对锁文件与实装集合一致；pip check 通过本身不是 ABI 正确证明。迁移后的有界 GPU 通信探针采用上述参数、设置超时并回收所有进程，不能仅以初始化成功代替 collective 数值校验。
3. 单卡短视频建立正确性和耗时基线，两卡通过后才试四卡。采样参数、尺寸、帧数、种子和冷/热启动条件清楚，至少同条件重复以区分噪声。
4. 真机验证 Director 文生及图生/首尾帧路径，产物有正常视频和音轨；通过进程/端口与设备证据确认只有一个 ComfyUI 服务，四卡参与同一任务。
5. 记录端到端耗时、分阶段耗时（可获得时）、主存、每卡显存及失败信息；证明多卡有实际收益，不预先承诺倍率。
6. 第五卡是否接入和未验证功能明确标注；不是以五卡全程满载作为验收。
7. 运行 python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py 与 python3 -m unittest -v。若改旧 UI/worker 交互，遵守 AGENTS 对 fake worker 与 UI 检查要求；不为了该要求启动真实五 worker。
8. 实际浏览器检查新 Director 页面/工作流；运行最小启停检查，防止遗留子进程或意外外网暴露。
9. fresh-context reviewer 只读复核最终候选，输出 approve / approve_with_follow_up / return_to_planning；ponytail 检查仅保留必要胶水代码。修复后按需复核，不能把接受回执当审查完成。

## Decision / Next Steps

状态：approved revision / paused-awaiting-owner-resume。本次仅更新 Plan 并通知下游，**不得因收到通知自动恢复开发**；Owner 将另行在下游明确要求继续。

原 Pi Fleet 开发 session 为 01-h3-director。前一次 workflow 已完成并以未交付收尾，不能伪装成仍在运行；小规模通信阻塞已有已测绕行，但 .venv 迁移、模型下载/转换、部署和视频验收仍未执行。

Owner 让下游继续后，先重新读取此修订、确认 baseline/角色 capability，再按 pi-subagents guide 对可恢复 child 做同协议续作；仍在原唯一 round 内，以当次一个顶层 async workflow 编排有依赖的 builder 与 fresh reviewer，不重复起 Fleet session。同一 cwd 不并发 writer。工具/认证/工作流基础设施失败必须停止，报告具体 run/status/cwd/branch 和部分 diff，不绕过协议换 CLI。

通信、内存、格式问题无法在此 bounded change 内解决，或四卡没有实际收益时停止并回报 orchestration；不降级成五套 ComfyUI，不继续研发新推理引擎。普通 review/fix 由开发 session 完成，无需 Owner 逐项确认。scope 或破坏性授权变更才升级。

交付：新入口与说明、可导入原生工作流、最小必要 diff、可复验的 work log/review、最终状态和残余风险。日志/媒体/权重保留在 ignored 本机位置，证据中不嵌入机器 IP/绝对路径或大块原始日志。
