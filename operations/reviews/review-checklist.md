# Round Review Checklist

每个 R1–R7 在 acceptance commit 前必须完成本清单，并生成独立 review artifact。

## Metadata

- Round：
- Reviewer：
- Review mode：`spawned_pi_process` | `same_session`
- Contract files：
- Change scope：
- Validation evidence：

## Contract Alignment

- [ ] 改动满足当前 round scope
- [ ] 未扩大 MVP 边界
- [ ] 与 `docs/specs/mvp-v0.md` 一致
- [ ] 与 `docs/architecture/architecture-v0.md` 一致
- [ ] portability 与项目内运行数据规则未被破坏

## Correctness

- [ ] 关键路径行为正确
- [ ] 错误和边界条件有处理
- [ ] 状态转换合法且可恢复
- [ ] 数据和 artifact 索引一致
- [ ] 未发现明显并发、取消或重复执行问题

## Security And Safety

- [ ] 未引入任意代码、shell 或 import 执行
- [ ] 路径无法逃逸项目运行目录
- [ ] Secret 和宿主机路径未进入提交
- [ ] 模型、数据库、缓存和媒体未进入 Git
- [ ] 服务暴露边界符合 loopback 默认策略

## Verification

- [ ] 自动测试覆盖当前 round acceptance
- [ ] 修复后重新运行相关回归
- [ ] 真实模型测试与 Mock 测试没有混淆
- [ ] 失败、跳过和环境限制被明确记录

## Maintainability

- [ ] Contract 和实现边界清楚
- [ ] 没有不必要的抽象或兼容层
- [ ] 新增依赖有明确理由
- [ ] 文档与实际命令一致

## Findings

### P0

- None / findings

### P1

- None / findings

### P2

- None / findings and disposition

## Decision

- [ ] `pass`
- [ ] `changes_required`
- [ ] `blocked`

通过条件：P0/P1 为零，P2 均有明确 disposition，验证证据完整。
