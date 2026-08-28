# R1 Independent Review Prompt

这是 R1 MiniMax-H3 本地真实 T2VA feasibility 的独立只读审阅合同。

Reviewer 必须读取：

- `AGENTS.md`
- `Harness_manual.md`
- `README.md`
- `docs/project-intake/minimax-h3-workflow.md`
- `docs/specs/mvp-v0.md`
- `docs/architecture/architecture-v0.md`
- `docs/development/process.md`
- `operations/planning/initialization-plan.md`
- `operations/planning/r1-h3-feasibility-matrix.md`
- `operations/reviews/review-checklist.md`
- `operations/reviews/2026-08-21-r1-feasibility-report.md`
- `operations/reviews/2026-08-21-r1-independent-review-1.md`
- `operations/reviews/2026-08-21-r1-verification.md`
- `operations/reviews/r1-verification-output.txt`
- `operations/reviews/r1-dependency-lock-1.txt`
- `operations/reviews/r1-dependency-lock-2.txt`
- `operations/reviews/r1-attempt-manifest.json`
- `operations/work_logs/2026-08-21-r1-h3-feasibility.md`
- `scripts/run_r1_h3_attempt.py`
- `scripts/verify_r1.py`

可按需读取 ignored runtime evidence：

- `var/outputs/r1-feasibility/A1/metadata.json`
- `var/outputs/r1-feasibility/A2/metadata.json`
- `var/outputs/r1-feasibility/B1/metadata.json`
- `var/outputs/r1-feasibility/B2/metadata.json`
- `var/outputs/r1-feasibility/B2/server.log`
- `var/outputs/r1-feasibility/C1/metadata.json`
- `var/outputs/r1-feasibility/C1/status.ndjson`
- `var/outputs/r1-feasibility/C2-lock1-preflight/metadata.json`
- `var/outputs/r1-feasibility/C2/metadata.json`
- `var/outputs/r1-feasibility/C2/status.ndjson`
- `var/outputs/r1-feasibility/C2/server.log`
- `var/logs/r1-feasibility/dor.txt`

审阅目标：

1. 是否严格限制在 R1，未开发 backend/frontend 或引入 forbidden branches
2. 两组 dependency lock、三个 profile、每 profile generation attempts、总 attempts、时间、主存和磁盘预算是否符合 matrix
3. 每个 execution 的配置、结果和资源数字是否与 evidence 自洽
4. C2 是否必须因 terminal `failed`、content/ffprobe/checksum 缺失而不能算 valid probe
5. `blocked` Stop Decision 是否诚实且 bounded，是否需要 Owner 选择
6. runner/verifier 是否存在会使 evidence 或 safety conclusion 不可信的缺陷
7. portability、Git ignore、无权重/secret/runtime media 入库边界是否保持
8. 第一次 spawned review 的 P1-1 至 P1-4 和 P2 disposition 是否已由 B2、runner、manifest、verifier、report 修复
9. 是否存在 P0/P1/P2 finding

特别要求：

- 不得把 SGLang 日志中的“generated successfully”替代 API `completed/succeeded` 和独立 ffprobe gate
- 核对 C2 corrected rerun 是否确实会超出 Profile C 两次 generation attempt
- 核对 B2 未执行是否有合理 disposition，而不是隐藏可用的矩阵内 retry
- Reviewer 只读，不修改任何文件

只输出 Markdown review report。报告必须包含：

- `Review mode=spawned_pi_process`
- files reviewed
- evidence checked
- P0/P1/P2 findings（每项有证据）
- required changes
- decision：`pass` | `changes_required` | `blocked`

这里的 `blocked` decision 可以在 P0/P1=0 时成立，表示实验结论需要 Owner control-gate decision；它不是 acceptance pass。
