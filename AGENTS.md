# AGENTS.md

给在这个仓库里工作的编码代理的说明。

## 读什么

1. `README.md` — 是什么、怎么跑
2. `docs/ARCHITECTURE.md` — 模块、Run 生命周期、网络
3. `docs/OPERATIONS.md` — 目标机器、并发上限、多卡路线
4. `config/*.json` — 所有可调参数都在这里，不在代码里

历史（R1–R4 的 review、work log、探针脚本）在 tag `v0.1-r4-mvp`，只在需要考古时看。

## 边界

- 不 fork ComfyUI，不写自己的画布 / 节点注册表 / DAG 执行器 / workflow 格式。Studio 只提交原生 ComfyUI API prompt。
- `h3_studio/` 只用标准库。
- 仓库里不出现宿主机 IP、绝对路径、权重、媒体、日志。机器相关配置走 `.env.local`。
- 不改系统驱动 / CUDA / 内核；需要时写进 OPERATIONS.md 让人来做。

## 改完必须做

```bash
python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py
python3 -m unittest -v
```

改了 UI 用 `python3 scripts/dev_fake_workers.py` 打开看一眼。改了和 worker 交互的逻辑，在 `tests/fake_comfy.py` 里补对应行为再写测试。

## 流程

小改动直接改、跑测试、提交。大改动（新的 worker 形态、换节点、换调度策略）先在 `docs/adr/` 写一页 ADR 再动手。不要新建"round"、"phase"、review 报告之类的流程文档。
