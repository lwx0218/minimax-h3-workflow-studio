# H3 Director 单卡续作：模型容器硬阻塞，未交付

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-single-gpu
- Timestamp (UTC): 2026-09-15T01:52:00Z
- Owner: project owner
- Route: direct-execute
- Source of truth: operations/planning/2026-09-14-h3-director-single-gpu.md

## Goal / Summary

按已批准单卡目标续作，无新 Fleet/子 agent。Plan SHA256 为 `53d5e58b95afa6fdda17e1776b336b5b132927ec4bf6b8bf773ed15b20e63631`，HEAD 保持 `389e550f97b57d320e088f50b74d2ed36d19818d`。

**未完成音视频闭环，不建议准入。** ModelScope 原生剪枝 INT8 FL2VA 下载成功且 SHA 完全匹配上游，但存在 72 字节非 tensor 尾部，原生 safetensors 拒绝。父 session 允许一次只读诊断后，Owner 控制门未授权独立副本裁尾修复，遂停止；未裁尾、未改 header/offset、未创建修复模型、未换来源/精度/模型绕过。此次拒绝仅针对该修复，不推断项目永久取消。

## Scope / Changes

- `scripts/start.py`：沿用前候选的 `.venv` / `-E -s` 隔离移除 fallback；新增默认单 Director、单数字 GPU、固定回环、端口占用拒绝、有限 readiness、Ctrl-C/SIGTERM child 清理。旧 Studio 需 `--legacy-studio` 显式选择，默认不误起五 worker。
- `scripts/prepare_runtime.py`：准备与启动同 `.venv`；固定 ComfyUI/Director，默认不装依赖；核对当前记录集合与 pip check；独立 Qwen header 前缀转换，保留全部 tensor 字节及原件；链接模型，不覆盖已有链接目标。旧 RH preparation 已被原生路线替代，旧源码和权重未删。
- `config/runtime-lock.json` / `requirements-lock.txt`：固定 Director `52f8fb7b8d8eb6bebf33ebb534827efa8f95484c`，记录当前98包传递集合，非干净复建证明。
- `tests/test_start.py`：隔离环境、prepare→默认 start→stop（真实临时 venv + HTTP child，mock git、假模型，无GPU）、Qwen payload/量化保留与不覆盖测试。
- 原生 UI workflow `workflows/comfy-ui/director-single-t2v.json`：固定 seed42、256×256、39帧/24fps、9步、单段、无Refine/LoRA；派生固定 Director 示例，**未实际执行**。
- README、最小ADR与 `docs/director-single-gpu.md` 清楚标识候选/停止/旧能力历史范围，未修改 Harness managed 分区或 AGENTS。

未安装 buqi 或任何多卡插件，未启动 Studio/真实worker，未更改 Torch/CUDA/驱动/系统/基础 Python、未改 dsbi/global。机器路径仅 `.env.local` 和 ignored 证据，模型保留于授权外部模型根。历史失败记录未覆盖。

## Validation

完整本机证据：ignored `var/h3-director-single-20260914/`（目录沿任务日期命名，实际本次执行UTC为09-15）。

| 验证 | 结果/边界 | 证据 |
|---|---|---|
| `agent-browser --session h3-director-single --args '--no-sandbox' doctor --offline --quick` | 7 pass，CLI0.33.2可用；未打开产品页 | 本轮工具输出 |
| 单文件 ModelScope 直连 `curl --noproxy '*' --max-time 1800 --retry 0` | 7m47s，20970379688 bytes，无代理无重试 | `download.txt`, `model-headers.txt`, `model-readme.txt` |
| 原生 FL2VA SHA256 | `f07a54277ca85b59e5243a924fb5c54d79768f820fc4155c1b614b6f613e9dbf`，匹配既有上游真实列表；磁盘可用约1.4TiB | `model-sha256.txt`、旧 `modelscope-files.json` |
| `safetensors.safe_open` 原生FL2VA | **失败：incomplete metadata, file not fully covered** | 运行输出、`fl2va-format-diagnosis.json` |
| 一次只读格式诊断 | 932 tensor，全部 dtype×shape 字节长度正确、offset从0连续无gap/overlap；200个I8各有quant；额外72字节不属于tensor/quant | `fl2va-format-diagnosis.json` |
| 额外尾部 | 换行 + `L2P_bypass_MiniMax_H3_FL2VA_pruned_int8_convrot.safetensors_1785751234` + 换行；非遗漏的quant。合法tensor末端20970379616 | 同上，含hex/尾部SHA；原件`.part`保留 |
| 许可证 | 仓库README声明MiniMax H3 Community License；ModelScope官方LICENSE路径404，未独立取得完整条款 | `model-readme.txt`；未分发权重 |
| Qwen转换容器验证 | 原件/新件safe_open都通过；完整payload SHA相同，350 quant保留；没有本轮文本/实际workflow推理 | `qwen-container-verification.json`, `qwen-convert.txt` |
| 实际 prepare | pip check与98包版本核对通过；随后因不合法模型仅保留`.part`、没有合法目标文件而失败。不得当prepare成功 | `prepare.txt` |
| `python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py` | exit0 | `py-compile.txt` |
| `python3 -m unittest -v` | 最后20 tests / 17.863s / OK | `unittest-final.txt` |
| `.venv/bin/python -E -s -m pip check` | 通过，但不代表ABI/覆盖文件/媒体路径正确 | `pip-check-final.txt` |
| T2V冷/暖同条件重复、I2V/首尾帧 | **全部未测**；无端到端/RAM/VRAM峰值，无生成媒体/解码帧数/时长/音轨 | 不适用 |
| Director浏览器导入/提交/播放、真机ready→stop→restart | **全部未测**，没有截图/snapshot或API替代页面的通过声明 | 不适用 |
| 清理/服务状态 | 下载进程已结束；GPU compute-app为空；30210–30215及8188无监听；专用browser已close；无可交付URL/PID | `cleanup-final.txt` |

### 依赖验证边界与遗留风险

初次 `scenedetect==0.6.7.1 --no-deps` 暴露缺platformdirs/Click版本冲突；同轮改为0.7.1，阿里源安装platformdirs及其opencv-python依赖后pip check通过。保留两次install报告，不覆盖失败。最终 `opencv-python==5.0.0.93` 与原有 `opencv-python-headless==4.10.0.84` 同占cv2，导入实际5.0.0；这是尚未解决的依赖文件覆盖风险，未做干净重建。停止控制门后不再安装/卸载处理。日志 `install*.txt` / `install*-report.json`。

Torch distribution metadata是2.11.0，但module build是2.11.0+cu130；vision/audio类似。当前文本锁只记录metadata，不能据此保证从阿里源取得相同CUDA构建。`--install-deps` 仅候选、未实测，不得用于无人值守复建；不会把当前环境能运行称为干净重建。

`environment-final.json` 记录隔离sys.path、关键库位置、PyAV共享库版本、项目imageio-ffmpeg路径。只出现允许的dsbi基础Python/stdlib路径，没有dsbi第三方site-packages。torchcodec缺FFmpeg共享库仍未解决；仅静态判断Director主要媒体路径用PyAV/ffmpeg，不声明完整链路不需要它。Qwen历史析构ignored TypeError保留。

## Decision / Next Steps

保持停止，当前是 **partial candidate / not delivered**，待fresh reviewer只读复核。普通准备/依赖缺口与没有真实媒体证据均不隐瞒。本次拒绝的容器修复不可被后续自动fix绕过。无commit/push/reset/clean/stash，无暂存文件。

全候选快照 `var/h3-director-single-20260914/candidate.diff` 包含产品改动和新文件；排除预存AGENTS/README Harness分区、`.pi/`、manual/intake/zip等无关基线、旧planning/review/work logs。模型/媒体/日志不入Git。
