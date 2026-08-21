# Phase 0 Independent Review Prompt

这是 Phase 0 baseline 的独立只读审阅合同。

Reviewer 必须读取：

- `AGENTS.md`
- `README.md`
- `Harness_manual.md`
- `docs/project-intake/minimax-h3-workflow.md`
- `docs/specs/mvp-v0.md`
- `docs/architecture/architecture-v0.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/reviews/review-checklist.md`

审阅目标：

1. Goal、Spec、Architecture、Plan 是否一致
2. R1–R7 是否 bounded，是否仍存在字母阶段膨胀风险
3. Builder/Verifier/Reviewer/Owner 职责是否可执行
4. Definition of Done 和最终收线是否可验证
5. Compact/session handoff 是否符合 Pi 实际行为
6. portability、Git ignore、项目内运行数据和模型外置边界是否一致
7. 是否存在 P0/P1/P2 finding

Reviewer 只输出 Markdown review report，不修改文件。报告必须包含：review mode、files reviewed、findings、required changes、decision。
