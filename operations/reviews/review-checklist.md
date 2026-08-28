# Checkpoint Review Checklist

适用于 Baseline Reset、Runtime Decision、Single-Worker Product 和 Multi-Worker MVP。历史 R1 Review 仍保留原 round 语境，不由本清单改写。

## Metadata

- Checkpoint：
- Reviewer：
- Review class：`A` | `B` | `C`
- Review mode：`spawned_pi_process` | `same_session` | `human_review`
- Contract files：
- Change scope：
- Validation evidence：

## Contract Alignment

- [ ] 改动满足当前 checkpoint scope
- [ ] 未扩大 MVP 边界或复活旧 R2–R7 编排
- [ ] ComfyUI-first source of truth 未被削弱
- [ ] Replica Execution 与 Single-Request Multi-GPU 未混淆
- [ ] portability、Git ignore 和项目内运行数据规则未被破坏

## Correctness And Safety

- [ ] 关键路径或文档结论有证据
- [ ] 失败和边界条件被诚实记录
- [ ] 未引入任意代码、shell、import 或不受信任节点执行
- [ ] 未提交 secret、宿主机路径、权重、runtime、数据库、cache 或媒体
- [ ] Backend-only evidence 未被写成最终 MVP acceptance

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

通过条件：P0/P1 为零，P2 有明确 disposition，且验证证据完整。