# Work Log：禁用 harness-flow

## Metadata

- Project: MiniMax H3 Studio
- Task: disable project-local harness-flow extension
- Timestamp (UTC): 2026-08-31T00:00:00Z
- Owner: project Owner
- Route: direct-execute
- Source of truth: Owner explicit request / `AGENTS.md`

## Goal

Owner 明确要求本项目不再使用 `harness-flow`，将其 disable。

## Scope / Changes

本任务只修改 project-local Pi capability layer 中的 `harness-flow` 入口，不修改业务代码、测试、数据或 runtime config。

变更：

- `.pi/extensions/harness-flow/index.ts` → `.pi/extensions/harness-flow/index.ts.disabled`
- 新增 `.pi/extensions/harness-flow/README.md`，说明禁用原因和恢复条件。

Pi 会自动发现 `.pi/extensions/*/index.ts` 或 `index.js`；改名后 `harness-flow` 不再匹配 project-local extension discovery 入口。源码仍保留，未删除。

## Validation

已执行：

```bash
find .pi/extensions/harness-flow -maxdepth 1 -type f -printf '%f\n' | sort
find .pi/extensions/harness-flow -maxdepth 1 -type f \( -name 'index.ts' -o -name 'index.js' \)
pi list
node -e "JSON.parse(require('fs').readFileSync('.pi/settings.json','utf8')); console.log('PASS')"
git check-ignore -v .pi/npm/node_modules/pi-subagents/package.json .pi/npm/node_modules/pi-fleet/package.json .pi/npm/node_modules/pi-wechat-assistant/package.json .pi/npm/node_modules/pi-web-access/package.json
git diff --check
git diff --exit-code -- scripts var inputs outputs .env.example .env.local
for p in src tests data; do if [ -e "$p" ]; then git diff --exit-code -- "$p"; git status --short -- "$p"; else echo "$p: absent"; fi; done
```

结果：

- `harness-flow` 目录下仅有 `README.md` 和 `index.ts.disabled`；无可自动加载的 `index.ts` / `index.js`。
- `pi list` 仍显示四个已安装 project packages。
- `.pi/settings.json` JSON parse PASS。
- `.pi/npm/node_modules/**` 仍被 `.pi/npm/.gitignore` 忽略。
- `git diff --check` PASS。
- `scripts var inputs outputs .env.example .env.local` 无 diff。
- `src`、`tests`、`data` 当前不存在。

## Next

当前 session 已禁用文件入口，但已加载的 extension runtime 可能要到 `/reload` 或新 session 后才消失。后续不要再使用 harness-flow handoff/review gate；如需重新启用，必须由 Owner 明确授权单独治理维护任务。
