# Work Log：Phase 0 项目初始化

- Date：2026-08-20
- Route：`spec-then-plan`
- Scope：需求基线、架构、计划、Git 与运行数据边界
- Business code：未创建

## 完成内容

- 使用 `grilling` 逐项确认 MVP 用户、能力和非目标
- 补全项目 intake
- 新建 MVP spec 和架构 v0
- 新建 Phase 0–3 初始化计划
- 将 README 从 starter 说明更新为项目说明
- 创建 `.gitignore` 和 `.env.example`
- 创建未提交的 `.env.local`，引用现有模型 snapshot root
- 建立 `var/` 项目内运行数据约定和本地目录
- 初始化 `main` 分支 Git 仓库
- 移除仅属于上游 starter、在本项目中不可用的 `scripts/bootstrap.sh`

## 已确认产品决策

- 长期可产品化，MVP 为单机单用户
- 首个技术里程碑为真实本地 T2VA
- 独立 workflow schema，不兼容 ComfyUI contract
- MVP 支持 T2VA + FL2VA
- Raw Prompt + 本地 Prompt Builder
- 基础 DAG 编辑闭环
- SGLang 先做限界可行性测试
- MVP 仅内置节点
- SQLite + 项目内文件系统
- loopback + SSH tunnel
- H3 单并发 FIFO
- 完整运行快照，大数据按阈值压缩
- 后端与 H3 runtime 使用两个项目内虚拟环境

## 验证

完整可复验证据见 `operations/reviews/phase-0-verification.md`。

已执行：

```bash
git status --short --branch
git check-ignore -v --no-index .env.local var/outputs/example.mp4 var/db/app.sqlite3 .venv-h3/bin/python accidental.safetensors
nvidia-smi --query-gpu=index,name,memory.total,memory.free,driver_version --format=csv,noheader
nvidia-smi topo -m
```

并执行 Python repository scan，检查候选文本中的宿主机绝对路径、尾随空格和 Markdown 相对链接。

关键结果：

- Git 仓库已初始化，当前分支为 `main`
- `.env.local`、虚拟环境、`var/` 产物和模型权重模式均命中 ignore 规则
- 可提交候选文件中未发现宿主机绝对路径
- Markdown 本地链接均存在，文本无尾随空格
- `.env.local` 指向的 snapshot root 存在 repository-level `model_index.json`
- `nvidia-smi` 检出 5×RTX A5000、每张 24564 MiB、driver `580.173.02`

## 未验证

- 尚未安装项目专用 SGLang 环境
- 尚未启动 H3 服务
- 尚未提交真实 T2VA 请求
- 尚未创建 workflow/backend/frontend contracts 或业务代码

## Governance Hardening

在 Owner 确认后补充：

- 将后续开发固定为 R1–R7，不再使用 Phase 1A/B/C
- 定义 Builder、Automated Verifier、Independent Reviewer 和 Owner 职责
- 增加 Definition of Ready、Definition of Done 和 Review severity
- 增加项目驾驭、compact、session 新建与恢复说明
- 选择 `spawned_pi_process` 作为目标 Review mode；独立只读 Pi 已成功运行，capability check 通过
- 首次独立 Review 产出 3 项 P1：commit 状态循环、R1 边界不足、验证证据不足
- 在同一 Phase 0 内完成两轮修复和三次独立 Review；最终 Review `pass`，P0/P1 为零
- 规定 Review/Fix 留在原 round，不由 Owner 逐条 prompt 驱动

## Review Result

- 首次 Review：3 项 P1，`changes_required`
- 第二次 Review：P1-01/P1-02 关闭，P1-03 仍需可复验命令和完整清单
- 最终 Review：P0=0、P1=0、`pass`
- P2-01（阶段性状态文字）已在 closeout 刷新

## 下一步

将 Phase 0 Ledger 准备为 accepted candidate，重跑最终 staged verification，创建 baseline commit 并执行 post-commit check。随后新建干净 session，进入 R1 本地真实 T2VA 可行性验证。
