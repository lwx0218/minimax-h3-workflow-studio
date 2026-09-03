#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from run_r3_product_e2e import get_json, post_form, validate_media
from run_r4_concurrent_e2e import ResourceMonitor, wait_run


def main() -> int:
    ap = argparse.ArgumentParser(description="Run R4 Draft/Balanced/Final profile matrix through the Studio product API")
    ap.add_argument("--studio-url", default="http://127.0.0.1:30210")
    ap.add_argument("--ffmpeg", type=Path, required=True)
    ap.add_argument("--ffprobe", type=Path, required=True)
    ap.add_argument("--timeout", type=int, default=5400)
    ap.add_argument("--profiles", default="draft-r4-a5000,balanced-r2-a5000,final-r4-a5000")
    ap.add_argument("--out", type=Path, default=Path("var/logs/r4-multi-worker-mvp/profile-matrix-result.json"))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    media_dir = args.out.parent / "profile-media"
    media_dir.mkdir(parents=True, exist_ok=True)
    config = get_json(args.studio_url.rstrip("/") + "/api/config", timeout=60)
    prompt = "A five-second cinematic 16:9 shot of a clockwork firefly crossing a rainy window at night, reflections and soft mechanical wing sounds synchronized in stereo, natural camera motion, no subtitles, no logos."
    results: list[dict[str, Any]] = []
    for idx, profile in enumerate([p.strip() for p in args.profiles.split(",") if p.strip()]):
        started = time.time()
        submit = post_form(args.studio_url, {"kind": "t2va", "profile": profile, "prompt": prompt, "seed": str(300 + idx)}, None)
        samples: list[dict[str, Any]] = []
        with ResourceMonitor() as monitor:
            run = wait_run(args.studio_url, submit["run_id"], args.timeout, samples)
        terminal = time.time()
        item: dict[str, Any] = {"profile": profile, "profile_config": config["profiles"].get(profile), "submit": submit, "run": run, "samples": samples, "resource_samples": monitor.samples, "resource_summary": monitor.summary(), "wall_seconds": round(terminal - started, 3), "ok": False}
        if run.get("status") == "completed" and run.get("artifacts"):
            art = run["artifacts"][0]
            media = media_dir / f"{profile}-{run['run_id']}.mp4"
            with urllib.request.urlopen(args.studio_url.rstrip("/") + art["download_url"], timeout=300) as resp:
                media.write_bytes(resp.read())
            validation = validate_media(args.ffprobe, args.ffmpeg, media, 864, 480, 124)
            item.update({"artifact": art, "media": str(media), "validation": validation, "ok": validation["ok"]})
        results.append(item)
    doc = {"schema_version": 1, "profiles": args.profiles, "results": results, "ok": all(r["ok"] for r in results)}
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(args.out), "ok": doc["ok"], "profiles": [{"profile": r["profile"], "ok": r["ok"], "wall_seconds": r["wall_seconds"], "worker": ((r["run"].get("worker") or {}).get("id"))} for r in results]}, ensure_ascii=False, indent=2))
    return 0 if doc["ok"] else 5


if __name__ == "__main__":
    raise SystemExit(main())
