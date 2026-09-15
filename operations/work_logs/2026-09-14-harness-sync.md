# Harness 治理下发记录

## Metadata

- Project: minimax-h3-workflow
- Task: 下发当前 Harness 治理模板并迁移旧流程条款
- Timestamp (UTC): 2026-09-14T03:26:29Z
- Owner: 项目 Owner
- Route: direct-execute
- Source of truth: AGENTS.md；Owner 本次聊天授权

## 目标与授权

Owner 要求下发 Harness，并明确冲突时以 Harness_Workspace 为准。模板来源为 Harness_Workspace 提交 `5f86b18`。本次只迁移治理文件，不执行产品开发流程。

## 改动

- 通过 `harness.sh` 下发 `.pi/` 能力文件、交付清单、手册、文档规范及 evidence 目录骨架。
- `AGENTS.md` 建立 managed / project-owned 分区；旧流程条款改为遵循 managed 分区。
- 保留项目产品、安全、测试规则，以及重大架构变更先写 ADR 的要求。
- 保留 README 原文，仅追加 Harness 入口；已有 `.pi/` 内容和项目 ZIP 文件不变。
- 四个必需 package 已声明；未安装依赖、启动工作流、提交或推送。

## 验证

- 首次 apply 后再次预览：`OK no changes`。
- 对下发前 12269 个文件进行指纹对照：仅获批的 `AGENTS.md` 和 `README.md` 改变。
- project-owned 分区与原合同对照：仅授权的流程段替换，其余保留。
- `python3 -m py_compile h3_studio/*.py scripts/*.py tests/*.py`：通过。
- `python3 -m unittest -v`：17 项通过。
- `git diff --check`：通过。

## 结论与边界

治理文件下发完成；未验证 Pi package 的安装或运行时可用性。原文件备份与同步 manifest 保存在仓库外临时目录。此次记录占用 work_logs 后，由同步工具回收其先前交付的空目录占位文件。不自动提交或推送，业务代码与配置未改动。
