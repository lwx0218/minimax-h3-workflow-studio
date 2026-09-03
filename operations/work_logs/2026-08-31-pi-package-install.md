# Work Log：项目本地 Pi Packages 安装

## Metadata

- Project: MiniMax H3 Studio
- Task: install project-local Pi packages
- Timestamp (UTC): 2026-08-31T00:00:00Z
- Owner: project Owner
- Route: direct-execute
- Source of truth: `AGENTS.md`

## Goal

Owner 明确要求为本项目安装以下 Pi packages：

- `pi-subagents`
- `pi-fleet`
- `pi-wechat-assistant`
- `pi-web-access`

本任务是项目本地 capability layer 维护，不改变产品 R2/R3/R4 交付范围，不修改业务代码、测试、数据或 runtime config。

## Source And Versions

安装前通过 `npm view` 检查 npm metadata，并固定当前版本：

| Package | Version | Description |
|---|---:|---|
| `pi-subagents` | `0.61.0` | Pi extension for single-agent delegation and scripted multi-agent workflows |
| `pi-fleet` | `0.2.0` | Cross-device orchestration and direct remote execution for pi over Tailscale |
| `pi-wechat-assistant` | `0.3.0` | 微信作为 pi TUI 的移动端分身 |
| `pi-web-access` | `0.27.0` | Web search、URL fetching、GitHub/PDF/YouTube/local video access |

Pi packages/extension 会以当前用户权限运行代码；本次安装基于 Owner 明确授权。

## Changes

执行 project-local 安装：

```bash
pi install -l --approve npm:pi-subagents@0.61.0
pi install -l --approve npm:pi-fleet@0.2.0
pi install -l --approve npm:pi-wechat-assistant@0.3.0
pi install -l --approve npm:pi-web-access@0.27.0
```

安装结果：

- `.pi/settings.json` 新增 `packages` 列表；
- `.pi/npm/.gitignore` 由安装器生成，用于避免 `.pi/npm/node_modules` 等安装产物进入 Git；
- `.pi/npm/node_modules/**` 已被 `.pi/npm/.gitignore` 忽略。

## Validation

已执行：

```bash
pi list
node -e "读取四个 package.json 并打印 name/version/pi/dependencies"
```

结果：

- `pi list` 显示四个 project packages 已安装；
- 四个 package manifest 均包含 `pi` 资源声明；
- npm install audit 均为 `found 0 vulnerabilities`；
- package versions 已固定在 `.pi/settings.json`。

后续完成总体验证时还需运行：

```bash
git diff --check
git status --short
git check-ignore -v .pi/npm/node_modules/pi-subagents/package.json .pi/npm/node_modules/pi-fleet/package.json .pi/npm/node_modules/pi-wechat-assistant/package.json .pi/npm/node_modules/pi-web-access/package.json
```

## Notes

当前 session 已安装 package，但新 extension/tool/command 通常需要 `/reload` 或新 session 才会加载。不要把 package 安装视为启用 formal workflow；`.pi/` 仍是 capability layer，不是 policy authority。
