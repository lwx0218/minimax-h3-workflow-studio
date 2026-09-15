# H3 Director 续作：环境与文本编码通过，现成多卡契约阻塞

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-migration-resume
- Timestamp (UTC): 2026-09-14T11:24:19Z
- Owner: project owner
- Route: direct-execute
- Source of truth: operations/planning/2026-09-14-h3-director-migration.md

## Goal / Summary

Owner 明确继续后，在原唯一 round 内恢复已结束的 builder；不是原失败 workflow 一直在运行。完整重读修订 Plan，SHA256 为 `1112124c91c8a31d45db0cb766b631a9f74a73e758a6e2f3de75ef7103c311ff`。原失败日志、review 和主会话通信诊断保留不改。

**未交付 Director 多卡视频。** 隔离环境迁移、通信数值断言、Qwen 原生真实文本编码通过；当前上游 buqi 与锁定 ComfyUI API 及目标逐行 INT8 分片契约不兼容。父 session 允许一次有界上游兼容版检查，当前 HEAD 与缓存相同，未找到现成修复，按回复停止，不改推理引擎或换模型精度。

## Scope / Changes

### 环境及最小代码

- ignored `.venv-h3` 重命名为 `.venv`，保留有效依赖；修复 bin 文本 shebang、激活脚本、提示符及 pyvenv.cfg 的旧路径。入口原件备份于本轮 ignored 证据目录。最终无旧名称残留，python/pip/activate 检查通过，两种名称均已被现有 Git ignore 覆盖。
- `include-system-site-packages=false`；基础 Python 及标准库仍可来自原 conda 环境，但 sys.path、关键模块路径及已加载模块断言确认没有 dsbi 第三方包。原有两个 `.pth` 仅为环境内部 cutlass 路径及 setuptools hook，不注入 dsbi。
- 原 ignored `var/runtime/venv` 不删除；其原先指向项目环境的包链接仅重定向到迁移后路径，不用于新启动。没有向 `.venv` 复制或链接 dsbi 已安装目录。
- `scripts/start.py` 选择唯一项目 `.venv`，删除启用 system-site-packages 与链接 fallback 包的全部钩子；worker Python 加 `-E -s` 防止 PYTHONPATH/用户包注入。它仍是原 worker 池入口，**不是已完成的新 Director 启动器**，未启动任何 worker 池。
- 新增 `tests/test_start.py`，用假 main 子进程验证忽略 PYTHONPATH 和 user-site，保留 GPU 参数。未修改 Studio UI、worker HTTP 交互或 workflow。
- ADR 仅更新严格环境隔离、已测通信参数作用域及续作阻塞状态。

### 依赖

原项目 pip check 已通过，但缺少 ComfyUI 包，av 16.1.0 不满足原生要求。查找本机 wheel 无适合的缺失 Comfy 包后，仅用阿里 PyPI 源并约束原 Torch/CUDA 集合安装。首次 240 秒总截止在模板媒体下载期间超时（exit124）；同源缓存续试，900 秒截止内 exit0。没有换源、系统安装或修改 dsbi。

最终 pip check 通过。原 Torch 2.11.0+cu130、torchvision 0.26.0+cu130、torchaudio 2.11.0+cu130、Triton 3.6.0、NCCL 2.28.9 与原 CUDA 库均未替换；原有包唯一升级是 av 16.1.0 → 18.1.0，另外新增 25 个包，完整 diff 与阿里下载报告在 ignored 证据目录。

GPU 矩阵乘、torchvision NMS、torchaudio resample smoke 通过；Qwen 推理实际执行原生 INT8 ConvRot。可选 torchcodec 0.11.1 import 因缺 FFmpeg 共享库失败，未改系统补库，**不把整个预装扩展集合宣称为全部兼容**。Comfy/Director 视频导出尚未验证。

`config/requirements-lock.txt` 与 `runtime-lock.json` 的旧栈漂移仍存在：本轮停止于插件契约，未把部分 smoke 通过改写成完整产品锁已验收；实装前后 freeze、安装报告、模块及库路径已保留供后续选择可复验集合。旧 prepare_runtime 路径尚未迁移收敛，不应按旧锁重装。旧 RH 路线文件/权重/环境保留，但调整入口后的真实 RH 采样未复验。

## Validation

### 通信复验

只对探针子进程设置修订 Plan 的五项通信变量；未写系统配置或产品默认参数。复用主会话 probe.py，新 label 避免覆盖历史。20 秒进程组超时、55 秒父截止、3 秒 kill 宽限及 wait 回收。

| 测试 | 结果 | 墙钟 |
|---|---|---:|
| 迁移后四卡，`resumed-venv-four-gpu` | 四 rank exit0 | 5.348 s |
| 安装后两卡，`resumed-final-two-gpu` | 两 rank exit0 | 3.828 s |
| 安装后四卡，`resumed-final-four-gpu` | 四 rank exit0 | 5.357 s |

每组均验证 Gloo 对象广播和 NCCL all-reduce/all-gather/all-to-all-single/broadcast，每尺寸重复三次逐元素断言。只是 SHM 中转通信，不是视频加速比。未另采整机 RAM/每卡总显存峰值；原始 rank 日志有 Torch allocated 指标，不能替代整卡 VRAM。

复验命令（解释器变量为本机 `.venv/bin/python`）：

```bash
python3 -B var/h3-nccl-diagnostic-20260914/probe.py \
  --python "$H3_DIAGNOSTIC_PYTHON" --label resumed-final-four-gpu \
  --mode eager --world 4 --p2p-disable --ib-disable
```

该 label 已使用；再次运行需新 label。

### Qwen 真实推理

保留原 `qwen3-vl-32b-int8_convrot.safetensors`，仅内存归一化 `model.language_model.` → `model.`、`model.visual.` → `visual.`；原件未改，也未写派生权重。原生 detect 从误认 8B 变为 32B，全部 350 个 comfy_quant 仍为 INT8 ConvRot（groupsize256），逐行 scale 保留。

原生 `load_text_encoder_state_dicts` + `CLIPType.MINIMAX`，同一 prompt 连续两次实际 `encode_from_tokens_scheduled`：输出 `[1,9,5120]`，finite 断言通过，均含 minimax_token_tags，平均绝对值相同。第一次 9.111 s，第二次 1.140 s，总计约 10.954 s（不含全部进程启动），进程最大 RSS 27,868,840 KiB；未采整卡 VRAM。这是文本条件编码成功，不是图像条件/视频正确性验证。退出0，但解释器析构时出现上游 ModelPatcher unpin 的 ignored TypeError，原始日志保留，不隐去。

### 多卡硬阻塞

1. 原生 ComfyUI `169fcf35a2fc163fec31338b816503ddac0d3fcf`（v0.34.2），buqi `bce083929c135bdabd41679da3ddf6f409336ed3`。完整导入 `sp_forward.py:30–40` 即 `ImportError: cannot import name 'time_shift_slope'`。buqi 源码写着按 ComfyUI0.30.0的 model.py 实现；README 的 >=0.30.0 不等于任意新版本 API 兼容。
2. ModelScope 列表与 Range header 直连核实实际文件为根目录 `MiniMax_H3_FL2VA_pruned_int8_convrot.safetensors`，20,970,379,688 bytes。先猜测 Director 风格小写目录 URL 返回404，随后以 API 实际文件名成功，不把404错报成模型不存在。目标 `blocks.0.attn.qkv_proj.weight` 为 I8 `[21504,5376]`，scale F32 `[21504,1]`，含 comfy_quant。仅读取 header，未下载完整权重；ProxyHandler 显式禁代理。
3. buqi `sp_forward.py:87–116` 的 `head_sharded_qkv` 在 QuantizedTensor 分支仅切 `_qdata` 并更新 orig_shape，保留原 `_params.scale`。`use_allgather` / `attn_allgather` 在两/四卡启用此路径。
4. 为避开独立导入错误，probe 从未改上游 AST 提取该函数，用原生 comfy.ops 创建逐行 INT8 ConvRot QuantizedTensor。输入 `[768,256]`，scale `[768,1]`；两卡所有 rank 权重切为384行、四卡所有 rank 切为192行，但 scale 仍768行。契约断言明确失败；没有擅自补分片或改变量化数学。
5. 父 session 允许一次有界检查当前上游/明确兼容版。`git ls-remote ... HEAD` 返回仍为上述同一提交，未发现当前现成修复。即使退到其明确参考的0.30.0解决导入，当前逐行 scale 分片问题独立存在，因此没有为此重建另一个 ComfyUI。此结论仅限核对版本及目标格式，不声称所有插件版本永久不可用。

### 产品验收与回归

| 项目 | 结果 |
|---|---|
| 单卡短视频基线、重复、T2V/I2V首尾帧音画 | 前置契约阻塞，未执行 |
| 两卡/四卡同 task 视频、端到端收益、阶段时间 | 未执行，无收益证据 |
| 第五卡编码/解码 | 未接入 |
| Director 浏览器/服务启停 | 未部署，未测，无新访问入口 |
| 编译 | `python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py` exit0 |
| 回归 | `python3 -m unittest -v`，18 tests，15.289 s，OK |
| 环境命令 | `.venv/bin/pip --version`、activate、`scripts/start.py --help` 通过；不等于真实服务启动 |
| 清理 | 本轮探针 PID 已回收，GPU compute apps 为空，各卡回到1 MiB；未启动 ComfyUI 或新增外网监听 |

## Evidence / Decision

本轮证据根 `var/h3-director-resume-20260914/`（ignored）：

- `migration.txt`、`migration-checks-final.txt`、`activate-final.txt`、`venv-bin-before/`：环境移动、原入口备份、最终入口检查。
- `isolation-final.json`、`core-smoke.txt`、`extensions-smoke.txt`：实际模块/库来源、通过及失败的扩展 smoke。
- `pip-check-before.txt`、`pip-check-after.txt`、`freeze-before.txt`、`freeze-after.txt`、`dependency-diff.json`、`install*.txt`、`install-report.json`：依赖与下载证据。
- `qwen_probe.py`、`qwen-probe.txt`：无磁盘转换的真实文本编码；`sp_int8_contract.py`、`sp-int8-contract.txt`、`sp-int8-isolated-contract.txt`、`upstream-contract.txt`：原模块导入失败与隔离原函数契约失败。
- `modelscope-files.json`、`fl2va-native-header.json`、`modelscope-contract-native.txt`、`buqi-upstream-head.txt`：来源与版本核实。
- `py-compile.txt`、`unittest.txt`、`cleanup.txt`、`candidate.diff`、`review-summary.json`：最终回归、清理和只读候选；候选包含原轮 ADR/失败 work log 与本次全部产品改动，排除治理、Plan、主会话诊断及 reviewer 文档。
- 三次通信日志仍在 `var/h3-nccl-diagnostic-20260914/resumed-*/`，按各自 label 可读。

停止迁移，建议 fresh reviewer `return_to_planning`；本记录不代替 reviewer 或 ponytail gate。是否转其他现成插件、精度或另做上游修复属于后续授权，不在此续作擅自推进。

Ponytail 自查：删除旧回退胶水，多于新增启动逻辑；只加一个可运行隔离测试。没有新引擎、插件数学补丁、调度平台或未经验证的使用说明；硬阻塞前仅下载模型 header，避免无用20GiB下载。
