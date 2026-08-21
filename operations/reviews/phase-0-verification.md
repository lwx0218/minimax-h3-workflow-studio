# Phase 0 Automated Verification Evidence

- Scope：Phase 0 governance baseline
- Result：pre-commit automated verification `pass`；final independent review `pass`；baseline commit pending
- Runtime artifacts：不提交

## Git And Ignore

执行：

```bash
git status --short --branch
git check-ignore -v --no-index \
  .env.local \
  var/outputs/example.mp4 \
  var/db/app.sqlite3 \
  .venv-h3/bin/python \
  accidental.safetensors
```

关键结果：

- repository branch：`main`
- `.env.local` 命中 `.env.*`
- `var/outputs` 与 `var/db` 命中 `/var/*`
- `.venv-h3` 命中虚拟环境规则
- `*.safetensors` 命中模型权重规则

已执行：

```bash
git add .
git diff --cached --check
git status --short --ignored
```

结果：

- 初次 staged candidate 检查通过；最终权威清单由 `scripts/verify_phase0.py` 在保存输出中生成
- `git diff --cached --check` 通过
- staged candidates 不包含 `.env.local`、`var/` runtime files、虚拟环境、模型、数据库或 MP4
- ignored status 明确显示 `.env.local`

## Reproducible Staged-Candidate Verification

可执行检查脚本：`scripts/verify_phase0.py`。

执行：

```bash
git add .
python3 scripts/verify_phase0.py > operations/reviews/phase-0-verification-output.txt
echo $?
git add operations/reviews/phase-0-verification-output.txt
```

脚本直接读取 Git index 中的 blobs，并检查：

- `git diff --cached --check`
- 完整 staged candidate 文件清单
- 禁止的 runtime/model/media 路径
- staged content 中的宿主机绝对路径
- 尾随空格
- Markdown 相对链接
- 实际 legacy/字母 round 结构
- `.env.local`、`var/`、虚拟环境和模型模式的 ignore 命中
- ignored `.env.local` 指向的 snapshot root
- 5×RTX A5000 与 driver 基线

完整输出和每项退出状态保存于 `operations/reviews/phase-0-verification-output.txt`。成功标准是结尾同时出现：

```text
RESULT PASS
COMMAND_EXIT=0
```

## Local Model Snapshot

执行等价检查：

```bash
model_path=$(grep '^H3_MODEL_PATH=' .env.local | cut -d= -f2-)
test -f "$model_path/model_index.json"
```

结果：通过。`.env.local` 指向的 snapshot root 含 repository-level `model_index.json`。

精确宿主机路径只存在于 ignored `.env.local`，不写入提交证据。

## GPU Baseline

执行：

```bash
nvidia-smi --query-gpu=index,name,memory.total,memory.free,driver_version --format=csv,noheader
nvidia-smi topo -m
```

关键结果：

- 5 × NVIDIA RTX A5000
- 每张总显存 24564 MiB
- 检查时每张空闲显存约 24112 MiB
- driver `580.173.02`
- topology 显示 PIX/NODE，未显示 NVLink

## Independent Reviewer Capability

执行新的只读 Pi print process：

```bash
pi -p --no-session --approve --tools read,grep,find,ls --thinking high <phase-0-review-prompt>
```

结果：

- 独立进程成功启动
- stderr 为空
- 成功读取合同并产出 `operations/reviews/2026-08-20-phase-0-baseline-review.md`
- capability decision：`spawned_pi_process` 可用
- 首次 review decision：`changes_required`，3 项 P1，正在同一 Phase 0 内修复

## Pre-Commit Verification Result

P1 修复后已完成：

1. 可执行 staged-candidate verification script：pass
2. 完整 staged candidate 清单与逐项退出状态：见保存输出
3. ignore、model snapshot、GPU 基线复验：pass
4. 固定 round 结构检查：pass
5. R1 bounded matrix 存在且包含 profile/attempt/time/resource/stop limits

Independent Review 状态：

- 首次 review：`changes_required`
- 第二次 review：`changes_required`，仅 P1-03 未关闭
- 最终 review：`pass`，P0/P1 为零

仍待：

1. 准备 Ledger accepted candidate
2. 将 final review 加入 staged candidates 后重跑 verification script
3. baseline commit 与 post-commit check
