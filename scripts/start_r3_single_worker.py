#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h3_studio.comfy import ComfyClient
from h3_studio.config import StudioConfig


def main() -> int:
    ap = argparse.ArgumentParser(description="Start one pinned ComfyUI Worker plus the R3 H3 Studio product entry")
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--runtime-root", type=Path, default=None)
    ap.add_argument("--gpu", default=os.environ.get("H3_WORKER_GPU", "0"))
    ap.add_argument("--no-worker", action="store_true", help="do not launch ComfyUI; use an already running H3_WORKER_URL")
    ap.add_argument("--wait-ready", type=int, default=900)
    args = ap.parse_args()

    repo = args.repo.resolve()
    os.chdir(repo)
    cfg = StudioConfig.from_env(repo)
    runtime = (args.runtime_root or (repo / "var" / "runtimes" / "r3-single-worker-product")).resolve()
    comfy = runtime / "ComfyUI"
    py = runtime / "venv" / "bin" / "python"
    gpu_label = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in str(args.gpu)) or "0"
    worker_label = f"worker-gpu{gpu_label}"
    logs = repo / "var" / "logs" / "r3-single-worker-product"
    outputs = repo / "var" / "outputs" / "r3-single-worker-product" / worker_label
    tmp = repo / "var" / "tmp" / "r3-single-worker-product" / worker_label
    for p in (logs, outputs, tmp):
        p.mkdir(parents=True, exist_ok=True)

    worker_proc = None
    if not args.no_worker:
        if not (comfy / "main.py").exists() or not py.exists():
            raise RuntimeError("R3 runtime is not prepared. Run scripts/prepare_r3_distribution.py first.")
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
        env["HF_HOME"] = str(repo / "var" / "cache" / "huggingface")
        env["TRANSFORMERS_CACHE"] = str(repo / "var" / "cache" / "huggingface" / "transformers")
        env["PYTORCH_CUDA_ALLOC_CONF"] = env.get("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        cmd = [
            str(py), str((comfy / "main.py").resolve()),
            "--listen", cfg.worker_host,
            "--port", str(cfg.worker_port),
            "--disable-auto-launch",
            "--cache-none",
            "--output-directory", str(outputs.resolve()),
            "--temp-directory", str(tmp.resolve()),
        ]
        logf = (logs / "comfyui-worker.log").open("a", encoding="utf-8")
        print("Starting ComfyUI Worker:", " ".join(cmd))
        worker_proc = subprocess.Popen(cmd, cwd=str(comfy), env=env, stdout=logf, stderr=subprocess.STDOUT, text=True)
        (logs / "comfyui-worker.pid").write_text(str(worker_proc.pid), encoding="utf-8")
        ComfyClient(cfg.worker_url).wait_ready(timeout_s=args.wait_ready)
    else:
        ComfyClient(cfg.worker_url).wait_ready(timeout_s=30)

    studio_cmd = [sys.executable, "-m", "h3_studio.server"]
    env = os.environ.copy()
    env.setdefault("H3_WORKER_URL", cfg.worker_url)
    env.setdefault("H3_STUDIO_PORT", str(cfg.studio_port))
    env.setdefault("H3_STUDIO_HOST", cfg.studio_host)
    print("Starting H3 Studio:", " ".join(studio_cmd))
    studio = subprocess.Popen(studio_cmd, cwd=str(repo), env=env)
    (logs / "h3-studio.pid").write_text(str(studio.pid), encoding="utf-8")
    print(f"H3 Studio: http://{cfg.studio_host}:{cfg.studio_port}")
    print(f"Advanced Canvas: {cfg.worker_url}/")
    exit_code = 0
    try:
        exit_code = studio.wait()
    except KeyboardInterrupt:
        studio.send_signal(signal.SIGINT)
        exit_code = 130
    finally:
        if worker_proc is not None and worker_proc.poll() is None:
            worker_proc.terminate()
            try:
                worker_proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                worker_proc.kill()
                worker_proc.wait(timeout=20)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
