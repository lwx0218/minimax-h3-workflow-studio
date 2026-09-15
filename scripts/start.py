#!/usr/bin/env python3
"""Start one ComfyUI + Director on one visible GPU (loopback by default).

    python3 scripts/start.py
    python3 scripts/start.py --legacy-studio --workers worker-gpu0

Legacy worker/Studio options require --legacy-studio; never selected implicitly.
"""
from __future__ import annotations

import argparse
import ipaddress
import urllib.request
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
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["HF_DATASETS_OFFLINE"] = "1"
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    cmd = [
        str(py), "-E", "-s", str(comfy / "main.py"),
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


def director_host() -> str:
    """Accept one explicit private/loopback IPv4, never a URL or wildcard bind."""
    try:
        host = ipaddress.IPv4Address(os.environ.get("H3_DIRECTOR_HOST", "127.0.0.1"))
    except ipaddress.AddressValueError as exc:
        raise SystemExit("H3_DIRECTOR_HOST must be one private/loopback IPv4 address") from exc
    if not host.is_private or host.is_unspecified or host.is_multicast or host.is_reserved:
        raise SystemExit("H3_DIRECTOR_HOST must be one private/loopback IPv4 address, not a wildcard")
    return str(host)


def start_director(repo: Path, comfy: Path, wait_ready: int, extra: list[str]) -> int:
    """One child, one configured bind address, single GPU, bounded readiness."""
    from scripts.prepare_runtime import project_python

    py = project_python(repo)
    if not (comfy / "main.py").is_file():
        raise SystemExit("Run scripts/prepare_runtime.py first")
    gpu = os.environ.get("H3_GPU", "0")
    if not gpu.isdecimal():
        raise SystemExit("H3_GPU must be one GPU index")
    if any(arg not in {"--cpu-vae", "--lowvram", "--disable-dynamic-vram"} for arg in extra):
        raise SystemExit("Director accepts only --cpu-vae, --lowvram, --disable-dynamic-vram")
    port = int(os.environ.get("H3_DIRECTOR_PORT", "30210"))
    worker = WorkerSpec("director", gpu, director_host(), port)
    # Refuse an occupied port rather than mistaking someone else's server for ready.
    import socket
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((worker.host, port))
    cmd, env, log_path = worker_command(py, comfy, worker, repo, [
        "--disable-all-custom-nodes", "--whitelist-custom-nodes", "ComfyUI_MiniMaxH3_Director", *extra,
    ])
    pid_path = repo / "var/logs/comfyui-director.pid"
    def stop(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    proc = None
    try:
        with log_path.open("a", encoding="utf-8") as log:
            proc = subprocess.Popen(cmd, cwd=comfy, env=env, stdout=log, stderr=subprocess.STDOUT)
        pid_path.write_text(str(proc.pid), encoding="utf-8")
        # This probes our own bound service, never an environment HTTP proxy.
        local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + wait_ready
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"ComfyUI exited {proc.returncode}; see {log_path}")
            try:
                with local_http.open(worker.url + "/object_info", timeout=2) as response:
                    nodes = json.load(response)
                required = {"MiniMaxH3Director", "UNETLoader", "CLIPLoader", "VAELoader", "CreateVideo", "SaveVideo"}
                if not required.issubset(nodes):
                    raise RuntimeError(f"Required Director nodes missing: {sorted(required - nodes.keys())}")
                break
            except OSError:
                time.sleep(1)
        else:
            raise TimeoutError(f"ComfyUI readiness timeout; see {log_path}")
        print(f"Director ready: {worker.url}/  PID {proc.pid} GPU {gpu}", flush=True)
        return proc.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        if proc is not None:
            terminate(proc)
            pid_path.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--legacy-studio", action="store_true", help="explicitly opt into the old Studio route")
    ap.add_argument("--workers", default="worker-gpu0", help="legacy only: comma-separated worker ids, or 'all'")
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
    if not args.legacy_studio:
        if args.no_workers or args.skip_studio or args.workers != "worker-gpu0":
            ap.error("worker/Studio options require --legacy-studio")
        return start_director(repo, cfg.runtime_root / "ComfyUI", args.wait_ready, args.comfy_arg)
    comfy = cfg.runtime_root / "ComfyUI"
    py = repo / ".venv" / "bin" / "python"
    if not args.no_workers and (not (comfy / "main.py").exists() or not py.exists()):
        raise SystemExit(f"ComfyUI missing under {cfg.runtime_root} or project .venv missing; prepare an isolated project environment first.")

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
