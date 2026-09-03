#!/usr/bin/env python3
"""Run the R2 bounded ComfyUI MiniMax-H3 cold/warm probe.

This is checkpoint evidence tooling, not product runtime code. It starts one
project-local ComfyUI process, submits a fixed T2VA workflow twice on one GPU,
records resource samples, validates media with ffprobe/ffmpeg, and exits with a
non-zero code if safety or media gates fail.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

try:
    import psutil
except Exception:  # pragma: no cover - dependency installed in runtime venv
    psutil = None


DEFAULT_PROMPT = (
    "A five-second cinematic 16:9 shot of a small paper boat gliding through "
    "a rain-lit city gutter at night. Reflections ripple across the water, a "
    "distant train passes, and the ambient rain and wheel noise stay "
    "synchronized with the movement. Natural camera motion, no subtitles, no logos."
)


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def post_json(url: str, payload: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str, timeout: float = 15.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_server(base_url: str, proc: subprocess.Popen[Any], timeout_s: int) -> dict[str, Any]:
    start = time.monotonic()
    last_error = None
    while time.monotonic() - start < timeout_s:
        if proc.poll() is not None:
            raise RuntimeError(f"ComfyUI exited before readiness with code {proc.returncode}")
        try:
            stats = get_json(f"{base_url}/system_stats", timeout=5)
            return {"ready_at": now(), "ready_after_s": round(time.monotonic() - start, 3), "system_stats": stats}
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            time.sleep(1)
    raise TimeoutError(f"ComfyUI did not become ready in {timeout_s}s; last_error={last_error}")


def build_prompt(prefix: str, seed: int, prompt: str, width: int, height: int, duration: float, sigma_points: int) -> dict[str, Any]:
    return {
        "1": {
            "class_type": "RHMiniMaxH3DirectTextEncoderLoader",
            "inputs": {
                "model_root": "MiniMax-H3",
                "dtype": "auto",
                "text_encoder_path": "qwen3-vl-32b-int8_convrot.safetensors",
            },
        },
        "2": {
            "class_type": "RHMiniMaxH3DirectModelLoader",
            "inputs": {
                "model_root": "MiniMax-H3",
                "dtype": "auto",
                "transformer_path": "MiniMax-H3-FL2VA-int8_convrot.safetensors",
            },
        },
        "3": {
            "class_type": "RHMiniMaxH3DirectVAELoader",
            "inputs": {
                "model_root": "MiniMax-H3",
                "video_vae_path": "MiniMax-H3-video_vae.safetensors",
                "audio_vae_path": "MiniMax-H3-audio_vae.safetensors",
            },
        },
        "4": {
            "class_type": "RHMiniMaxH3T2VATarget",
            "inputs": {
                "aspect_ratio": "16:9",
                "duration_seconds": duration,
                "width": width,
                "height": height,
            },
        },
        "5": {
            "class_type": "RHMiniMaxH3T2VATextEncode",
            "inputs": {"h3_text_encoder": ["1", 0], "prompt": prompt},
        },
        "6": {
            "class_type": "RHMiniMaxH3EmptyAVLatent",
            "inputs": {"target": ["4", 0]},
        },
        "7": {
            "class_type": "RHMiniMaxH3DualSigmaSampler",
            "inputs": {
                "h3_model": ["2", 0],
                "conditioning": ["5", 0],
                "av_latent": ["6", 0],
                "seed": seed,
                "sigma_points": sigma_points,
                "video_shift": 12.0,
                "audio_shift": 3.0,
                "accel": "off",
                "denoise_video": True,
                "cache_dit_rdt": 0.12,
                "cache_dit_mc": 2,
                "cache_dit_warmup": 4,
                "velocity_stride": 4,
                "sampler_mode": "res_multistep",
                "allow_accel_with_res_multistep": False,
            },
        },
        "8": {
            "class_type": "RHMiniMaxH3DecodeAV",
            "inputs": {"h3_vae_bundle": ["3", 0], "sampled_av_latent": ["7", 0]},
        },
        "9": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["8", 0], "audio": ["8", 1], "fps": 24.0, "bit_depth": 8},
        },
        "10": {
            "class_type": "SaveVideo",
            "inputs": {"video": ["9", 0], "filename_prefix": prefix, "format": "mp4", "codec": "h264"},
        },
    }


def rss_tree_mib(pid: int) -> float:
    if psutil is None:
        return 0.0
    try:
        proc = psutil.Process(pid)
        procs = [proc] + proc.children(recursive=True)
        total = 0
        for p in procs:
            try:
                total += p.memory_info().rss
            except psutil.Error:
                pass
        return total / 1024 / 1024
    except Exception:
        return 0.0


def mem_used_gib() -> float:
    if psutil is not None:
        vm = psutil.virtual_memory()
        return (vm.total - vm.available) / 1024**3
    with open("/proc/meminfo", "r", encoding="utf-8") as f:
        vals: dict[str, int] = {}
        for line in f:
            key, rest = line.split(":", 1)
            vals[key] = int(rest.strip().split()[0])
    return (vals["MemTotal"] - vals.get("MemAvailable", vals.get("MemFree", 0))) / 1024**2


def gpu_snapshot() -> list[dict[str, Any]]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,uuid,memory.used,memory.free,temperature.gpu,pstate",
        "--format=csv,noheader,nounits",
    ]
    try:
        out = subprocess.check_output(cmd, text=True, timeout=10)
    except Exception as exc:  # noqa: BLE001
        return [{"error": repr(exc)}]
    rows = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 6:
            rows.append({
                "index": int(parts[0]),
                "uuid": parts[1],
                "memory_used_mib": int(parts[2]),
                "memory_free_mib": int(parts[3]),
                "temperature_c": int(parts[4]),
                "pstate": parts[5],
            })
    return rows


class ResourceMonitor:
    def __init__(self, pid: int, interval_s: float, abort_mem_gib: float, hard_mem_gib: float, max_temp_c: int):
        self.pid = pid
        self.interval_s = interval_s
        self.abort_mem_gib = abort_mem_gib
        self.hard_mem_gib = hard_mem_gib
        self.max_temp_c = max_temp_c
        self.samples: list[dict[str, Any]] = []
        self.violations: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            sample = {
                "t": now(),
                "host_used_gib": round(mem_used_gib(), 3),
                "process_rss_mib": round(rss_tree_mib(self.pid), 1),
                "gpus": gpu_snapshot(),
            }
            self.samples.append(sample)
            if sample["host_used_gib"] >= self.abort_mem_gib:
                self.violations.append({"kind": "host_abort", "sample": sample})
                try:
                    os.kill(self.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                time.sleep(5)
                try:
                    os.kill(self.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                return
            if sample["host_used_gib"] >= self.hard_mem_gib:
                self.violations.append({"kind": "host_hard_line", "sample": sample})
            for gpu in sample["gpus"]:
                if isinstance(gpu, dict) and gpu.get("temperature_c", 0) >= self.max_temp_c:
                    self.violations.append({"kind": "gpu_temp", "sample": sample})
                    try:
                        os.kill(self.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    return
            self._stop.wait(self.interval_s)

    def summary(self) -> dict[str, Any]:
        peak_host = max((s["host_used_gib"] for s in self.samples), default=0.0)
        peak_rss = max((s["process_rss_mib"] for s in self.samples), default=0.0)
        peak_gpu: dict[str, int] = {}
        peak_temp: dict[str, int] = {}
        for s in self.samples:
            for g in s["gpus"]:
                if not isinstance(g, dict) or "index" not in g:
                    continue
                idx = str(g["index"])
                peak_gpu[idx] = max(peak_gpu.get(idx, 0), int(g.get("memory_used_mib", 0)))
                peak_temp[idx] = max(peak_temp.get(idx, 0), int(g.get("temperature_c", 0)))
        return {
            "sample_count": len(self.samples),
            "peak_host_used_gib": round(peak_host, 3),
            "peak_process_rss_mib": round(peak_rss, 1),
            "peak_gpu_memory_used_mib": peak_gpu,
            "peak_gpu_temperature_c": peak_temp,
            "violations": self.violations,
        }


def poll_prompt(base_url: str, prompt_id: str, timeout_s: int) -> dict[str, Any]:
    start = time.monotonic()
    last = None
    while time.monotonic() - start < timeout_s:
        hist = get_json(f"{base_url}/history/{prompt_id}", timeout=20)
        if prompt_id in hist:
            last = hist[prompt_id]
            status = last.get("status", {})
            if status.get("completed") is True or status.get("status_str") in {"success", "error"}:
                return {"history": last, "elapsed_s": round(time.monotonic() - start, 3)}
        time.sleep(5)
    return {"history": last, "elapsed_s": round(time.monotonic() - start, 3), "timeout": True}


def flatten_history_outputs(history: dict[str, Any]) -> list[dict[str, Any]]:
    outs: list[dict[str, Any]] = []
    for node_id, payload in (history.get("outputs") or {}).items():
        if not isinstance(payload, dict):
            continue
        for key, value in payload.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "filename" in item:
                        out = dict(item)
                        out["node_id"] = node_id
                        out["output_key"] = key
                        outs.append(out)
    return outs


def resolve_output_file(output_dir: Path, item: dict[str, Any]) -> Path:
    typ = item.get("type", "output")
    base = output_dir if typ == "output" else output_dir.parent / str(typ)
    sub = item.get("subfolder") or ""
    return base / sub / item["filename"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_capture(cmd: list[str], timeout_s: int) -> dict[str, Any]:
    started = time.monotonic()
    cp = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s)
    return {
        "cmd": cmd,
        "returncode": cp.returncode,
        "elapsed_s": round(time.monotonic() - started, 3),
        "stdout": cp.stdout[-8000:],
        "stderr": cp.stderr[-8000:],
    }


def media_validate(ffprobe: Path, ffmpeg: Path, media: Path, frames_dir: Path, label: str) -> dict[str, Any]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    probe_cmd = [str(ffprobe), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(media)]
    probe_raw = subprocess.check_output(probe_cmd, text=True, timeout=60)
    probe = json.loads(probe_raw)
    streams = probe.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    decode = run_capture([str(ffmpeg), "-v", "error", "-i", str(media), "-f", "null", "-"], timeout_s=300)
    black = run_capture([str(ffmpeg), "-hide_banner", "-i", str(media), "-vf", "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"], timeout_s=300)
    silence = run_capture([str(ffmpeg), "-hide_banner", "-i", str(media), "-af", "silencedetect=n=-50dB:d=0.5", "-vn", "-f", "null", "-"], timeout_s=300)
    duration = float((probe.get("format") or {}).get("duration") or 0.0)
    positions = [0.1, max(0.1, duration / 2.0), max(0.1, duration - 0.2)]
    extracted = []
    for idx, pos in enumerate(positions):
        png = frames_dir / f"{label}-frame-{idx}.png"
        cmd = [str(ffmpeg), "-y", "-ss", f"{pos:.3f}", "-i", str(media), "-frames:v", "1", "-update", "1", str(png)]
        cap = run_capture(cmd, timeout_s=120)
        extracted.append({"position_s": pos, "path": str(png), "returncode": cap["returncode"], "stderr": cap["stderr"][-1000:]})
    stats: list[dict[str, Any]] = []
    try:
        from PIL import Image, ImageStat
        for item in extracted:
            p = Path(item["path"])
            if not p.exists():
                continue
            im = Image.open(p).convert("RGB")
            stat = ImageStat.Stat(im)
            stats.append({
                "path": str(p),
                "size": list(im.size),
                "mean_rgb": [round(v, 3) for v in stat.mean],
                "stddev_rgb": [round(v, 3) for v in stat.stddev],
            })
    except Exception as exc:  # noqa: BLE001
        stats.append({"error": repr(exc)})
    return {
        "file": str(media),
        "sha256": sha256_file(media),
        "bytes": media.stat().st_size,
        "probe": probe,
        "decode": decode,
        "blackdetect": black,
        "silencedetect": silence,
        "extracted_frames": extracted,
        "frame_stats": stats,
        "pass": bool(
            video
            and audio
            and decode["returncode"] == 0
            and black["returncode"] == 0
            and silence["returncode"] == 0
            and "black_start" not in black.get("stderr", "")
            and "silence_start" not in silence.get("stderr", "")
            and media.stat().st_size > 1000
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--comfy", type=Path, required=True)
    ap.add_argument("--python", type=Path, required=True)
    ap.add_argument("--ffmpeg", type=Path, required=True)
    ap.add_argument("--ffprobe", type=Path, required=True)
    ap.add_argument("--gpu", default="0")
    ap.add_argument("--port", type=int, default=30122)
    ap.add_argument("--width", type=int, default=864)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--duration", type=float, default=5.0)
    ap.add_argument("--sigma-points", type=int, default=21)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--load-timeout", type=int, default=900)
    ap.add_argument("--generation-timeout", type=int, default=3600)
    ap.add_argument("--host-abort-gib", type=float, default=230.0)
    ap.add_argument("--host-hard-gib", type=float, default=235.0)
    ap.add_argument("--max-temp-c", type=int, default=84)
    args = ap.parse_args()

    repo = args.repo.resolve()
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    root = repo / "var" / "outputs" / "r2-runtime-decision" / f"probe-{run_id}"
    logs = repo / "var" / "logs" / "r2-runtime-decision" / f"probe-{run_id}"
    tmp = repo / "var" / "tmp" / "r2-runtime-decision" / f"probe-{run_id}"
    frames = root / "frames"
    root.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)

    base_url = f"http://127.0.0.1:{args.port}"
    server_log = logs / "comfyui-server.log"
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    env["PATH"] = str(args.ffmpeg.parent.resolve()) + os.pathsep + env.get("PATH", "")
    env["HF_HOME"] = str(repo / "var" / "cache" / "huggingface")
    env["TRANSFORMERS_CACHE"] = str(repo / "var" / "cache" / "huggingface" / "transformers")
    env["PYTORCH_CUDA_ALLOC_CONF"] = env.get("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    cmd = [
        str(args.python),
        str((args.comfy / "main.py").resolve()),
        "--listen",
        "127.0.0.1",
        "--port",
        str(args.port),
        "--disable-auto-launch",
        "--cache-none",
        "--output-directory",
        str(root.resolve()),
        "--temp-directory",
        str(tmp.resolve()),
    ]
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": now(),
        "server_command": cmd,
        "cuda_visible_devices": env["CUDA_VISIBLE_DEVICES"],
        "bounds": {
            "host_abort_gib": args.host_abort_gib,
            "host_hard_gib": args.host_hard_gib,
            "max_temp_c": args.max_temp_c,
            "load_timeout_s": args.load_timeout,
            "generation_timeout_s": args.generation_timeout,
        },
        "profile": {
            "task": "T2VA via FL2VA partition",
            "width": args.width,
            "height": args.height,
            "duration_seconds_requested": args.duration,
            "expected_frame_count": 124,
            "fps": 24,
            "sigma_points": args.sigma_points,
            "effective_dit_forwards": args.sigma_points - 1,
            "sampler_mode": "res_multistep",
            "accel": "off",
            "seed": args.seed,
            "prompt_sha256": hashlib.sha256(args.prompt.encode("utf-8")).hexdigest(),
        },
        "paths": {"output_root": str(root), "log_root": str(logs), "tmp_root": str(tmp)},
        "initial_gpu_snapshot": gpu_snapshot(),
        "initial_host_used_gib": round(mem_used_gib(), 3),
    }

    proc: subprocess.Popen[Any] | None = None
    monitor: ResourceMonitor | None = None
    try:
        with server_log.open("w", encoding="utf-8") as logf:
            proc = subprocess.Popen(cmd, cwd=str(args.comfy.resolve()), env=env, stdout=logf, stderr=subprocess.STDOUT, text=True)
            metadata["server_pid"] = proc.pid
            monitor = ResourceMonitor(proc.pid, interval_s=1.0, abort_mem_gib=args.host_abort_gib, hard_mem_gib=args.host_hard_gib, max_temp_c=args.max_temp_c)
            monitor.start()
            metadata["server_ready"] = wait_server(base_url, proc, args.load_timeout)

            phases = []
            for label in ("cold", "warm"):
                prefix = f"r2_probe/{label}"
                prompt = build_prompt(prefix, args.seed, args.prompt, args.width, args.height, args.duration, args.sigma_points)
                req_path = logs / f"{label}-prompt.json"
                req_path.write_text(json.dumps(prompt, ensure_ascii=False, indent=2), encoding="utf-8")
                submit_started = time.monotonic()
                submit = post_json(f"{base_url}/prompt", {"prompt": prompt, "client_id": f"r2-{label}-{uuid.uuid4()}"}, timeout=60)
                prompt_id = submit["prompt_id"]
                poll = poll_prompt(base_url, prompt_id, args.generation_timeout)
                phase_elapsed = round(time.monotonic() - submit_started, 3)
                hist_path = logs / f"{label}-history.json"
                hist_path.write_text(json.dumps(poll, ensure_ascii=False, indent=2), encoding="utf-8")
                hist = poll.get("history") or {}
                status = hist.get("status") or {}
                outs = flatten_history_outputs(hist)
                media_items = [o for o in outs if str(o.get("filename", "")).lower().endswith((".mp4", ".webm", ".mkv", ".mov"))]
                media_validations = []
                for item in media_items:
                    fpath = resolve_output_file(root, item)
                    if fpath.exists():
                        media_validations.append(media_validate(args.ffprobe.resolve(), args.ffmpeg.resolve(), fpath, frames, label))
                phase = {
                    "label": label,
                    "submitted_at": now(),
                    "prompt_id": prompt_id,
                    "submit_response": submit,
                    "elapsed_submit_to_terminal_s": phase_elapsed,
                    "poll": {k: v for k, v in poll.items() if k != "history"},
                    "status": status,
                    "outputs": outs,
                    "media_validations": media_validations,
                    "pass": bool(status.get("completed") is True and media_validations and all(m.get("pass") for m in media_validations)),
                }
                phases.append(phase)
                metadata["phases"] = phases
                (logs / "partial-result.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
                if not phase["pass"]:
                    break
            metadata["phases"] = phases
    except Exception as exc:  # noqa: BLE001
        metadata["exception"] = repr(exc)
    finally:
        if monitor is not None:
            monitor.stop()
            metadata["resource_summary"] = monitor.summary()
            samples_path = logs / "resource-samples.jsonl"
            with samples_path.open("w", encoding="utf-8") as f:
                for s in monitor.samples:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=20)
        metadata["server_returncode"] = None if proc is None else proc.returncode
        time.sleep(3)
        metadata["final_gpu_snapshot"] = gpu_snapshot()
        metadata["finished_at"] = now()
        metadata["server_log"] = str(server_log)
        result_path = logs / "result.json"
        result_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({
            "result_path": str(result_path),
            "output_root": str(root),
            "passes": [p.get("pass") for p in metadata.get("phases", [])],
            "resource_summary": metadata.get("resource_summary"),
            "exception": metadata.get("exception"),
        }, ensure_ascii=False, indent=2))

    if metadata.get("exception"):
        return 2
    if metadata.get("resource_summary", {}).get("violations"):
        return 3
    phases = metadata.get("phases", [])
    if len(phases) != 2 or not all(p.get("pass") for p in phases):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
