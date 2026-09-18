#!/usr/bin/env python3
"""Prepare pinned native ComfyUI + Director using the isolated project .venv.

Model paths come from the sourced .env.local. No package installation by default.
--install-deps is disabled: observed versions do not identify CUDA wheels.
A populated environment is not evidence of a clean rebuild.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from h3_studio.config import StudioConfig, apply_project_local_env


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, timeout=1800)


def project_python(repo: Path) -> Path:
    py = repo / ".venv/bin/python"
    cfg = repo / ".venv/pyvenv.cfg"
    if not py.exists() or not cfg.exists():
        raise SystemExit("Project .venv missing; create it with python3 -m venv .venv")
    if "include-system-site-packages = false" not in cfg.read_text():
        raise SystemExit("Project .venv must disable system site packages")
    return py


def git_checkout(path: Path, repo: str, commit: str) -> None:
    if not path.exists():
        run(["git", "clone", "--filter=blob:none", repo, str(path)])
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=path, text=True)
    if dirty:
        raise RuntimeError(f"Refusing dirty upstream checkout: {path}")
    if current != commit:
        run(["git", "fetch", "origin", commit], cwd=path)
        run(["git", "checkout", "--detach", commit], cwd=path)


def normalize_qwen(src: Path, dst: Path) -> None:
    """Rewrite only safetensors keys; tensor bytes and quant metadata are untouched.

    Never overwrite an existing target or source. Interrupted copies remain .partial.
    """
    with src.open("rb") as source:
        length = struct.unpack("<Q", source.read(8))[0]
        if length > 100_000_000:
            raise ValueError("Invalid safetensors header size")
        header = json.loads(source.read(length))
        normalized = {}
        changed = 0
        for key, value in header.items():
            new = key
            for old, prefix in (("model.language_model.", "model."), ("model.visual.", "visual.")):
                if key.startswith(old):
                    new = prefix + key[len(old):]
                    changed += 1
                    break
            if new in normalized:
                raise ValueError(f"Key collision: {new}")
            normalized[new] = value
        if not changed or sum(k.endswith(".comfy_quant") for k in header) != 350:
            raise ValueError("Unexpected Qwen source layout/quantization metadata")
        encoded = json.dumps(normalized, separators=(",", ":"), ensure_ascii=False).encode()
        encoded += b" " * (-len(encoded) % 8)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            raise FileExistsError(dst)
        partial = dst.with_suffix(dst.suffix + ".partial")
        with partial.open("xb") as target:
            target.write(struct.pack("<Q", len(encoded)))
            target.write(encoded)
            shutil.copyfileobj(source, target, 16 * 1024 * 1024)
        # Hard-link creation is atomic and refuses a racing existing target.
        os.link(partial, dst)
        partial.unlink()


def link_model(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() and dst.resolve() == src.resolve():
        return
    if dst.exists() or dst.is_symlink():
        raise FileExistsError(f"Refusing to replace model: {dst}")
    dst.symlink_to(src.resolve())


def prepare_code(repo: Path, comfy: Path, lock: dict) -> None:
    """Update only pinned checkouts and the project-owned frontend link."""
    source = repo / "comfy_extensions/H3_Director_Entry"
    for required in (source / "__init__.py", source / "web/director-entry.js",
                     repo / "workflows/comfy-ui/director-single-t2v.json"):
        if not required.is_file():
            raise FileNotFoundError(required)
    target = comfy / "custom_nodes/H3_Director_Entry"
    if target.is_symlink() and target.resolve() == source.resolve():
        pass
    elif target.exists() or target.is_symlink():
        raise FileExistsError(f"Refusing to replace extension: {target}")
    git_checkout(comfy, lock["comfyui"]["repo"], lock["comfyui"]["commit"])
    for node in lock["custom_nodes"]:
        git_checkout(comfy / "custom_nodes" / node["name"], node["repo"], node["commit"])
    if not target.is_symlink():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source.resolve(), target_is_directory=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--code-only", action="store_true", help="only pinned git checkouts + frontend link; no packages/models")
    ap.add_argument("--install-deps", action="store_true", help="disabled: no verified CUDA wheel lock")
    ap.add_argument("--wheel-dir", type=Path, help="disabled together with --install-deps")
    args = ap.parse_args()
    repo = args.repo.resolve()
    apply_project_local_env(repo)
    cfg = StudioConfig.from_env(repo)
    py = project_python(repo)
    lock = cfg.runtime_lock
    requirements = repo / lock["python_stack"]["dependency_lock"]
    if args.install_deps or args.wheel_dir:
        raise SystemExit("Installation disabled: observed package versions are not a verified CUDA wheel lock")
    comfy = cfg.runtime_root / "ComfyUI"
    if args.code_only:
        prepare_code(repo, comfy, lock)
        return 0
    run([str(py), "-E", "-s", "-m", "pip", "check"])
    # Compare the recorded collection, not just pip's dependency consistency.
    run([str(py), "-E", "-s", "-c", "import importlib.metadata as m, pathlib, sys; "
         "rows=[s.split('==') for s in pathlib.Path(sys.argv[1]).read_text().splitlines() if s and not s.startswith('#')]; "
         "bad=[f'{n}: expected {v}, got {m.version(n)}' for n,v in rows if m.version(n)!=v]; "
         "assert not bad, '\\n'.join(bad)", str(requirements)])
    root = Path(os.environ["H3_MODEL_ROOT"]).expanduser().resolve()
    fl2va = Path(os.environ["H3_NATIVE_FL2VA"]).expanduser().resolve()
    qwen = Path(os.environ["H3_NATIVE_QWEN"]).expanduser().resolve()
    for target, original in ((fl2va, root / "MiniMax-H3-FL2VA-int8_convrot.safetensors"),
                             (qwen, root / "qwen3-vl-32b-int8_convrot.safetensors")):
        if target == original.resolve() or not target.is_relative_to(root):
            raise SystemExit("Native model targets must be separate files inside H3_MODEL_ROOT")
    if not args.check_only:
        prepare_code(repo, comfy, lock)
        if not qwen.exists():
            normalize_qwen(root / "qwen3-vl-32b-int8_convrot.safetensors", qwen)
        if not fl2va.exists():
            from scripts.convert_fl2va import convert
            convert(root / "MiniMax-H3-FL2VA-int8_convrot.safetensors", fl2va)
        for kind in ("audio", "video"):
            target = root / f"MiniMax-H3-{kind}_vae-native.safetensors"
            if not target.exists():
                run([str(py), "-E", "-s", str(repo / "scripts/convert_vae.py"),
                     str(root / f"MiniMax-H3-{kind}_vae.safetensors"),
                     str(root / "FL2VA" / f"{kind}_vae" / "config.json"), str(target)])
    models = {
        "diffusion_models/MiniMax-H3-FL2VA-native-qkv-int8_convrot.safetensors": fl2va,
        "text_encoders/qwen3-vl-32b-native-int8_convrot.safetensors": qwen,
        "vae/MiniMax-H3-video_vae-native.safetensors": root / "MiniMax-H3-video_vae-native.safetensors",
        "vae/MiniMax-H3-audio_vae-native.safetensors": root / "MiniMax-H3-audio_vae-native.safetensors",
    }
    for rel, src in models.items():
        if not src.is_file():
            raise FileNotFoundError(src)
        if not args.check_only:
            link_model(src, comfy / "models" / rel)
    manifest = {"python": str(py), "comfy": str(comfy), "models": {k: str(v) for k,v in models.items()},
                "clean_rebuild_verified": False, "check_only": args.check_only}
    out = repo / "var/manifests/director-runtime.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
