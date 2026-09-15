# Director 单服务迁移

## Metadata

- Project: minimax-h3-workflow
- Document type: other
- Status: draft
- Owner: project owner
- Last updated: 2026-09-15
- Source of truth: operations/planning/2026-09-14-h3-director-single-gpu.md

## 当前决策（单卡续作）

Owner 已批准以一个原生 ComfyUI + 固定版本 Director、单可见 GPU 完成音视频闭环；不安装 buqi 或其他多卡插件。默认启动不再运行五 worker 或 Studio。准备与启动统一项目 `.venv`，保持当前 Torch/CUDA，不自动按旧漂移锁重装。只复用指定本地 FL2VA/Qwen/VAE/sidecar，禁止模型/tokenizer下载。独立格式副本：Qwen键名前缀；FL2VA从RH分组QKV到原生Q/K/V行重排、同步逐行scale并保留252quant；VAE从同目录sidecar合入归一化buffer，音频weight_norm使用相同PyTorch运算物化。先做小型等价检查，再真实单卡；原件和历史非法下载`.part`不改。允许原生CPU offload/内部tiled VAE，不修改推理数学。

本地短片T2V重复、I2V/首尾帧、浏览器播放和真实启停已实测，详见 `operations/work_logs/2026-09-15-h3-director-local-model.md`，独立review待完成。未可信复建前禁用安装入口，仅保留实装观察清单；不为收敛记录重装Torch/CUDA。

以下保留为历史决策，**不再是本次执行目标**。

## 历史决策

在隔离的 ignored runtime 中验证原生 ComfyUI、AIMixer Director 与 buqi 多卡节点。只允许一个 ComfyUI 服务；额外 GPU 进程只执行同一任务的推理，不启动独立画布或 Studio 调度。不 fork ComfyUI 或实现新的分布式引擎。

静态核对版本、量化与模型布局后，先做带显式超时的通信探针，再按单卡、两卡、四卡顺序重复同条件短视频测试。四卡必须证明端到端收益、正常音画和同任务参与，才切换默认入口。旧入口、配置和权重在此之前保持可用。通信、格式或内存硬阻塞即停止，不以部分通过替代交付。

## 约束与取舍

- Director 使用原生模型、CLIP（minimax）、视频和音频 VAE 输入；T2V/I2V/首尾帧使用 FL2VA，不默认引入 Ref2VA。
- buqi 的序列并行在每卡复制完整 DiT；56 个注意力头支持四卡，不支持五卡均分。其公开 Blackwell 测速不是本机 A5000 证据。
- 保留现有 Qwen INT8 ConvRot；键名前缀识别仅为必要条件，不能代替真实推理。旧 RH FL2VA 不靠改名冒充原生权重。
- 24 GiB 卡暂不启用同时驻留 DiT 和视频 VAE 的多卡解码。第五卡编码/解码仅在现成兼容路径实测后考虑。
- 服务与推理子进程仅使用隔离的项目 `.venv`；不继承 dsbi 第三方包或旧 runtime venv 回退钩子。基础 Python/标准库可复用，依赖仅保留项目兼容包或从可验证 wheel/阿里源安装，不混用 Torch/CUDA 栈，不改系统组件。
- 通信允许已测的进程级禁 IB/P2P 共享内存中转参数，仅放本机 ignored 配置；迁移后重验 collective 数值。通信通过不代表四卡视频收益。无收益或插件格式硬阻塞时不继续建设启动胶水、下载权重或扩充工作流。

## 状态

此 ADR 记录获批的验证方向，不表示迁移已通过。原失败记录保持历史；续作见 `operations/work_logs/2026-09-14-h3-director-migration-resume.md`。环境迁移与通信、文本编码通过，但现成 buqi 与原生版本/逐行 INT8 契约不兼容，视频迁移停止，未切换默认产品形态。
