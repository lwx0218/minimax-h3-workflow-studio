#!/usr/bin/env python3
"""Prepare the ignored ComfyUI runtime (pinned checkout, venv, model links).

    H3_MODEL_ROOT=/path/to/MiniMax-H3 python3 scripts/prepare_runtime.py [--compute-sha] [--check-only]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h3_studio.assets import validate_assets  # noqa: E402
from h3_studio.config import StudioConfig, apply_project_local_env  # noqa: E402


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


def git_checkout(path: Path, repo: str, commit: str, tag: str | None = None) -> None:
    if not (path / ".git").exists():
        if path.exists():
            shutil.rmtree(path)
        run(["git", "clone", "--filter=blob:none", repo, str(path)])
    run(["git", "fetch", "--tags", "origin", commit], cwd=path)
    if tag:
        run(["git", "fetch", "--tags", "origin", tag], cwd=path)
    run(["git", "checkout", "--detach", commit], cwd=path)


def symlink_or_replace(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.symlink_to(src)


def copy_sidecars(src_root: Path, dst_root: Path) -> None:
    """Copy config/tokenizer/processor files but never weights."""
    dst_root.mkdir(parents=True, exist_ok=True)
    for child in src_root.iterdir():
        if child.name.endswith((".safetensors", ".bak")) or child.name == ".cache":
            continue
        dst = dst_root / child.name
        if child.is_dir():
            if dst.exists() or dst.is_symlink():
                shutil.rmtree(dst) if dst.is_dir() and not dst.is_symlink() else dst.unlink()
            shutil.copytree(child, dst, ignore=shutil.ignore_patterns("*.safetensors", "*.bak"))
        elif child.is_file():
            shutil.copy2(child, dst)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--check-only", action="store_true", help="only validate model assets")
    ap.add_argument("--compute-sha", action="store_true", help="verify full SHA-256 of model assets (slow)")
    args = ap.parse_args()

    repo = args.repo.resolve()
    os.chdir(repo)
    apply_project_local_env(repo)
    cfg = StudioConfig.from_env(repo)
    lock = cfg.runtime_lock
    model_root_value = os.environ.get(str(cfg.asset_manifest.get("asset_root_env", "H3_MODEL_ROOT")))
    if not model_root_value:
        raise SystemExit("Set H3_MODEL_ROOT to the external MiniMax-H3 model root")
    model_root = Path(model_root_value).expanduser().resolve()

    report = validate_assets(cfg.asset_manifest, compute_sha=args.compute_sha)
    if not report["ok"] or args.check_only:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 2

    runtime = cfg.runtime_root
    comfy = runtime / "ComfyUI"
    venv = runtime / "venv"
    runtime.mkdir(parents=True, exist_ok=True)
    git_checkout(comfy, lock["comfyui"]["repo"], lock["comfyui"]["commit"], lock["comfyui"].get("tag"))
    node_dirs = []
    for node in lock["custom_nodes"]:
        target = comfy / "custom_nodes" / node["name"]
        git_checkout(target, node["repo"], node["commit"])
        node_dirs.append(target)
    if not venv.exists():
        run([sys.executable, "-m", "venv", str(venv)])
    py = venv / "bin" / "python"
    constraints = repo / lock["python_stack"]["dependency_lock"]
    stack = lock["python_stack"]
    run([str(py), "-m", "pip", "install", "pip==26.2.1", "wheel==0.48.0", "setuptools==84.0.0"])
    run([str(py), "-m", "pip", "install", "-c", str(constraints), f"torch=={stack['torch']}", f"torchvision=={stack['torchvision']}", f"torchaudio=={stack['torchaudio']}", "--index-url", "https://download.pytorch.org/whl/cu130"])
    run([str(py), "-m", "pip", "install", "-c", str(constraints), "-r", str(comfy / "requirements.txt")])
    for node_dir in node_dirs:
        if (node_dir / "requirements.txt").exists():
            run([str(py), "-m", "pip", "install", "-c", str(constraints), "-r", str(node_dir / "requirements.txt")])
    run([str(py), "-m", "pip", "install", "-c", str(constraints), f"comfy-kitchen=={stack['comfy-kitchen']}", f"comfy-aimdo=={stack['comfy-aimdo']}", f"transformers=={stack['transformers']}", f"accelerate=={stack['accelerate']}", f"av=={stack['av']}", "psutil", "Pillow"])

    # RH MiniMax-H3 resolves release sidecars under diffusers/MiniMax-H3 and flat
    # weights under models/MiniMax-H3. Weights are symlinked, never copied.
    sidecar_root = comfy / "models" / "diffusers" / "MiniMax-H3"
    flat_root = comfy / "models" / "MiniMax-H3"
    for asset in cfg.asset_manifest["required_assets"]:
        rel = asset["relative_path"]
        src = model_root / rel
        if src.is_dir():
            copy_sidecars(src, sidecar_root / rel)
        elif src.is_file() and rel.endswith(".safetensors"):
            symlink_or_replace(src, flat_root / rel)

    manifest = {"runtime_root": str(runtime), "comfy_root": str(comfy), "venv_python": str(py), "asset_report": report}
    out = repo / "var" / "manifests" / "runtime.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(out), "comfy": str(comfy), "python": str(py)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
