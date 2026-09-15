# Director 本地模型单卡运行

## Metadata

- Project: minimax-h3-workflow
- Document type: guide
- Status: draft
- Owner: project owner
- Last updated: 2026-09-15
- Source of truth: operations/planning/2026-09-14-h3-director-single-gpu.md

## 已验证边界

原生ComfyUI固定提交 + Director `52f8fb7`、单可见A5000：320×320、39帧/24fps、9步、seed42、单段无Refine/LoRA，完成T2V同参数两次、I2V和首尾帧。四条均为可解码H264、1.625秒、立体声AAC，浏览器播放及真机stop→同端口restart通过；[单卡独立review](../operations/reviews/2026-09-15-h3-director-local-model.md)已approve_with_follow_up。LAN绑定增量另待复核。不是官方4–15秒参考质量或大尺寸验收，不承诺提速。

只用现有本地模型和sidecar，禁止任何模型资产下载。旧ModelScope下载`.part`与72字节尾部完全保留、不使用；本次授权没有恢复裁尾许可。

## 本机配置

机器路径只写ignored `.env.local`。脚本不自动解析shell文件，运行前手动source：

```bash
# H3_MODEL_ROOT 填现有 MiniMax-H3-INT8-CONVROT 目录
H3_NATIVE_FL2VA="$H3_MODEL_ROOT/MiniMax-H3-FL2VA-native-qkv-int8_convrot.safetensors"
H3_NATIVE_QWEN="$H3_MODEL_ROOT/qwen3-vl-32b-native-int8_convrot.safetensors"
H3_GPU=0
H3_DIRECTOR_HOST=127.0.0.1  # 默认回环；LAN仅在.env.local填获准的具体网卡IPv4
H3_DIRECTOR_PORT=30210
```

`H3_RUNTIME_ROOT`默认 `var/runtime`。推理固定项目 `.venv/bin/python -E -s`，要求 `include-system-site-packages=false`；不回退旧runtime venv、不注入外部site-packages。基础Python/stdlib可复用。HF Hub/Transformers/Datasets离线标志由启动器强制置1，原生tokenizer使用已存在本机文件，禁止隐式外取。

## 准备与运行

```bash
set -a; . ./.env.local; set +a
python3 scripts/prepare_runtime.py
python3 scripts/prepare_runtime.py --check-only
python3 scripts/start.py
```

准备默认不安装依赖。`--install-deps`及`--wheel-dir`都直接拒绝：当前97包记录是distribution metadata观察集合，不是带来源/哈希的可安装CUDA wheel锁。Torch metadata为2.11.0，模块build为2.11.0+cu130；vision/audio同样有差异，实际build另记在runtime-lock。**当前环境能运行不等于干净重建已通过。** 缺包应先核对兼容本地wheel/cache，必要时仅阿里源有界补缺，不重装已验证Torch/CUDA或混入dsbi包。

OpenCV已收敛为单一 `opencv-python==5.0.0.93`，满足 `scenedetect==0.7.1`。Director上游独立requirements推荐headless，但两provider共享cv2不能共装；本项目保留满足scenedetect且实际验证可解码/resize的一个provider。精确本轮wheel来源/hash在ignored证据，不代表完整环境已复建。

准备会在授权模型根生成独立副本（额外磁盘约67GB，不覆盖原件/已有目标，中断`.partial`不自动删除）：

- `scripts/convert_fl2va.py`：合法容器/长度检查后，仅把56头、128维的分组QKV重排成原生全Q/K/V，逐行scale同排。1039tensor/252quant保留；102个QKV相关tensor重排，其余完全相同。小型数值差0，全部tensor逐项核对通过。
- Qwen：仅把 `model.language_model.` / `model.visual.` 前缀变成原生前缀，350quant及全部payload保留。
- `scripts/convert_vae.py`：音视频归一化参数取自已有 `FL2VA/{audio,video}_vae/config.json`；音频legacy weight_g/v用同一个PyTorch weight_norm运算合成为weight，不换精度。视频其余权重不变。两个副本原生strict load所有key/shape匹配。

当前prepare检查包版本/模型路径并准备链接，`--check-only`不做重新推理，也不代表对任意旧副本完成数值校验。真实等价/数值证据只覆盖本轮指定源文件。

默认只有一个ComfyUI child，未配置 `H3_DIRECTOR_HOST` 时监听 `127.0.0.1`；可显式指定一个私网/回环IPv4（不接受URL、主机名、IPv6、通配或公网地址）。监听、占端口检查、readiness URL与CLI提示共用该地址；本机readiness请求不走环境代理。LAN只用于可信网络，ComfyUI无鉴权；不绑定所有网卡、不修改防火墙或代理配置。只白名单加载Director，不加载旧RH/多卡插件。readiness检查必需节点注册，不仅HTTP。额外参数仅允许 `--cpu-vae`、`--lowvram`、`--disable-dynamic-vram`；本轮使用原生默认动态显存管理及内部tiled VAE，未改引擎。

## 原生工作流与媒体

导入 `workflows/comfy-ui/director-single-t2v.json`，页面点击Run。I2V/首尾帧图分别为 `director-single-i2v.json`、`director-single-fl2v.json`，连接Director原生Group节点，需先准备 `director-first.png` / `director-last.png` 输入图片。本轮从T2V输出抽帧，存放 `var/inputs/director/`；未把图片入Git。替换图片用原生LoadImage。

本轮浏览器通过页面原生 `app.handleFile(File)` / `loadGraphData` 导入、真实Run按钮提交，并访问同源 `/view` 视频播放器，验证时间推进/解码帧与正常画面。CDP直接文件input导入曾返回alert，未声称该chooser路径通过，也没有使用后端POST prompt替代页面提交。普通浏览器文件导入仍需用户环境确认。

产物在 `var/outputs/director/video/`，日志 `var/logs/comfyui-director.log`。页面能开、history成功、文件存在都不能代替媒体帧数/时长/音轨解码；本轮四条均做了PyAV完整解码和实际浏览器播放。浏览器为静音播放验证，音轨验证为数值/解码，未做人耳听辨或音画语义同步评分。

## 停止与保留服务

停止/改绑定前先确认 `/queue` 的running/pending均空，并核对当前PID身份；不要盲用历史PID。前台Ctrl-C或给启动器PID发SIGTERM会终止child、等待退出并删除 `var/logs/comfyui-director.pid`。也可从项目根停止唯一child，启动器将随之退出并清理：

```bash
kill -TERM "$(cat var/logs/comfyui-director.pid)"
```

端口被占用时拒绝启动；不要并行启动旧Studio或第二个Director。旧入口仅显式 `--legacy-studio --workers worker-gpu0` 保留，当前隔离环境RH采样未回归，不能当本轮默认路线。

## 风险与证据

`operations/work_logs/2026-09-15-h3-director-local-model.md` 含真实参数/耗时/资源/输出/页面引用。冷场资源前33.4秒漏采，峰值为采样下界；RAM记service RSS，未测整机RAM峰值；耗时是后端完整prompt日志，不是浏览器点击到呈现的独立秒表。

torchcodec缺FFmpeg共享库未修；本轮实际PyAV/ffmpeg路径已通过，但其他功能不保证。Qwen历史析构ignored TypeError未修，不声称消除。没有系统、驱动、CUDA、模型精度变更，没有多卡或新Studio/调度器。
