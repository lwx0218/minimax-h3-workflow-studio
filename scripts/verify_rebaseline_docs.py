#!/usr/bin/env python3
"""Validate the documentation-only ComfyUI-first baseline reset."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NORMATIVE = [
    "README.md",
    "AGENTS.md",
    "Harness_manual.md",
    "CONTEXT.md",
    "docs/adr/0001-use-comfyui-as-studio-foundation.md",
    "docs/project-intake/minimax-h3-workflow.md",
    "docs/specs/mvp-v0.md",
    "docs/architecture/architecture-v0.md",
    "docs/development/process.md",
    "operations/planning/rebaseline-plan-v1.md",
    "operations/planning/orchestration-v1.md",
    "operations/planning/initialization-plan.md",
    "operations/reviews/review-checklist.md",
    "operations/handoffs/pi-rebaseline-handoff.md",
]
REQUIRED = {
    "CONTEXT.md": ["ComfyUI Foundation", "Replica Execution", "Single-Request Multi-GPU", "Functional MVP"],
    "operations/planning/rebaseline-plan-v1.md": ["Baseline Reset", "Runtime Decision", "Single-Worker Product", "Multi-Worker MVP"],
    "operations/planning/initialization-plan.md": ["`accepted`", "accepted / feasible_with_constraints", "Runtime Decision", "SUPERSEDED"],
    "docs/specs/mvp-v0.md": ["Guided Mode", "Advanced Canvas", "supporting engineering evidence"],
    "docs/architecture/architecture-v0.md": ["authoritative graph", "Replica Execution", "Single-Request Multi-GPU"],
}
# These are positive legacy instructions, not mentions in a non-goal or historical record.
FORBIDDEN_ACTIVE = [
    "采用独立的 workflow contract、节点接口和运行时",
    "ComfyUI 仅作产品形态参考",
    "ComfyUI 仅作为产品和架构参考",
    "独立版本化 DAG contract",
    "当前 MVP 固定为 R1–R7",
    "MVP 在 Phase 0 后固定为 R1–R7",
    "只有实测需要时才评估 ComfyUI backend",
]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def main() -> int:
    failures: list[str] = []
    documents: dict[str, str] = {}
    for relative in NORMATIVE:
        path = ROOT / relative
        if not path.is_file():
            fail(f"missing normative file: {relative}", failures)
            continue
        documents[relative] = path.read_text(encoding="utf-8")

    for relative, needles in REQUIRED.items():
        text = documents.get(relative, "")
        for needle in needles:
            if needle not in text:
                fail(f"{relative}: missing required anchor {needle!r}", failures)

    all_markdown = sorted(ROOT.rglob("*.md"))
    for path in all_markdown:
        relative = path.relative_to(ROOT).as_posix()
        historical = (
            relative.startswith("operations/reviews/") or
            relative.startswith("operations/work_logs/") or
            relative.startswith("operations/planning/r1-")
        )
        if historical or relative.startswith(".pi/skills/"):
            continue
        text = path.read_text(encoding="utf-8")
        for legacy in FORBIDDEN_ACTIVE:
            if legacy in text:
                fail(f"{relative}: stale active legacy clause {legacy!r}", failures)

    for relative, text in documents.items():
        for target in LINK_RE.findall(text):
            target = target.strip().split()[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_path = target.split("#", 1)[0]
            resolved = (ROOT / relative).parent / target_path
            if not resolved.exists():
                fail(f"{relative}: broken repository link {target!r}", failures)

    plan = documents.get("operations/planning/rebaseline-plan-v1.md", "")
    for anchor in ("Plan approval: approved", "Accepted-effective Rounds: R1", "| R1 | R1-baseline-reset |", "| R2 | R2-runtime-decision |", "| R3 | R3-single-worker-product |", "| R4 | R4-multi-worker-mvp |", "## R2 — Runtime Decision"):
        if anchor not in plan:
            fail(f"rebaseline plan is missing fixed-handoff anchor {anchor!r}", failures)
    if "R2-R7" not in plan or "Single-Request Multi-GPU" not in plan:
        fail("rebaseline plan is missing legacy disposition or Track X", failures)
    if not ("backend-API generation is supporting evidence only" in plan or "Backend CLI/API probes remain required engineering evidence" in plan):
        fail("rebaseline plan does not distinguish backend evidence from MVP acceptance", failures)

    if failures:
        print("rebaseline documentation verification: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"rebaseline documentation verification: PASS ({len(documents)} normative files, links and anchors checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
