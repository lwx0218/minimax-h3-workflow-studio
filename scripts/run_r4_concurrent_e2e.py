#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from run_r3_product_e2e import get_json, post_form, run_capture, validate_media


def host_memory_status() -> dict[str, Any]:
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, rest = line.split(":", 1)
            values[key] = int(rest.strip().split()[0]) * 1024
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", 0)
        used = max(total - available, 0)
        gib = 1024**3
        return {"total_gib": round(total / gib, 3), "available_gib": round(available / gib, 3), "used_gib": round(used / gib, 3)}
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


def gpu_status() -> list[dict[str, Any]]:
    cp = run_capture(["nvidia-smi", "--query-gpu=index,memory.used,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"], 30)
    rows = []
    if cp.get("returncode") == 0:
        for line in str(cp.get("stdout", "")).splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                rows.append({"index": parts[0], "memory_used_mib": int(parts[1]), "utilization_gpu_pct": int(parts[2]), "temperature_c": int(parts[3])})
    return rows


class ResourceMonitor:
    def __init__(self, interval_s: float = 5.0):
        self.interval_s = interval_s
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        start = time.monotonic()
        while not self._stop.is_set():
            self.samples.append({"t": round(time.monotonic() - start, 3), "host_memory": host_memory_status(), "gpus": gpu_status()})
            self._stop.wait(self.interval_s)

    def __enter__(self) -> "ResourceMonitor":
        self._thread.start()
        return self

    def __exit__(self, *_args: Any) -> None:
        self._stop.set()
        self._thread.join(timeout=self.interval_s + 2)

    def summary(self) -> dict[str, Any]:
        peak_host = max((s.get("host_memory", {}).get("used_gib", 0) for s in self.samples), default=0)
        peak_gpu: dict[str, int] = {}
        peak_temp: dict[str, int] = {}
        for sample in self.samples:
            for gpu in sample.get("gpus", []):
                idx = str(gpu["index"])
                peak_gpu[idx] = max(peak_gpu.get(idx, 0), int(gpu.get("memory_used_mib", 0)))
                peak_temp[idx] = max(peak_temp.get(idx, 0), int(gpu.get("temperature_c", 0)))
        return {"sample_count": len(self.samples), "peak_host_used_gib": peak_host, "peak_gpu_memory_used_mib": peak_gpu, "peak_gpu_temperature_c": peak_temp}


def wait_run(base: str, run_id: str, timeout_s: int, samples: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        run = get_json(base.rstrip("/") + "/api/runs/" + urllib.parse.quote(run_id), timeout=60)
        samples.append({
            "t": round(time.monotonic() - start, 3),
            "run_id": run_id,
            "status": run.get("status"),
            "worker": run.get("worker"),
            "prompt_id": run.get("prompt_id"),
            "artifacts": len(run.get("artifacts", [])),
        })
        print(json.dumps(samples[-1], ensure_ascii=False), flush=True)
        if run.get("status") in {"completed", "failed", "cancelled"}:
            return run
        time.sleep(5)
    raise TimeoutError(run_id)


def submit_and_wait(args: argparse.Namespace, label: str, seed: str, prompt: str, out: dict[str, Any]) -> None:
    submit_wall = time.time()
    submit = post_form(args.studio_url, {"kind": "t2va", "profile": "balanced-r2-a5000", "prompt": prompt, "seed": seed}, None)
    samples: list[dict[str, Any]] = []
    run = wait_run(args.studio_url, submit["run_id"], args.timeout, samples)
    completed_wall = time.time()
    result: dict[str, Any] = {"label": label, "submit": submit, "run": run, "samples": samples, "submitted_at_unix": submit_wall, "terminal_at_unix": completed_wall, "ok": False}
    if run.get("status") == "completed" and run.get("artifacts"):
        art = run["artifacts"][0]
        media_path = args.media_dir / f"{label}-{run['run_id']}.mp4"
        with urllib.request.urlopen(args.studio_url.rstrip("/") + art["download_url"], timeout=300) as resp:
            media_path.write_bytes(resp.read())
        validation = validate_media(args.ffprobe, args.ffmpeg, media_path, 864, 480, 124)
        result.update({"artifact": art, "media": str(media_path), "validation": validation, "ok": validation["ok"]})
    out[label] = result


def main() -> int:
    ap = argparse.ArgumentParser(description="Submit two independent Runs concurrently through H3 Studio and validate media/artifact correlation")
    ap.add_argument("--studio-url", default="http://127.0.0.1:30210")
    ap.add_argument("--ffmpeg", type=Path, required=True)
    ap.add_argument("--ffprobe", type=Path, required=True)
    ap.add_argument("--timeout", type=int, default=4200)
    ap.add_argument("--out", type=Path, default=Path("var/logs/r4-multi-worker-mvp/concurrent-e2e-result.json"))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.media_dir = args.out.parent / "media"
    args.media_dir.mkdir(parents=True, exist_ok=True)

    pool_before = get_json(args.studio_url.rstrip("/") + "/api/workers", timeout=60)
    prompts = {
        "run_a": "A five-second cinematic 16:9 shot of a paper boat racing through neon rainwater at night, train lights reflected in ripples, synchronized stereo rain and wheel ambience, no subtitles, no logos.",
        "run_b": "A five-second cinematic 16:9 shot of a tiny lantern floating across a moonlit harbor, gulls and soft bell tones synchronized in stereo, natural camera motion, no subtitles, no logos.",
    }
    results: dict[str, Any] = {}
    threads = [
        threading.Thread(target=submit_and_wait, args=(args, "run_a", "201", prompts["run_a"], results), daemon=True),
        threading.Thread(target=submit_and_wait, args=(args, "run_b", "202", prompts["run_b"], results), daemon=True),
    ]
    start_wall = time.time()
    with ResourceMonitor() as monitor:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    pool_after = get_json(args.studio_url.rstrip("/") + "/api/workers", timeout=60)
    workers = [((r.get("run") or {}).get("worker") or {}).get("id") for r in results.values()]
    intervals = [(r.get("submitted_at_unix"), r.get("terminal_at_unix")) for r in results.values()]
    overlap = False
    if len(intervals) == 2 and all(a and b for a, b in intervals):
        (a0, a1), (b0, b1) = intervals
        overlap = max(a0, b0) < min(a1, b1)
    doc = {
        "schema_version": 1,
        "started_at_unix": start_wall,
        "pool_before": pool_before,
        "pool_after": pool_after,
        "results": results,
        "resource_samples": monitor.samples,
        "resource_summary": monitor.summary(),
        "distinct_workers": len(set(workers)) == 2,
        "overlap": overlap,
        "ok": len(results) == 2 and all(r.get("ok") for r in results.values()) and len(set(workers)) == 2 and overlap,
        "nvidia_compute_apps_after": run_capture(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory", "--format=csv,noheader,nounits"], 30),
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(args.out), "ok": doc["ok"], "workers": workers, "overlap": overlap}, ensure_ascii=False, indent=2))
    return 0 if doc["ok"] else 5


if __name__ == "__main__":
    raise SystemExit(main())
