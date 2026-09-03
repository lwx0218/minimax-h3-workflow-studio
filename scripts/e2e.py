#!/usr/bin/env python3
"""End-to-end checks against a running Studio, with media validation.

    python3 scripts/e2e.py concurrent --count 2       # N independent T2VA runs at once
    python3 scripts/e2e.py profiles                   # draft/balanced/final one after another
    python3 scripts/e2e.py fl2va                      # one FL2VA run with a generated first frame

Needs ffmpeg/ffprobe (default: var/cache/tools/ffprobe-static-extracted/). Results and
downloaded media go to var/logs/e2e/. Use `concurrent --count 3/4/5` while watching
host memory to decide whether safe_concurrent_runs can be raised.
"""
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

PROMPTS = [
    "A five-second cinematic 16:9 shot of a paper boat racing through neon rainwater at night, train lights reflected in ripples, synchronized stereo rain and wheel ambience, no subtitles, no logos.",
    "A five-second cinematic 16:9 shot of a tiny lantern floating across a moonlit harbor, gulls and soft bell tones synchronized in stereo, natural camera motion, no subtitles, no logos.",
    "A five-second cinematic 16:9 shot of a clockwork firefly crossing a rainy window at night, reflections and soft mechanical wing sounds synchronized in stereo, no subtitles, no logos.",
    "A five-second cinematic 16:9 shot of autumn leaves spiralling down a stone stairway, footsteps and wind in stereo, natural handheld motion, no subtitles, no logos.",
    "A five-second cinematic 16:9 shot of a kettle whistling on a wood stove in a cabin, crackling fire and rising steam, stereo ambience, no subtitles, no logos.",
]


def multipart(fields: dict[str, str], files: dict[str, Path] | None = None) -> tuple[bytes, str]:
    boundary = "----h3e2e" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for k, v in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for k, path in (files or {}).items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{path.name}\"\r\nContent-Type: image/png\r\n\r\n".encode())
        chunks.append(path.read_bytes() + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def post_form(base: str, fields: dict[str, str], files: dict[str, Path] | None = None) -> dict[str, Any]:
    body, boundary = multipart(fields, files)
    req = urllib.request.Request(base.rstrip("/") + "/api/runs", data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def get_json(url: str, timeout: float = 60.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def run_capture(cmd: list[str], timeout_s: int) -> dict[str, Any]:
    cp = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s)
    return {"cmd": cmd, "returncode": cp.returncode, "stdout": cp.stdout[-4000:], "stderr": cp.stderr[-4000:]}


def host_memory_status() -> dict[str, Any]:
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, rest = line.split(":", 1)
            values[key] = int(rest.strip().split()[0]) * 1024
        gib = 1024**3
        total, avail = values.get("MemTotal", 0), values.get("MemAvailable", 0)
        return {"total_gib": round(total / gib, 3), "used_gib": round(max(total - avail, 0) / gib, 3)}
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


def gpu_status() -> list[dict[str, Any]]:
    try:
        cp = run_capture(["nvidia-smi", "--query-gpu=index,memory.used,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"], 30)
    except Exception:  # noqa: BLE001
        return []
    rows = []
    if cp.get("returncode") == 0:
        for line in str(cp.get("stdout", "")).splitlines():
            p = [x.strip() for x in line.split(",")]
            if len(p) >= 4:
                rows.append({"index": p[0], "memory_used_mib": int(p[1]), "utilization_gpu_pct": int(p[2]), "temperature_c": int(p[3])})
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
        for sample in self.samples:
            for gpu in sample.get("gpus", []):
                peak_gpu[str(gpu["index"])] = max(peak_gpu.get(str(gpu["index"]), 0), int(gpu.get("memory_used_mib", 0)))
        return {"sample_count": len(self.samples), "peak_host_used_gib": peak_host, "peak_gpu_memory_used_mib": peak_gpu}


def validate_media(ffprobe: Path, ffmpeg: Path, media: Path, width: int, height: int, frames: int) -> dict[str, Any]:
    probe = json.loads(subprocess.check_output([str(ffprobe), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(media)], text=True, timeout=60))
    video = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    audio = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
    decode = run_capture([str(ffmpeg), "-v", "error", "-i", str(media), "-f", "null", "-"], 300)
    black = run_capture([str(ffmpeg), "-hide_banner", "-i", str(media), "-vf", "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"], 300)
    silence = run_capture([str(ffmpeg), "-hide_banner", "-i", str(media), "-af", "silencedetect=n=-50dB:d=0.5", "-vn", "-f", "null", "-"], 300)
    ok = bool(video and audio and int(video[0].get("width", 0)) == width and int(video[0].get("height", 0)) == height
              and int(video[0].get("nb_frames", frames)) == frames and int(audio[0].get("channels", 0)) == 2
              and decode["returncode"] == 0 and "black_start" not in black["stderr"] and "silence_start" not in silence["stderr"])
    return {"ok": ok, "video": video[:1], "audio": audio[:1], "decode_rc": decode["returncode"], "black": "black_start" in black["stderr"], "silence": "silence_start" in silence["stderr"]}


def write_sample_png(path: Path) -> None:
    try:
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (864, 480), (24, 30, 48))
        d = ImageDraw.Draw(im)
        d.rectangle([80, 80, 784, 400], outline=(180, 210, 255), width=6)
        d.ellipse([340, 150, 524, 334], fill=(230, 170, 90))
        im.save(path)
    except Exception:  # noqa: BLE001
        path.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de0000000c49444154789c63606060000000040001f61738550000000049454e44ae426082"))


def wait_run(base: str, run_id: str, timeout_s: int) -> dict[str, Any]:
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        run = get_json(base.rstrip("/") + "/api/runs/" + urllib.parse.quote(run_id))
        print(json.dumps({"run_id": run_id, "status": run.get("status"), "worker": (run.get("worker") or {}).get("id"), "queue_position": run.get("queue_position")}, ensure_ascii=False), flush=True)
        if run.get("status") in {"completed", "failed", "cancelled"}:
            return run
        time.sleep(5)
    raise TimeoutError(run_id)


def submit_and_wait(args: argparse.Namespace, label: str, fields: dict[str, str], files: dict[str, Path] | None, out: dict[str, Any]) -> None:
    t0 = time.time()
    try:
        submit = post_form(args.studio_url, fields, files)
        run = wait_run(args.studio_url, submit["run_id"], args.timeout)
    except Exception as exc:  # noqa: BLE001
        out[label] = {"label": label, "ok": False, "error": repr(exc)}
        return
    result: dict[str, Any] = {"label": label, "run": run, "submitted_at_unix": t0, "terminal_at_unix": time.time(), "ok": False}
    if run.get("status") == "completed" and run.get("artifacts"):
        art = run["artifacts"][0]
        media = args.media_dir / f"{label}-{run['run_id']}.mp4"
        with urllib.request.urlopen(args.studio_url.rstrip("/") + art["download_url"], timeout=300) as resp:
            media.write_bytes(resp.read())
        profile = run.get("profile") or {}
        validation = validate_media(args.ffprobe, args.ffmpeg, media, int(profile.get("width", 864)), int(profile.get("height", 480)), int(profile.get("expected_frame_count", 124)))
        result.update({"media": str(media), "validation": validation, "ok": validation["ok"]})
    out[label] = result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["concurrent", "profiles", "fl2va"])
    ap.add_argument("--studio-url", default="http://127.0.0.1:30210")
    ap.add_argument("--count", type=int, default=2, help="concurrent: number of simultaneous runs")
    ap.add_argument("--profile", default="balanced")
    ap.add_argument("--profiles", default="draft,balanced,final")
    ap.add_argument("--ffmpeg", type=Path, default=Path("var/cache/tools/ffprobe-static-extracted/ffmpeg"))
    ap.add_argument("--ffprobe", type=Path, default=Path("var/cache/tools/ffprobe-static-extracted/ffprobe"))
    ap.add_argument("--timeout", type=int, default=5400)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    args.out = args.out or Path(f"var/logs/e2e/{args.mode}-{time.strftime('%Y%m%d-%H%M%S')}.json")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.media_dir = args.out.parent / "media"
    args.media_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}
    pool_before = get_json(args.studio_url.rstrip("/") + "/api/workers")
    with ResourceMonitor() as monitor:
        if args.mode == "concurrent":
            threads = [threading.Thread(target=submit_and_wait, args=(args, f"run_{i}", {"kind": "t2va", "profile": args.profile, "prompt": PROMPTS[i % len(PROMPTS)], "seed": str(200 + i)}, None, results), daemon=True) for i in range(args.count)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        elif args.mode == "profiles":
            for i, profile in enumerate(p.strip() for p in args.profiles.split(",") if p.strip()):
                submit_and_wait(args, profile, {"kind": "t2va", "profile": profile, "prompt": PROMPTS[2], "seed": str(300 + i)}, None, results)
        else:
            sample = args.media_dir / "first-frame.png"
            write_sample_png(sample)
            submit_and_wait(args, "fl2va", {"kind": "fl2va_first_frame", "profile": args.profile, "prompt": PROMPTS[0], "seed": "43"}, {"first_frame": sample}, results)
    pool_after = get_json(args.studio_url.rstrip("/") + "/api/workers")
    workers = [((r.get("run") or {}).get("worker") or {}).get("id") for r in results.values()]
    doc = {
        "mode": args.mode,
        "results": results,
        "workers": workers,
        "distinct_workers": len(set(w for w in workers if w)),
        "resource_summary": monitor.summary(),
        "resource_samples": monitor.samples,
        "pool_before": pool_before,
        "pool_after": pool_after,
        "ok": bool(results) and all(r.get("ok") for r in results.values()),
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(args.out), "ok": doc["ok"], "workers": workers, "peak_host_used_gib": doc["resource_summary"]["peak_host_used_gib"]}, ensure_ascii=False, indent=2))
    return 0 if doc["ok"] else 5


if __name__ == "__main__":
    raise SystemExit(main())
