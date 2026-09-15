# H3 Director 单卡闭环续作任务

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-single-gpu
- Timestamp (UTC): 2026-09-15T02:22:27Z
- Owner: project owner
- Route: direct-execute
- Source of truth: AGENTS.md；Owner 已批准单卡闭环；本次明确指定复用现有 MiniMax-H3-INT8-CONVROT 目录，禁止继续下载模型

## Goal / Summary

Owner 在单卡交付后追加授权：改为通过本机指定局域网网卡地址访问，不再只监听回环。该地址已由主会话核对网卡，具体值只通过 Fleet 和 `.env.local` 传递。此项替代下文“仅回环/固定回环”的绑定限制；仍只启动一个服务、一个 GPU。增加可选 `H3_DIRECTOR_HOST`（未配置默认回环），实际配置仅绑定指定网卡，不绑定所有网卡、不改防火墙。重启前确认队列空闲，验证指定地址的节点 readiness、页面与停止/同地址重启；保留既有模型、环境及无下载约束。浏览器临时 no-sandbox 授权仍仅用于本机项目页面，可使用此次指定的本机局域网地址，不扩大到其他站点。此为原交付的有界配置续作，builder/fresh reviewer 自行完成普通修复，不新增产品规划。

本次授权替代原多卡计划的当前交付目标和暂停指令：先交付一个原生 ComfyUI 服务 + AIMixer Director，以一张 A5000 完成真实音视频生成、界面操作和可复验启停。多卡协作、第五卡及提速不再是本次完成条件；不等待多卡调研结果才执行。

沿用 `01-h3-director` session、`h3-director` 分支及当前候选，作为原任务的有界续作，不新开 Fleet session。历史失败和 review 保留，不能覆盖为成功。原环境隔离、阿里源、安全及治理边界继续适用；本修订撤销此前为本任务下载模型的授权。

## Scope / Changes

- 收尾准备与启动：统一项目 `.venv`，删除对旧 runtime/venv 的新路线依赖，依赖记录与真实验证集合一致；不按漂移旧锁重装 Torch/CUDA，不恢复 dsbi 混包。默认入口不得误启动五 worker。旧资源与无关改动保留，旧入口若继续保留必须清楚区分。
- 原生 ComfyUI + Director 单实例、单可见 GPU。允许 CPU offload、原生 tiled VAE/低显存选项，先跑最小合法短片，不因速度慢改用多卡或新引擎。
- 不部署 buqi，不修其导入或量化数学，不加其他多卡插件。没有新 Studio/画布/调度器。
- 复用本地 VAE/Qwen；Qwen 的内存前缀归一化已真实文本编码通过，但需收敛为可复验准备方式，并验证实际工作流。保留原模型，不以仅识别成功冒充正确。
- **只使用 Owner 指定本机 `MiniMax-H3-INT8-CONVROT` 目录下的模型，不再下载任何模型**（包括自动下载的 tokenizer/processor 等模型资产）。主模型为 `MiniMax-H3-FL2VA-int8_convrot.safetensors`，编码器为 `qwen3-vl-32b-int8_convrot.safetensors`，复用同目录视频/音频 VAE 和已有 sidecar。实际绝对路径仅走 `.env.local` 或本机参数。已有新下载 `.part` 保留为失败证据，不继续其裁尾、修复或重新下载。
- 先核对指定本地模型的合法容器、键名、shape、量化元数据及实际加载器路径。RH 与原生 QKV 布局是否不同必须用当前源码/数据验证，不能直接套用历史推测宣布不可用。允许沿既有格式转换范围做可证明等价的独立副本转换（如键名前缀归一化）；布局重排必须同时保持对应 scale/量化元数据，先有小型数值等价检查，再真实单卡推理。保留原件，不改模型精度、不研发推理引擎。不能证明等价或需删除未知内容时停止说明具体差异，不通过改扩展名、忽略loader错误或下载新模型绕过。此前被拒绝的72字节裁尾授权未被本指令恢复。
- 必须安装的缺包优先本机兼容 wheel/cache，再阿里 PyPI；保持已验证 Torch/CUDA集合，不改系统、dsbi 或全局。
- 更新最小 ADR、运行说明与原生 ComfyUI workflow，机器路径/媒体/日志只在 ignored 本机位置。没有交付前不要把 README 写成已经完成。

## Validation

1. 核对 baseline、实际解释器/sys.path/关键库路径及 pip check；准备与启动一致性必须有测试，不能只测试 `-E -s`。明确哪些准备路径实测、哪些仅静态/模拟验证，不把当前环境能运行称为干净重建已通过。
2. 只允许一个 ComfyUI 服务、一个可见 GPU。验证 ready、停止与再次启动；无遗留 GPU 进程、意外外网监听、端口冲突和隐藏五 worker。验收末可保留唯一已验证服务供 Owner 使用，但需明确访问方式、PID与停止方式；其他探针和临时进程全部回收。
3. 必须真机产出最小合法单段 T2V 音视频；同参数重复至少一次，记录 prompt、seed、尺寸、帧数、步数、冷/热条件、端到端耗时、显存/主存峰值（缺测项明确列出）。有限数值/完成状态不代替正常可播放视频；检查视频帧与音轨解码，人工可见结果/实际浏览器证据及输出路径。
4. 继续验证同一 FL2VA 的 I2V/首尾帧路径，不引入 Ref2VA；若不能完成，明确失败路径及原因，不把未测项标通过。禁止黑帧、损坏媒体、只有文本编码就报闭环成功。
5. Director 浏览器实际加载、原生工作流导入、提交与结果访问/播放检查。页面能开不等于视频链路通过。仅原生API探针先通过也不能替代 Director 页面验收。
6. `python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py` 与 `python3 -m unittest -v`；修改 UI/worker 交互时遵守 AGENTS 对 fake 行为和浏览器检查的要求，不启动真实五 worker。
7. builder 后 fresh-context reviewer 只读复核最终候选；ponytail 最小性及代码准入，普通 finding 在开发 session 内有界修复并复核，不把可修复准备/启动缺口推回 Owner 重新规划。

## Decision / Next Steps

状态：approved / dispatch-authorized。本次 Owner 已授权继续，不再等待额外的规划确认。Fleet requests 当前 blocked；notify 仅证明接受通知，不能声称已经唤醒。禁止绕过通道限制经其他 CLI/API 注入任务；如仍需 Owner 在原 session 输入“继续”，主会话说明一次，不重新传递整包上下文。

当前 `29a6e16a` workflow 已 complete 且未交付，不伪装为仍在运行。开发 session 重新核对可执行 builder/reviewer capability 与原 workflow/child 生命周期，按 pi-subagents 同协议一个顶层 async workflow 完成续作、fresh review 和必要 fixes；基础设施故障 fail closed，不 CLI 降级。接管后是唯一产品 writer。主会话只读调研多卡，不安装/跑 GPU/改产品文件；调研结果先通过 notify 共享，不中途扩大单卡任务。

原 review 的普通缺口（不安全 `--install-deps`、双 OpenCV provider、误导 readiness、生命周期测试）仍属本轮有界修复，不因更换本地模型路径而遗忘或推回 Owner。不得为收敛记录重装已验证 Torch/CUDA。

浏览器已可用，Owner 仅授权本机项目验收临时 `--no-sandbox`，每条 CLI 显式带独立 session 与该参数；不访问外站/登录凭据、不改系统安全设置，测试后关闭。

停止条件：未经授权系统/精度/引擎变更、不可恢复内存/模型正确性硬阻塞、协议基础设施失败。可用原生配置及普通实现缺口由 round 内解决。真实视频生成较慢不是自动失败，但设置相称且有界的超时并记录状态，不无限重试。

交付：单实例可运行入口、环境准备与实际依赖记录、原生 workflow、音视频产物引用、真实页面证据、测试及独立 review、剩余风险。多卡方案由主会话独立检查源码、open/closed issue、维护者回复、合并修复和可复验案例；README 仅作线索，不作验收证据。
