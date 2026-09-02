from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


T2VA_TEMPLATE = "workflows/comfy-api/t2va-balanced-r2-a5000.json"
FL2VA_TEMPLATE = "workflows/comfy-api/fl2va-first-frame-balanced-r2-a5000.json"


def load_api_template(repo_root: Path, kind: str) -> dict[str, Any]:
    if kind == "t2va":
        path = repo_root / T2VA_TEMPLATE
    elif kind == "fl2va_first_frame":
        path = repo_root / FL2VA_TEMPLATE
    else:
        raise ValueError(f"unsupported workflow kind: {kind}")
    with path.open("r", encoding="utf-8") as f:
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
    """Patch a native ComfyUI API prompt for one Guided Mode Run.

    The returned dictionary is still the ComfyUI API prompt; this function only
    sets approved widget inputs and does not create a second workflow contract.
    """
    api = copy.deepcopy(load_api_template(repo_root, kind))
    width = int(profile["width"])
    height = int(profile["height"])
    duration = float(profile["duration_seconds"])
    sigma_points = int(profile["sigma_points"])
    common_sampler = {
        "seed": int(seed),
        "sigma_points": sigma_points,
        "video_shift": float(profile["video_shift"]),
        "audio_shift": float(profile["audio_shift"]),
        "accel": str(profile["accel"]),
        "denoise_video": True,
        "cache_dit_rdt": float(profile["cache_dit_rdt"]),
        "cache_dit_mc": int(profile["cache_dit_mc"]),
        "cache_dit_warmup": int(profile["cache_dit_warmup"]),
        "velocity_stride": int(profile["velocity_stride"]),
        "sampler_mode": str(profile["sampler_mode"]),
        "allow_accel_with_res_multistep": bool(profile["allow_accel_with_res_multistep"]),
    }
    if kind == "t2va":
        api["4"]["inputs"].update({"aspect_ratio": profile["aspect_ratio"], "duration_seconds": duration, "width": width, "height": height})
        api["5"]["inputs"]["prompt"] = prompt
        api["7"]["inputs"].update(common_sampler)
        api["10"]["inputs"]["filename_prefix"] = filename_prefix
    elif kind == "fl2va_first_frame":
        if not first_frame_name:
            raise ValueError("FL2VA first-frame workflow requires an uploaded first frame")
        api["4"]["inputs"]["image"] = first_frame_name
        api["6"]["inputs"].update({"aspect_ratio": profile["aspect_ratio"], "duration_seconds": duration, "width": width, "height": height})
        api["7"]["inputs"]["prompt"] = prompt
        api["9"]["inputs"].update(common_sampler)
        api["12"]["inputs"]["filename_prefix"] = filename_prefix
    else:  # pragma: no cover - guarded above
        raise ValueError(kind)
    return api


def workflow_summary(api_prompt: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_count": len(api_prompt),
        "class_types": sorted({str(v.get("class_type")) for v in api_prompt.values() if isinstance(v, dict)}),
        "save_nodes": [node_id for node_id, node in api_prompt.items() if node.get("class_type") == "SaveVideo"],
    }
