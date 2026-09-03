#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h3_studio.comfy import ComfyClient
from h3_studio.config import StudioConfig
from h3_studio.workers import WorkerSpec, host_memory_status


def sanitize(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value) or "worker"


def run_capture(cmd: list[str], timeout_s: int = 30) -> dict[str, Any]:
    try:
        cp = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s)
        return {"cmd": cmd, "returncode": cp.returncode, "stdout": cp.stdout[-4000:], "stderr": cp.stderr[-4000:]}
    except Exception as exc:  # noqa: BLE001
        return {"cmd": cmd, "error": repr(exc)}


def terminate(proc: subprocess.Popen[Any], timeout_s: int = 25) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout_s)


def main() -> int:
    ap = argparse.ArgumentParser(description="Start the R4 isolated ComfyUI Worker Pool plus H3 Studio")
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--runtime-root", type=Path, default=None, help="prepared R3/R4 runtime root; defaults to var/runtimes/r3-single-worker-product")
    ap.add_argument("--workers", default="all", help="comma-separated Worker ids to launch, or 'all'")
    ap.add_argument("--no-workers", action="store_true", help="do not launch ComfyUI; use already running configured Workers")
    ap.add_argument("--wait-ready", type=int, default=900)
    ap.add_argument("--stagger-start-s", type=float, default=10.0)
    ap.add_argument("--skip-studio", action="store_true", help="launch/wait Workers only")
    args = ap.parse_args()

    repo = args.repo.resolve()
    os.chdir(repo)
    cfg = StudioConfig.from_env(repo)
    runtime = (args.runtime_root or (repo / "var" / "runtimes" / "r3-single-worker-product")).resolve()
    comfy = runtime / "ComfyUI"
    py = runtime / "venv" / "bin" / "python"
    if not args.no_workers and (not (comfy / "main.py").exists() or not py.exists()):
        raise RuntimeError("Runtime is not prepared. Run scripts/prepare_r3_distribution.py first.")

    all_workers = [WorkerSpec.from_doc(item) for item in cfg.worker_pool.get("workers", [])]
    requested = {w.strip() for w in args.workers.split(",") if w.strip()}
    selected = all_workers if args.workers == "all" else [w for w in all_workers if w.id in requested]
    if not selected:
        raise RuntimeError("No configured Workers selected")

    logs_root = repo / "var" / "logs" / "r4-multi-worker-mvp"
    manifest_dir = repo / "var" / "manifests"
    logs_root.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    procs: list[tuple[WorkerSpec, subprocess.Popen[Any]]] = []
    lifecycle: dict[str, Any] = {
        "schema_version": 1,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_root": str(runtime),
        "worker_pool": cfg.worker_pool,
        "selected_workers": [w.as_record() for w in selected],
        "safe_concurrent_runs": cfg.worker_pool.get("safe_concurrent_runs"),
        "host_memory_start": host_memory_status(),
        "nvidia_smi_start": run_capture(["nvidia-smi", "--query-gpu=index,name,uuid,memory.total,memory.used,utilization.gpu", "--format=csv,noheader,nounits"]),
        "processes": [],
    }
    exit_code = 0
    studio: subprocess.Popen[Any] | None = None

    def request_stop(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        if not args.no_workers:
            for idx, worker in enumerate(selected):
                worker_log_dir = logs_root / sanitize(worker.log_namespace)
                outputs = repo / "var" / "outputs" / "r4-multi-worker-mvp" / sanitize(worker.output_namespace)
                tmp = repo / "var" / "tmp" / "r4-multi-worker-mvp" / sanitize(worker.temp_namespace)
                for path in (worker_log_dir, outputs, tmp):
                    path.mkdir(parents=True, exist_ok=True)
                env = os.environ.copy()
                env["CUDA_VISIBLE_DEVICES"] = worker.gpu
                env["HF_HOME"] = str(repo / "var" / "cache" / "huggingface")
                env["TRANSFORMERS_CACHE"] = str(repo / "var" / "cache" / "huggingface" / "transformers")
                env["PYTORCH_CUDA_ALLOC_CONF"] = env.get("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
                cmd = [
                    str(py), str((comfy / "main.py").resolve()),
                    "--listen", worker.host,
                    "--port", str(worker.port),
                    "--disable-auto-launch",
                    "--cache-none",
                    "--output-directory", str(outputs.resolve()),
                    "--temp-directory", str(tmp.resolve()),
                ]
                logf = (worker_log_dir / "comfyui-worker.log").open("a", encoding="utf-8")
                print(f"Starting {worker.id} on GPU {worker.gpu}: {' '.join(cmd)}", flush=True)
                proc = subprocess.Popen(cmd, cwd=str(comfy), env=env, stdout=logf, stderr=subprocess.STDOUT, text=True)
                (worker_log_dir / "comfyui-worker.pid").write_text(str(proc.pid), encoding="utf-8")
                procs.append((worker, proc))
                lifecycle["processes"].append({"worker": worker.as_record(), "pid": proc.pid, "log": str(worker_log_dir / "comfyui-worker.log")})
                if idx + 1 < len(selected) and args.stagger_start_s > 0:
                    time.sleep(args.stagger_start_s)
        for worker in selected:
            ComfyClient(worker.url).wait_ready(timeout_s=args.wait_ready)
        lifecycle["workers_ready_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lifecycle["host_memory_after_worker_ready"] = host_memory_status()
        (manifest_dir / "r4-worker-pool-lifecycle.json").write_text(json.dumps(lifecycle, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.skip_studio:
            print(json.dumps({"workers_ready": [w.id for w in selected], "manifest": str(manifest_dir / "r4-worker-pool-lifecycle.json")}, ensure_ascii=False, indent=2))
            return 0

        env = os.environ.copy()
        env.setdefault("H3_STUDIO_PORT", str(cfg.studio_port))
        env.setdefault("H3_STUDIO_HOST", cfg.studio_host)
        env.setdefault("H3_WORKER_POOL_CONFIG", str(repo / "config" / "worker-pool.json"))
        studio_cmd = [sys.executable, "-m", "h3_studio.server"]
        studio_log = (logs_root / "h3-studio.log").open("a", encoding="utf-8")
        print("Starting H3 Studio:", " ".join(studio_cmd), flush=True)
        studio = subprocess.Popen(studio_cmd, cwd=str(repo), env=env, stdout=studio_log, stderr=subprocess.STDOUT, text=True)
        (logs_root / "h3-studio.pid").write_text(str(studio.pid), encoding="utf-8")
        print(f"H3 Studio: http://{cfg.studio_host}:{cfg.studio_port}")
        print("Workers:", ", ".join(f"{w.id}={w.url}" for w in selected))
        exit_code = studio.wait()
    except KeyboardInterrupt:
        exit_code = 130
        if studio is not None:
            studio.send_signal(signal.SIGINT)
    finally:
        if studio is not None:
            terminate(studio)
        for _worker, proc in reversed(procs):
            terminate(proc)
        lifecycle["stopped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lifecycle["host_memory_stop"] = host_memory_status()
        lifecycle["nvidia_smi_stop"] = run_capture(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory", "--format=csv,noheader,nounits"])
        (manifest_dir / "r4-worker-pool-lifecycle.json").write_text(json.dumps(lifecycle, ensure_ascii=False, indent=2), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
