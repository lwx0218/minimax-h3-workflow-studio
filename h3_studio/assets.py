from __future__ import annotations

import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Any


MAX_HEADER = 100_000_000


def safetensors_header(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        raw = f.read(8)
        if len(raw) != 8:
            raise ValueError(f"{path.name}: missing safetensors header length")
        size = struct.unpack("<Q", raw)[0]
        if size <= 0 or size > MAX_HEADER:
            raise ValueError(f"{path.name}: invalid safetensors header length {size}")
        header = f.read(size)
        try:
            parsed = json.loads(header.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"{path.name}: invalid safetensors JSON header: {exc}") from exc
    return {"header_len": size, "tensor_count": len([k for k in parsed if k != "__metadata__"])}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(path: Path) -> str:
    """Hash a sidecar tree by relative file path, size and file SHA-256."""
    h = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if not item.is_file() or item.name.endswith((".safetensors", ".bak")):
            continue
        rel = item.relative_to(path).as_posix()
        h.update(rel.encode("utf-8") + b"\0")
        h.update(str(item.stat().st_size).encode("ascii") + b"\0")
        h.update(sha256_file(item).encode("ascii") + b"\n")
    return h.hexdigest()


def validate_assets(manifest: dict[str, Any], *, compute_sha: bool = False) -> dict[str, Any]:
    root_env = manifest.get("asset_root_env", "H3_MODEL_ROOT")
    root_value = os.environ.get(str(root_env), "")
    if not root_value:
        raise RuntimeError(f"{root_env} must point to the external MiniMax-H3 model root")
    root = Path(root_value).expanduser().resolve()
    results = []
    ok = True
    for asset in manifest.get("required_assets", []):
        rel = asset["relative_path"]
        path = root / rel
        item: dict[str, Any] = {"role": asset.get("role"), "relative_path": rel, "exists": path.exists()}
        if not path.exists():
            ok = False
            results.append(item)
            continue
        item["is_dir"] = path.is_dir()
        if path.is_file():
            item["bytes"] = path.stat().st_size
        if asset.get("safetensors_header") == "required":
            try:
                item["safetensors"] = safetensors_header(path)
            except Exception as exc:  # noqa: BLE001
                ok = False
                item["safetensors_error"] = repr(exc)
        expected = asset.get("sha256")
        if expected and compute_sha:
            actual = sha256_tree(path) if path.is_dir() else sha256_file(path)
            item["sha256"] = actual
            item["sha256_ok"] = actual == expected
            ok = ok and bool(item["sha256_ok"])
        results.append(item)
    return {"ok": ok, "asset_root_env": root_env, "asset_root_set": True, "assets": results}
