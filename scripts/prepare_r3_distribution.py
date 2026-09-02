#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h3_studio.assets import validate_assets
from h3_studio.config import StudioConfig


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


def git_checkout(path: Path, repo: str, commit: str, tag: str | None = None) -> None:
    if path.exists():
        if not (path / ".git").exists():
            # A prior --skip-install asset check may have created only
            # ComfyUI/models/... under the ignored runtime root. Remove that
            # incomplete tree so the real pinned checkout can be cloned.
            shutil.rmtree(path)
            run(["git", "clone", "--filter=blob:none", repo, str(path)])
    else:
        run(["git", "clone", "--filter=blob:none", repo, str(path)])
    run(["git", "fetch", "--tags", "origin", commit], cwd=path)
    if tag:
        run(["git", "fetch", "--tags", "origin", tag], cwd=path)
    run(["git", "checkout", "--detach", commit], cwd=path)


def symlink_or_replace(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.symlink_to(src)


def copy_sidecars(src_root: Path, dst_root: Path) -> None:
    for child in src_root.iterdir():
        if child.name.endswith(".safetensors") or child.name.endswith(".bak") or child.name == ".cache":
            continue
        dst = dst_root / child.name
        if child.is_dir():
            if dst.exists() or dst.is_symlink():
                if dst.is_dir() and not dst.is_symlink():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            shutil.copytree(child, dst, ignore=shutil.ignore_patterns("*.safetensors", "*.bak"))
        elif child.is_file():
            shutil.copy2(child, dst)


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare the ignored R3 controlled ComfyUI distribution")
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--runtime-root", type=Path, default=None)
    ap.add_argument("--skip-install", action="store_true", help="only validate/link assets and write manifest")
    ap.add_argument("--compute-sha", action="store_true", help="verify full SHA-256 for external model assets")
    args = ap.parse_args()

    repo = args.repo.resolve()
    os.chdir(repo)
    cfg = StudioConfig.from_env(repo)
    runtime = (args.runtime_root or (repo / "var" / "runtimes" / "r3-single-worker-product")).resolve()
    comfy = runtime / "ComfyUI"
    venv = runtime / "venv"
    lock = cfg.runtime_lock
    model_root_value = os.environ.get(str(cfg.asset_manifest.get("asset_root_env", "H3_MODEL_ROOT")))
    if not model_root_value:
        raise RuntimeError("Set H3_MODEL_ROOT to the external MiniMax-H3 model root before preparing R3")
    model_root = Path(model_root_value).expanduser().resolve()

    asset_report = validate_assets(cfg.asset_manifest, compute_sha=args.compute_sha)
    if not asset_report["ok"]:
        print(json.dumps(asset_report, ensure_ascii=False, indent=2))
        return 2

    if args.skip_install:
        out = repo / "var" / "manifests" / "r3-distribution-asset-check.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"schema_version": 1, "asset_report": asset_report, "prepared": False}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"manifest": str(out), "asset_check": asset_report["ok"]}, ensure_ascii=False, indent=2))
        return 0

    runtime.mkdir(parents=True, exist_ok=True)
    git_checkout(comfy, lock["comfyui"]["repo"], lock["comfyui"]["commit"], lock["comfyui"].get("tag"))
    custom = comfy / "custom_nodes" / "ComfyUI_RH_MinMaxH3"
    node_lock = lock["custom_nodes"][0]
    git_checkout(custom, node_lock["repo"], node_lock["commit"])
    if not venv.exists():
        run([sys.executable, "-m", "venv", str(venv)])
    py = venv / "bin" / "python"
    constraints = repo / lock["python_stack"]["dependency_lock"]
    run([str(py), "-m", "pip", "install", "pip==26.2.1", "wheel==0.48.0", "setuptools==84.0.0"])
    run([str(py), "-m", "pip", "install", "-c", str(constraints), "torch==2.14.0+cu130", "torchvision==0.29.0+cu130", "torchaudio==2.11.0+cu130", "--index-url", "https://download.pytorch.org/whl/cu130"])
    run([str(py), "-m", "pip", "install", "-c", str(constraints), "-r", str(comfy / "requirements.txt")])
    run([str(py), "-m", "pip", "install", "-c", str(constraints), "-r", str(custom / "requirements.txt")])
    run([str(py), "-m", "pip", "install", "-c", str(constraints), "comfy-kitchen==0.2.31", "comfy-aimdo==0.4.15", "transformers==5.8.1", "accelerate==1.14.0", "av==18.1.0", "psutil==7.2.2", "Pillow==12.3.0"])

    # RH MiniMax-H3 resolves release sidecars under diffusers/MiniMax-H3, while
    # explicit flat component selections are discovered under models/MiniMax-H3.
    sidecar_model_root = comfy / "models" / "diffusers" / "MiniMax-H3"
    flat_model_root = comfy / "models" / "MiniMax-H3"
    sidecar_model_root.mkdir(parents=True, exist_ok=True)
    flat_model_root.mkdir(parents=True, exist_ok=True)
    for asset in cfg.asset_manifest["required_assets"]:
        rel = asset["relative_path"]
        src = model_root / rel
        if src.is_dir():
            copy_sidecars(src, sidecar_model_root / rel)
        elif src.is_file() and rel.endswith(".safetensors"):
            symlink_or_replace(src, flat_model_root / rel)

    manifest = {
        "schema_version": 1,
        "runtime_root": str(runtime),
        "comfy_root": str(comfy),
        "venv_python": str(venv / "bin" / "python"),
        "model_root_env": cfg.asset_manifest.get("asset_root_env", "H3_MODEL_ROOT"),
        "asset_report": asset_report,
        "prepared": True,
    }
    out = repo / "var" / "manifests" / "r3-distribution.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(out), "comfy": str(comfy), "python": str(venv / "bin" / "python")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
