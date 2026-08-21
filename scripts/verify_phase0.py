#!/usr/bin/env python3
"""Reproducible pre-commit verification for the Phase 0 governance baseline."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST_PATH_RE = re.compile(r"/(?:home|Users)/[^\s)`\"']+|[A-Z]:[\\/][^\s]+")
FORBIDDEN_STAGE_RE = re.compile(
    r"(^|/)(?:\.env\.local|var/(?:db|uploads|outputs|runs|cache|logs|tmp)/|"
    r"\.venv(?:-h3)?/)|\.(?:safetensors|ckpt|pt|pth|onnx|gguf|engine|"
    r"sqlite3?|db|mp4)$"
)
LEGACY_ROUND_RE = re.compile(r"^#{1,6} .*Phase 1[A-Z]|^\| R[1-7][A-Z] ", re.MULTILINE)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []

    diff_check = run("git", "diff", "--cached", "--check")
    require(diff_check.returncode == 0, f"git diff --cached --check: {diff_check.stdout}{diff_check.stderr}", errors)
    print(f"CHECK staged_diff_whitespace exit={diff_check.returncode}")

    names_proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(names_proc.returncode == 0, names_proc.stderr.decode(errors="replace"), errors)
    staged = sorted(
        item.decode() for item in names_proc.stdout.split(b"\0") if item
    )
    print(f"CHECK staged_candidate_list exit={names_proc.returncode} count={len(staged)}")
    print("STAGED_CANDIDATES_BEGIN")
    for name in staged:
        print(name)
    print("STAGED_CANDIDATES_END")

    for name in staged:
        if FORBIDDEN_STAGE_RE.search(name):
            errors.append(f"forbidden staged path: {name}")
            continue

        blob = run("git", "show", f":{name}")
        if blob.returncode != 0:
            errors.append(f"cannot read staged blob {name}: {blob.stderr}")
            continue
        text = blob.stdout
        if "\x00" in text:
            continue
        if HOST_PATH_RE.search(text):
            errors.append(f"host absolute path in staged content: {name}")
        if LEGACY_ROUND_RE.search(text):
            errors.append(f"actual legacy round structure in: {name}")
        for line_no, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                errors.append(f"trailing whitespace: {name}:{line_no}")
        if name.endswith(".md"):
            source = ROOT / name
            for target in MARKDOWN_LINK_RE.findall(text):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                relative = target.split("#", 1)[0]
                if relative and not (source.parent / relative).resolve().exists():
                    errors.append(f"missing markdown target: {name} -> {target}")

    print(f"CHECK staged_content_policy exit={0 if not errors else 1}")

    ignored_paths = [
        ".env.local",
        "var/outputs/example.mp4",
        "var/db/app.sqlite3",
        ".venv-h3/bin/python",
        "accidental.safetensors",
    ]
    for path in ignored_paths:
        ignored = run("git", "check-ignore", "--no-index", "--", path)
        require(ignored.returncode == 0, f"expected ignored path: {path}", errors)
        print(f"CHECK ignored:{path} exit={ignored.returncode}")

    env_local = ROOT / ".env.local"
    require(env_local.is_file(), "missing ignored .env.local", errors)
    model_path = ""
    if env_local.is_file():
        for line in env_local.read_text().splitlines():
            if line.startswith("H3_MODEL_PATH="):
                model_path = line.split("=", 1)[1]
                break
    require(bool(model_path), "H3_MODEL_PATH missing from .env.local", errors)
    if model_path:
        require((Path(model_path) / "model_index.json").is_file(), "snapshot root missing model_index.json", errors)
    print(f"CHECK local_model_snapshot exit={0 if model_path and (Path(model_path) / 'model_index.json').is_file() else 1}")

    gpu = run(
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,driver_version",
        "--format=csv,noheader",
    )
    require(gpu.returncode == 0, f"nvidia-smi failed: {gpu.stderr}", errors)
    gpu_lines = [line for line in gpu.stdout.splitlines() if line.strip()]
    require(len(gpu_lines) == 5, f"expected 5 GPUs, got {len(gpu_lines)}", errors)
    require(all("RTX A5000" in line for line in gpu_lines), "not all GPUs are RTX A5000", errors)
    print(f"CHECK gpu_baseline exit={gpu.returncode} count={len(gpu_lines)}")
    for line in gpu_lines:
        print(f"GPU {line}")

    if errors:
        print("RESULT FAIL")
        for error in errors:
            print(f"ERROR {error}")
        print("COMMAND_EXIT=1")
        return 1

    print("RESULT PASS")
    print("COMMAND_EXIT=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
