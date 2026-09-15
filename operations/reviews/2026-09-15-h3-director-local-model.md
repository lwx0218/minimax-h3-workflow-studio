# 本地模型单卡 Director 交付复核

## Metadata

- Project: minimax-h3-workflow
- Task: h3-director-local-model
- Timestamp (UTC): 2026-09-15T03:59:53Z
- Owner: project owner
- Route: review-only
- Source of truth: operations/planning/2026-09-14-h3-director-single-gpu.md

## Decision / Findings

Fresh 项目 reviewer：**`approve_with_follow_up`**。未发现 P0/P1 阻塞；独立 **ponytail 代码准入通过**。父 session 接受当前指定本机模型、单GPU短片范围的交付，不启动额外修复循环。

唯一 **P2 非阻塞后续项**：`tests/test_start.py:129–134` 的 QKV 回归只检查小型字节排列，scaled-INT8 数值检查目前只保留结果记录，未固化可运行源码。后续在现有转换测试增加一个使用非均匀逐行scale的CPU线性输出等价用例，防止未来遗漏scale排列。不需要GPU、大模型或新框架。当前实现、RH/native源码、全量转换核对与真实生成共同支持正确性，未发现现有转换错误。

## Acceptance Evidence

- 仅使用指定本地FL2VA/Qwen/两VAE和已有sidecar；独立转换副本，原件SHA匹配。1039个FL2VA tensor逐个核对，102个权重/scale同步排列，252份quant保持；Qwen前缀转换保留payload；VAE相同weight_norm及sidecar归一化，原生strict keys/shapes匹配。旧失败 `.part` 未使用、未裁尾；本次无模型/tokenizer下载。
- prepare/start统一隔离 `.venv`；不可信安装分支已fail closed；单一OpenCV provider通过实际cv2/scenedetect检查；原Torch/CUDA集合保持。默认一个回环ComfyUI、单可见GPU、Director白名单，旧Studio必须显式选择。
- 节点级readiness、占端口/提前退出/超时/缺节点测试，以及真实stop→PID消失/端口关闭→同端口restart通过。
- 四条真实页面提交产物：T2V两次、I2V、首尾帧。均完整解码39帧320×320、1.625秒，H264和双声道AAC，非黑有运动、音轨finite非零；浏览器同源播放器推进通过，reviewer独立查看四组首中尾帧。
- 页面原生 `app.handleFile(File)` 导入和点击Run通过；直接CDP文件input路径曾alert，普通文件chooser未宣称通过。浏览器静音播放，未做人耳听辨或语义同步评分。

| 路径 | 后端完整prompt日志耗时 | 进程RSS采样峰GiB | GPU0采样峰MiB |
| --- | ---: | ---: | ---: |
| T2V进程冷场 | 75.23s | ≥63.26 | ≥23833 |
| 同参数同进程重复 | 99.07s | 63.53 | 23853 |
| I2V | 102.52s | 65.06 | 23805 |
| 首尾帧 | 102.72s | 65.13 | 23859 |

共同参数：seed42、320×320、39帧/24fps、9步、cfg1、res_multistep/simple，无Refine/LoRA。冷场不是磁盘冷缓存，前33.4秒资源漏采，峰是下界；其他约2秒采样。未测整机RAM峰和浏览器点击到呈现独立秒表，未宣称重复提速。

## Parent Final Checks

- 父 session 重跑py_compile：exit0；unittest：25 tests / 24.506s / OK。日志 `var/h3-director-local-20260915/parent-unittest.txt`。
- `git diff --check`通过，无暂存/提交/push。父复算审前完整16文件候选SHA256：`cd356634209690edb608f768f93f43160c5b8b85a12b7138b446a0640db64b90`；候选快照不覆写，审后仅新增本文。
- 父查看首条T2V解码帧和首尾帧浏览器截图，正常黄鸟与绿叶画面；核实launcher/child父子关系及仅回环30210监听。当前保留唯一已验服务，专用测试浏览器已关闭。
- reviewer严格只读，未重跑命令、独立重算大权重或展开超长单行容器记录；结论结合源码、原始日志、转换与媒体证据，不声称无限范围模型认证。

## Deliverables / Service

16文件候选清单在 `var/h3-director-local-20260915/candidate-manifest.json`：准备/启动及两个转换脚本、两个依赖记录、三个测试文件、README/ADR/运行说明、三份原生workflow及本次work log。既有治理、主会话Plan和旧失败记录保留原归属。

视频：`var/outputs/director/video/Director_single_t2v_00001_.mp4`、`Director_single_t2v_00002_.mp4`、`Director_single_i2v_00001_.mp4`、`Director_single_fl2v_00001_.mp4`。

服务仅本机回环，端口30210；访问及停止操作见 [运行说明](../../docs/director-single-gpu.md)。本机PID与准确URL通过会话交付，ignored `final-processes.txt` 留证；不把历史PID当永久身份。

## Artifact References / Residual Risks

- Workflow：`0e7b259d-c405-4fdf-8110-d26d80751f83`。
- Builder：`3a9c62f3-49ce-4e46-9a0c-887560949f3a`；fresh reviewer：`7e099419-6581-4434-bbba-2a0a3ddf166e`。
- Runtime绑定输出：`local-model-single/builder.md`、`local-model-single/reviewer.md`，两者均已实际读取完整内容；准确宿主路径见workflow receipt/Fleet交接。
- 全部本机原始证据：`var/h3-director-local-20260915/`；[执行记录](../work_logs/2026-09-15-h3-director-local-model.md)。
- 未干净复建，metadata观察清单不能唯一指定CUDA wheel，安装分支保持禁用；不覆盖大尺寸、长片、多卡、Refine/LoRA或旧RH路线。
- torchcodec共享库与Qwen历史析构TypeError未修；本次真实PyAV/ffmpeg链路通过不代表所有功能兼容。完整模型许可证未重新独立取得，不分发权重。
- 当前交付不改写旧失败历史，不恢复任何模型下载或被拒绝的裁尾授权。
