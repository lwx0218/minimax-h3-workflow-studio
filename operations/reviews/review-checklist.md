# Checkpoint Review Checklist

适用于 Baseline Reset、Runtime Decision、Single-Worker Product 和 Multi-Worker MVP。历史 R1 Review 仍保留原 round 语境，不由本清单改写。

## Metadata

- Checkpoint：
- Reviewer：
- Review class：`A` | `B` | `C`
- Review mode：`spawned_pi_process` | `same_session` | `human_review`
- Contract files：
- Candidate scope（可给 P0/P1/P2 的当前验收变更）：
- Context scope（只读合同/Plan/spec/source/tests/baseline；不自动成为 candidate）：
- Environment / dirty-worktree scope（dirty/untracked/pre-existing/tool residue；只记录透明度和污染风险）：
- Validation evidence：

## Contract Alignment

- [ ] 改动满足当前 checkpoint / task 的 candidate scope
- [ ] 进入 review bundle 的 context 未被误当作 candidate scope
- [ ] Git changed/untracked paths 未被自动纳入当前产品 Round / task 验收范围
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
- [ ] `.pi/` / harness / extensions / skills / prompts / settings 问题未被当成产品 candidate P1 自动修复
- [ ] 非当前任务问题已分类为当前产品阻塞、review evidence limitation、governance maintenance issue 或非当前 task / Round backlog

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

通过条件：candidate scope 内 P0/P1 为零，P2 有明确 disposition，验证证据完整；context scope 和 environment / dirty-worktree scope 只可产生限制、治理维护或 backlog 分类，除非它们直接阻断当前必要门禁。
