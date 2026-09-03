"""Patch native ComfyUI API workflow templates for one Guided Mode Run.

The templates under workflows/comfy-api/ are the ComfyUI API format exported
from the matching workflows/comfy-ui/ graphs. Only approved widget inputs are
patched here; there is no second workflow contract.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

KINDS = {
    "t2va": {
        "template": "workflows/comfy-api/t2va.json",
        "target": "4",
        "text": "5",
        "sampler": "7",
        "save": "10",
    },
    "fl2va_first_frame": {
        "template": "workflows/comfy-api/fl2va-first-frame.json",
        "image": "4",
        "target": "6",
        "text": "7",
        "sampler": "9",
        "save": "12",
    },
}

SAMPLER_KEYS = (
    "sigma_points", "video_shift", "audio_shift", "accel", "cache_dit_rdt", "cache_dit_mc",
    "cache_dit_warmup", "velocity_stride", "sampler_mode", "allow_accel_with_res_multistep",
)


def load_api_template(repo_root: Path, kind: str) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"unsupported workflow kind: {kind}")
    with (repo_root / KINDS[kind]["template"]).open("r", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(
    repo_root: Path,
    *,
    kind: str,
    profile: dict[str, Any],
    prompt: str,
    seed: int,
    filename_prefix: str,
    first_frame_name: str | None = None,
) -> dict[str, Any]:
    api = copy.deepcopy(load_api_template(repo_root, kind))
    nodes = KINDS[kind]
    api[nodes["target"]]["inputs"].update({
        "aspect_ratio": profile["aspect_ratio"],
        "duration_seconds": float(profile["duration_seconds"]),
        "width": int(profile["width"]),
        "height": int(profile["height"]),
    })
    api[nodes["text"]]["inputs"]["prompt"] = prompt
    sampler = {k: profile[k] for k in SAMPLER_KEYS}
    sampler.update({"seed": int(seed), "denoise_video": True})
    api[nodes["sampler"]]["inputs"].update(sampler)
    api[nodes["save"]]["inputs"]["filename_prefix"] = filename_prefix
    if "image" in nodes:
        if not first_frame_name:
            raise ValueError("FL2VA first-frame workflow requires an uploaded first frame")
        api[nodes["image"]]["inputs"]["image"] = first_frame_name
    return api


def workflow_summary(api_prompt: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_count": len(api_prompt),
        "class_types": sorted({str(v.get("class_type")) for v in api_prompt.values() if isinstance(v, dict)}),
        "save_nodes": [node_id for node_id, node in api_prompt.items() if node.get("class_type") == "SaveVideo"],
    }
