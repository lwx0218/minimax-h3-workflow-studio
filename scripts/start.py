#!/usr/bin/env python3
"""Start the ComfyUI worker pool and the Studio.

    python3 scripts/start.py                       # all workers + Studio
    python3 scripts/start.py --workers worker-gpu0 # one worker + Studio
    python3 scripts/start.py --no-workers          # Studio only, workers already running
    python3 scripts/start.py --skip-studio         # workers only

Workers bind worker_host from config/worker-pool.json (default 127.0.0.1) and are
reached through the Studio's /canvas/<worker-id>/ proxy. Ctrl-C stops everything.
"""
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

from h3_studio.comfy import ComfyClient  # noqa: E402
from h3_studio.config import StudioConfig, apply_project_local_env, project_local_env  # noqa: E402
from h3_studio.workers import WorkerPool, WorkerSpec, host_memory_status  # noqa: E402


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


def worker_command(py: Path, comfy: Path, worker: WorkerSpec, repo: Path, extra: list[str]) -> tuple[list[str], dict[str, str], Path]:
    outputs = repo / "var" / "outputs" / worker.id
    tmp = repo / "var" / "tmp" / worker.id
    inputs = repo / "var" / "inputs" / worker.id
    user = repo / "var" / "user" / worker.id
    log_dir = repo / "var" / "logs"
    for path in (outputs, tmp, inputs, user, log_dir):
        path.mkdir(parents=True, exist_ok=True)
    env = project_local_env(repo)
    env["CUDA_VISIBLE_DEVICES"] = worker.gpu
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    cmd = [
        str(py), str(comfy / "main.py"),
        "--listen", worker.host,
        "--port", str(worker.port),
        "--disable-auto-launch",
        "--cache-none",
        "--output-directory", str(outputs.resolve()),
        "--temp-directory", str(tmp.resolve()),
        "--input-directory", str(inputs.resolve()),
        "--user-directory", str(user.resolve()),
        *extra,
    ]
    return cmd, env, log_dir / f"comfyui-{worker.id}.log"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--workers", default="all", help="comma-separated worker ids, or 'all'")
    ap.add_argument("--no-workers", action="store_true", help="do not launch ComfyUI; use already running workers")
    ap.add_argument("--skip-studio", action="store_true", help="launch and wait for workers only")
    ap.add_argument("--wait-ready", type=int, default=900, help="seconds to wait for each worker")
    ap.add_argument("--stagger-start-s", type=float, default=10.0)
    ap.add_argument("--comfy-arg", action="append", default=[], help="extra argument passed to every ComfyUI worker (repeatable), e.g. --comfy-arg=--use-sage-attention")
    args = ap.parse_args()

    repo = args.repo.resolve()
    os.chdir(repo)
    apply_project_local_env(repo)
    cfg = StudioConfig.from_env(repo)
    comfy = cfg.runtime_root / "ComfyUI"
    py = cfg.runtime_root / "venv" / "bin" / "python"
    if not args.no_workers and (not (comfy / "main.py").exists() or not py.exists()):
        raise SystemExit(f"Runtime not prepared under {cfg.runtime_root}. Run scripts/prepare_runtime.py first (or set H3_RUNTIME_ROOT).")

    pool = WorkerPool(cfg.worker_pool)
    wanted = {w.strip() for w in args.workers.split(",") if w.strip()}
    selected = pool.workers if args.workers == "all" else [w for w in pool.workers if w.id in wanted]
    if not selected:
        raise SystemExit("No configured workers selected")

    logs = repo / "var" / "logs"
    manifests = repo / "var" / "manifests"
    logs.mkdir(parents=True, exist_ok=True)
    manifests.mkdir(parents=True, exist_ok=True)
    lifecycle: dict[str, Any] = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_root": str(cfg.runtime_root),
        "selected_workers": [w.as_record() for w in selected],
        "safe_concurrent_runs": pool.safe_concurrent_runs,
        "host_memory_start": host_memory_status(),
        "nvidia_smi_start": run_capture(["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used", "--format=csv,noheader,nounits"]),
        "processes": [],
    }
    procs: list[tuple[WorkerSpec, subprocess.Popen[Any]]] = []
    studio: subprocess.Popen[Any] | None = None
    exit_code = 0

    def request_stop(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        if not args.no_workers:
            for idx, worker in enumerate(selected):
                cmd, env, log_path = worker_command(py, comfy, worker, repo, args.comfy_arg)
                print(f"Starting {worker.id} on GPU {worker.gpu} -> {worker.url}", flush=True)
                logf = log_path.open("a", encoding="utf-8")
                proc = subprocess.Popen(cmd, cwd=str(comfy), env=env, stdout=logf, stderr=subprocess.STDOUT, text=True)
                (logs / f"comfyui-{worker.id}.pid").write_text(str(proc.pid), encoding="utf-8")
                procs.append((worker, proc))
                lifecycle["processes"].append({"worker": worker.id, "pid": proc.pid, "log": str(log_path)})
                if idx + 1 < len(selected) and args.stagger_start_s > 0:
                    time.sleep(args.stagger_start_s)
        for worker in selected:
            ComfyClient(worker.url).wait_ready(timeout_s=args.wait_ready)
            print(f"{worker.id} ready", flush=True)
        lifecycle["workers_ready_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lifecycle["host_memory_after_ready"] = host_memory_status()
        (manifests / "worker-pool-lifecycle.json").write_text(json.dumps(lifecycle, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.skip_studio:
            print(json.dumps({"workers_ready": [w.id for w in selected]}, ensure_ascii=False))
            return 0

        studio_log = (logs / "h3-studio.log").open("a", encoding="utf-8")
        studio = subprocess.Popen([sys.executable, "-m", "h3_studio.server"], cwd=str(repo), env=project_local_env(repo), stdout=studio_log, stderr=subprocess.STDOUT, text=True)
        (logs / "h3-studio.pid").write_text(str(studio.pid), encoding="utf-8")
        print(f"H3 Studio: http://{cfg.studio_host}:{cfg.studio_port}/   (canvas: /canvas/<worker-id>/)", flush=True)
        exit_code = studio.wait()
    except KeyboardInterrupt:
        exit_code = 130
        if studio is not None and studio.poll() is None:
            studio.send_signal(signal.SIGINT)
            try:
                studio.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
    finally:
        if studio is not None:
            terminate(studio)
        for _worker, proc in reversed(procs):
            terminate(proc)
        lifecycle["stopped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lifecycle["nvidia_smi_stop"] = run_capture(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory", "--format=csv,noheader,nounits"])
        (manifests / "worker-pool-lifecycle.json").write_text(json.dumps(lifecycle, ensure_ascii=False, indent=2), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
