#!/usr/bin/env python3
"""Create reproducible independent ffprobe/decode/signal evidence for an R1 MP4."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=600)


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--media", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--ffprobe", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True, type=Path)
    args = parser.parse_args()

    media = args.media.resolve()
    evidence_root = args.evidence_root.resolve()
    ffprobe = args.ffprobe.resolve()
    ffmpeg = args.ffmpeg.resolve()
    project_var = (ROOT / "var").resolve()
    for name, path in (("media", media), ("evidence_root", evidence_root), ("ffprobe", ffprobe), ("ffmpeg", ffmpeg)):
        if not path.is_relative_to(project_var):
            raise ValueError(f"{name} must resolve under project var/: {path}")
    if not media.is_file():
        raise FileNotFoundError(media)
    evidence_root.mkdir(parents=True, exist_ok=True)

    commands = {
        "ffprobe": [relative(ffprobe), "-v", "error", "-show_streams", "-show_format", "-of", "json", relative(media)],
        "decode": [relative(ffmpeg), "-v", "error", "-i", relative(media), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
        "audio_stats": [relative(ffmpeg), "-hide_banner", "-nostats", "-i", relative(media), "-map", "0:a:0", "-af", "astats=metadata=0:reset=0", "-f", "null", "-"],
        "blackdetect": [relative(ffmpeg), "-hide_banner", "-nostats", "-i", relative(media), "-map", "0:v:0", "-vf", "blackdetect=d=0.25:pix_th=0.10", "-an", "-f", "null", "-"],
        "silencedetect": [relative(ffmpeg), "-hide_banner", "-nostats", "-i", relative(media), "-map", "0:a:0", "-af", "silencedetect=n=-50dB:d=0.5", "-vn", "-f", "null", "-"],
        "contact_sheet": [relative(ffmpeg), "-y", "-v", "error", "-i", relative(media), "-vf", "fps=1,scale=448:-2,tile=3x2", "-frames:v", "1", relative(evidence_root / "contact-sheet.jpg")],
    }
    results = {name: run(command) for name, command in commands.items()}
    (evidence_root / "ffprobe-independent.json").write_text(results["ffprobe"].stdout, encoding="utf-8")
    for name in ("decode", "audio_stats", "blackdetect", "silencedetect"):
        (evidence_root / f"{name.replace('_', '-')}.stderr.txt").write_text(results[name].stderr, encoding="utf-8")

    probe_data = json.loads(results["ffprobe"].stdout) if results["ffprobe"].returncode == 0 else {}
    streams = probe_data.get("streams", [])
    tool_versions = {}
    for name, tool in (("ffprobe", ffprobe), ("ffmpeg", ffmpeg)):
        version = run([relative(tool), "-version"])
        tool_versions[name] = {"command": [relative(tool), "-version"], "exit_code": version.returncode, "first_line": version.stdout.splitlines()[0] if version.stdout else ""}

    evidence = {
        "schema_version": 1,
        "created_at": utc_now(),
        "input": {
            "path": relative(media),
            "bytes": media.stat().st_size,
            "sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
        },
        "tool_versions": tool_versions,
        "checks": {
            name: {
                "command": command,
                "exit_code": results[name].returncode,
                "stderr_path": None if name == "ffprobe" else relative(evidence_root / f"{name.replace('_', '-')}.stderr.txt") if name != "contact_sheet" else None,
            }
            for name, command in commands.items()
        },
        "stream_counts": {
            "video": sum(stream.get("codec_type") == "video" for stream in streams),
            "audio": sum(stream.get("codec_type") == "audio" for stream in streams),
        },
        "black_segment_count": len(re.findall(r"black_start", results["blackdetect"].stderr)),
        "silence_segment_count": len(re.findall(r"silence_start", results["silencedetect"].stderr)),
        "contact_sheet": relative(evidence_root / "contact-sheet.jpg"),
    }
    output = evidence_root / "independent-media-verification.json"
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    required = ("ffprobe", "decode", "audio_stats", "blackdetect", "silencedetect", "contact_sheet")
    passed = all(results[name].returncode == 0 for name in required)
    passed = passed and evidence["stream_counts"] == {"video": 1, "audio": 1}
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
