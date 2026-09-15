# Director 本地模型单卡闭环实测

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-local-model-single-gpu
- Timestamp (UTC): 2026-09-15T03:49:23Z
- Owner: project owner
- Route: direct-execute
- Source of truth: operations/planning/2026-09-14-h3-director-single-gpu.md

## Goal / Summary

遵循本地模型修订Plan（SHA256 `c8f2e138b67d42565e1d16c0bd257a26e4db836dfc8952cce467ae9afadd1026`），HEAD保持 `389e550f97b57d320e088f50b74d2ed36d19818d`。完成一个原生ComfyUI+固定Director、一个可见A5000上的T2V重复、I2V、首尾帧及页面播放、真实停止/重启。**builder实测通过，独立review待完成，不宣布代码已准入。**

没有模型/tokenizer下载，没有buqi/多卡插件，没有改Torch/CUDA/系统/驱动/精度或推理数学。此前非法下载`.part`完全保留，不裁尾、不修header、不使用，拒绝的授权没有被绕过。原失败work log/review保留。

## Scope / Changes

- prepare/start使用项目`.venv`，不注入dsbi第三方包；原生默认单child、单数字GPU、固定回环、Director白名单，强制HF Hub/Transformers/Datasets离线。旧Studio须显式选择。
- 禁用不可信`--install-deps`/`--wheel-dir`，观察清单不再可作为安装锁执行。保留97包metadata观察及另列的实际cu130模块build，不重装Torch/CUDA。
- OpenCV收敛一个provider：保留满足scenedetect0.7.1的opencv-python5.0.0.93，移除headless并从先缓存到本地的同版wheel无依赖重装恢复共享文件。pip check、cv2解码39帧/resize、scenedetect调用通过。Director上游headless建议与scenedetect的opencv依赖不能同时共装，本机选用已验证的普通provider。
- `convert_fl2va.py`：当前RH源码分组QKV→原生split布局，56头/128维的weight与per-row scale同步重排；1039tensor/252quant保留，102个tensor重排，其余逐tensor完全相同。先CPU小型scaled-INT8线性等价（差0），再转换/全量核对/真实推理；不只是重命名。
- Qwen只变更原生键名前缀，350quant及payload保留。原生既有本机tokenizer与指定sidecar的vocab相同，merges仅版本注释差别；MiniMax特殊token补齐后全词表/中英文/图像标记编码等价，检查使用local_files_only。无隐式外取。
- `convert_vae.py`：从本地sidecar合入latent mean/std；audio weight_g/v用同一个PyTorch weight_norm运算物化FP32 weight，小型数值检查差0；视频其余权重不变。两个独立副本原生strict load所有keys/shapes匹配。
- 所有四个源权重SHA与原asset manifest一致（`original-hashes.json`），原件未改。衍生文件仅授权模型根，路径只`.env.local`/ignored证据。
- readiness检查必需节点，不仅`/system_stats`；测试等待实际ready行，再查PID退出/端口关闭并同端口重启，覆盖占端口、提前退出、超时、缺Director节点。fake_comfy补`/object_info`行为；不启动真实五worker。
- 三份原生UI图、最小ADR/README/运行说明更新；无自造画布/调度/引擎。

## Validation

全部大日志/机器路径/截图放ignored `var/h3-director-local-20260915/`。以下4条均实际从浏览器页面Run提交，未使用后端POST prompt代替。prompt/原生图快照和所有history/queue原文保留。

公共参数：320×320、39帧、24fps、9步、res_multistep/simple、cfg1、seed42，单段无Refine/LoRA。默认原生动态显存管理，VAE内部tiled。T2V prompt为：

> A small yellow bird sings on a leafy branch in a sunlit garden. The bird turns its head gently. Natural daylight, realistic colors. Audio: clear bird chirps and soft rustling leaves. No text or watermark.

I2V/首尾帧使用同一FL2VA、同seed/尺寸/帧数/步数；输入为首次T2V抽出的首帧/中间帧，不下载图片。Group prompt为黄鸟歌唱和转头，Director额外添加原生首帧/首尾帧保持提示词，实际完整文本在history。

| 路径 | 后端prompt总耗时 | history执行→success | service RSS峰GiB | GPU0峰MiB | 输出文件（`var/outputs/director/video/`） |
|---|---:|---:|---:|---:|---|
| T2V进程冷场 | 75.23s | 72.023s | ≥63.26 | ≥23833 | `Director_single_t2v_00001_.mp4` |
| 同参数同进程重复 | 99.07s | 95.731s | 63.53 | 23853 | `Director_single_t2v_00002_.mp4` |
| I2V | 102.52s | 99.285s | 65.06 | 23805 | `Director_single_i2v_00001_.mp4` |
| 首尾帧 | 102.72s | 99.344s | 65.13 | 23859 | `Director_single_fl2v_00001_.mp4` |

冷场为成功服务重启后的首条，**不是磁盘冷缓存**（转换/核验已读过文件）；第二条未重启，参数一致，但native cache-none/模型卸载仍存在，不据此承诺热场加速。耗时来自后端`Prompt executed in`，包括本轮prompt处理/清理；不是浏览器点击到屏幕呈现的独立秒表。资源约2秒采样，冷场前33.4秒漏采，冷场峰仅下界；其余也为采样峰，不是瞬时硬峰。RAM为service RSS，未测整机used RAM峰。GPU1–4采样均1MiB，无其他compute进程，未用第五卡。

### 媒体/页面

- 四条完整PyAV解码均39帧、320×320、1.625s H264；AAC时长1.625s、双声道、52224个解码样本（含codec padding），finite且非静音。
- T2V两次audio RMS均0.01557，I2V0.03685，首尾帧0.02451；各视频RGB std约55–62、相邻帧差非零，不是黑帧/单帧零秒文件。未以history成功或文件存在判通过。
- 首/中/尾抽帧已目视为正常黄鸟/树叶画面；首尾帧与输入有VAE/有损编码差异，不承诺逐像素硬锁。
- 原生页面导入使用浏览器内`app.loadGraphData`/`app.handleFile(File)`，后者走完整原生FileReader解析；真实点击Run。CDP直接input文件上传曾alert，未称该chooser路径通过，也未改上游导入器。此方式限制保留。
- 同源`/view`播放器四条实际play成功，记录paused=false、时长/尺寸、currentTime推进和decodedFrames；截图有正常画面。浏览器播放设置muted以避免自动播放限制；音频为解码/数值验收，未做人耳听辨/语义同步评分。
- 页面资源origin记录仅本机；专用session `h3-director-local-model`，每条CLI显式`--args '--no-sandbox'`，无外站/登录/系统安全变更，最后close。

媒体/页面证据：`media-validation.json`、`*-frames.png`、`cold-browser-playback.png/json`、`t2v_00002_-playback.png`、`i2v_00001_-playback.png`、`fl2v-playback.png`及对应play-start/end JSON；`i2v-import.png`、`fl2v-import.png`、`final-director.png`、`final-director-snapshot.txt`。

### 命令与回归

| 命令/检查 | 结果与边界 |
|---|---|
| `.venv/bin/python -E -s scripts/convert_fl2va.py <local-source> <independent-target>` | 本地容器合法；全量1039tensor等价检查通过；不触碰旧`.part` |
| `.venv/bin/python -E -s scripts/convert_vae.py <source> <local-config> <target>` | 音视频副本strict native keys/shapes通过；CPU weight_norm等价 |
| `python3 scripts/prepare_runtime.py`（source本机env后） | 实际准备通过，`prepare-native-vaes.txt` |
| `python3 scripts/prepare_runtime.py --check-only` | 最终通过，非完整干净重建 |
| `python3 scripts/start.py --wait-ready 180` | 两次成功就绪；最后真实stop→同端口restart通过 |
| `python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py` | 最终exit0 |
| `python3 -m unittest -v` | 最终25 tests / 24.188s / OK；含临时真实venv+fake HTTP，不把fake当真机 |
| `.venv/bin/python -E -s -m pip check` | 通过；另做单OpenCV实际cv2/scenedetect检查，不把pip check当ABI证明 |
| `git diff --check` / `git diff --cached --name-only` | 无空白错误，无暂存文件 |

### 有界失败及修复（未覆盖为成功）

1. 首次页面Run发现原始VAE不含native所需权重/buffer：立即interrupt/stop，没有收为通过。独立等价VAE转换及strict检查后重启再跑成功。
2. 初次I2V导入的timeline仍存t2v，Director正常拒绝带首帧的t2v；从页面切换i2v、导出正确图，单次重试通过。原失败日志/history保留。
3. 初始CDP文件input导入alert及一次CLI不支持的find/select用法保留；改用页面原生完整File处理及支持的select命令，无后端提交替代。

## Service / Cleanup

最后真实停止已证实旧child PID消失、端口关闭、PIDfile删除，stop时GPU compute-app为空（`real-stop-check.txt`）。同端口重启后仅留唯一已验服务：

- URL：`http://127.0.0.1:30210/`
- 本次child PID：`130422`；launcher PID：`130417`（事件型记录，后续重启以PIDfile为准）。
- 停止：项目根 `kill -TERM 130417`，或对 `var/logs/comfyui-director.pid` 中的child发SIGTERM；启动器随child退出并清理。
- `final-processes.txt`、`final-listeners.txt`、`final-gpu.txt`证明loopback单端口、单可见GPU。所有临时探针/监测和browser已退出，没有真实五worker或额外GPU服务。

## Decision / Next Steps

本次本地小片闭环已实测，交fresh reviewer复核，未自动commit/push。完整候选 `var/h3-director-local-20260915/candidate.diff` 含新代码/测试/workflow/docs，排除治理、主会话Plan/review及旧失败work logs；旧失败文件保持原样。

剩余边界：完整环境干净复建未测且安装分支禁用；普通文件chooser导入未通过本轮CDP测试；冷场资源漏采/整机RAM峰和浏览器端到端秒表缺测；音轨未做人耳听辨；仅短小单段/本例输入，没有大尺寸、长片、Refine/LoRA/多卡验收。torchcodec缺FFmpeg共享库未修，但本轮实际PyAV/ffmpeg媒体路径通过；其他路径不保证。Qwen历史析构ignored TypeError未修，未冒称消除。完整许可证条款未重新独立取得，权重未分发。
