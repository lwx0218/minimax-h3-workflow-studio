#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


def multipart(fields: dict[str, str], files: dict[str, Path] | None = None) -> tuple[bytes, str]:
    boundary = "----h3studioe2e" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for k, v in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for k, path in (files or {}).items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{path.name}\"\r\nContent-Type: image/png\r\n\r\n".encode())
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
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


def wait_run(base: str, run_id: str, timeout_s: int) -> dict[str, Any]:
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        run = get_json(base.rstrip("/") + "/api/runs/" + urllib.parse.quote(run_id), timeout=60)
        print(json.dumps({"run_id": run_id, "status": run.get("status"), "prompt_id": run.get("prompt_id"), "artifacts": len(run.get("artifacts", []))}, ensure_ascii=False))
        if run.get("status") in {"completed", "failed", "cancelled"}:
            return run
        time.sleep(5)
    raise TimeoutError(run_id)


def run_capture(cmd: list[str], timeout_s: int) -> dict[str, Any]:
    cp = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s)
    return {"cmd": cmd, "returncode": cp.returncode, "stdout": cp.stdout[-4000:], "stderr": cp.stderr[-4000:]}


def validate_media(ffprobe: Path, ffmpeg: Path, media: Path, width: int, height: int, frames: int) -> dict[str, Any]:
    probe = json.loads(subprocess.check_output([str(ffprobe), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(media)], text=True, timeout=60))
    video = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    audio = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
    decode = run_capture([str(ffmpeg), "-v", "error", "-i", str(media), "-f", "null", "-"], 300)
    black = run_capture([str(ffmpeg), "-hide_banner", "-i", str(media), "-vf", "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"], 300)
    silence = run_capture([str(ffmpeg), "-hide_banner", "-i", str(media), "-af", "silencedetect=n=-50dB:d=0.5", "-vn", "-f", "null", "-"], 300)
    ok = bool(video and audio and int(video[0].get("width", 0)) == width and int(video[0].get("height", 0)) == height and int(video[0].get("nb_frames", frames)) == frames and int(audio[0].get("channels", 0)) == 2 and decode["returncode"] == 0 and "black_start" not in black["stderr"] and "silence_start" not in silence["stderr"])
    return {"ok": ok, "video": video[:1], "audio": audio[:1], "decode": decode, "blackdetect": black, "silencedetect": silence}


def write_sample_png(path: Path) -> None:
    # 864x480 PNG created with Pillow when available; fallback is a 1x1 valid PNG.
    try:
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (864, 480), (24, 30, 48))
        d = ImageDraw.Draw(im)
        d.rectangle([80, 80, 784, 400], outline=(180, 210, 255), width=6)
        d.ellipse([340, 150, 524, 334], fill=(230, 170, 90))
        d.text((120, 420), "H3 Studio FL2VA first frame", fill=(240, 240, 255))
        im.save(path)
    except Exception:
        path.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de0000000c49444154789c63606060000000040001f61738550000000049454e44ae426082"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Submit R3 T2VA and FL2VA through the Studio product API and validate returned media")
    ap.add_argument("--studio-url", default="http://127.0.0.1:30210")
    ap.add_argument("--ffmpeg", type=Path, required=True)
    ap.add_argument("--ffprobe", type=Path, required=True)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--out", type=Path, default=Path("var/logs/r3-single-worker-product/product-e2e-result.json"))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    media_dir = args.out.parent / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    sample = media_dir / "fl2va-first-frame.png"
    write_sample_png(sample)
    prompt = (
        "A five-second cinematic 16:9 shot of a small paper boat gliding through "
        "a rain-lit city gutter at night. Reflections ripple across the water, a "
        "distant train passes, and the ambient rain and wheel noise stay synchronized "
        "with the movement. Natural camera motion, no subtitles, no logos."
    )
    results = []
    for kind, seed, files in (("t2va", "42", None), ("fl2va_first_frame", "43", {"first_frame": sample})):
        submit = post_form(args.studio_url, {"kind": kind, "profile": "balanced-r2-a5000", "prompt": prompt, "seed": seed}, files)
        run = wait_run(args.studio_url, submit["run_id"], args.timeout)
        if run.get("status") != "completed" or not run.get("artifacts"):
            results.append({"kind": kind, "submit": submit, "run": run, "ok": False})
            continue
        art = run["artifacts"][0]
        media_path = media_dir / f"{kind}.mp4"
        with urllib.request.urlopen(args.studio_url.rstrip("/") + art["download_url"], timeout=300) as resp:
            media_path.write_bytes(resp.read())
        validation = validate_media(args.ffprobe, args.ffmpeg, media_path, 864, 480, 124)
        results.append({"kind": kind, "submit": submit, "run_id": run["run_id"], "artifact": art, "media": str(media_path), "validation": validation, "ok": validation["ok"]})
    doc = {"ok": all(r.get("ok") for r in results), "results": results}
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(args.out), "ok": doc["ok"]}, ensure_ascii=False, indent=2))
    return 0 if doc["ok"] else 5


if __name__ == "__main__":
    raise SystemExit(main())
