from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class StudioConfig:
    repo_root: Path
    studio_host: str
    studio_port: int
    worker_host: str
    worker_port: int
    worker_url: str
    worker_pool: dict[str, Any]
    data_root: Path
    run_root: Path
    upload_root: Path
    runtime_lock: dict[str, Any]
    asset_manifest: dict[str, Any]
    profiles: dict[str, Any]
    default_profile: str

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> "StudioConfig":
        root = (repo_root or REPO_ROOT).resolve()
        runtime_lock = load_json(root / "config" / "runtime-lock.json")
        asset_manifest = load_json(root / "config" / "asset-manifest.json")
        profile_doc = load_json(root / "config" / "generation-profiles.json")
        net = runtime_lock.get("network_defaults", {})
        studio_host = os.environ.get("H3_STUDIO_HOST", str(net.get("studio_host", "127.0.0.1")))
        studio_port = int(os.environ.get("H3_STUDIO_PORT", str(net.get("studio_port", 30210))))
        worker_host = os.environ.get("H3_WORKER_HOST", str(net.get("worker_host", "127.0.0.1")))
        worker_port = int(os.environ.get("H3_WORKER_PORT", str(net.get("worker_port", 30211))))
        worker_url = os.environ.get("H3_WORKER_URL", f"http://{worker_host}:{worker_port}").rstrip("/")
        pool_path = Path(os.environ.get("H3_WORKER_POOL_CONFIG", str(root / "config" / "worker-pool.json")))
        if not pool_path.is_absolute():
            pool_path = root / pool_path
        if pool_path.exists():
            worker_pool = load_json(pool_path)
        else:
            worker_pool = {"schema_version": 1, "safe_concurrent_runs": 1, "workers": [{"id": "worker-gpu0", "gpu": "0", "url": worker_url}]}
        data_root = Path(os.environ.get("H3_STUDIO_DATA", str(root / "var" / "h3-studio"))).resolve()
        run_root = data_root / "runs"
        upload_root = data_root / "uploads"
        return cls(
            repo_root=root,
            studio_host=studio_host,
            studio_port=studio_port,
            worker_host=worker_host,
            worker_port=worker_port,
            worker_url=worker_url,
            worker_pool=worker_pool,
            data_root=data_root,
            run_root=run_root,
            upload_root=upload_root,
            runtime_lock=runtime_lock,
            asset_manifest=asset_manifest,
            profiles=profile_doc["profiles"],
            default_profile=str(profile_doc["default_profile"]),
        )

    def profile(self, name: str | None) -> dict[str, Any]:
        key = name or self.default_profile
        if key not in self.profiles:
            raise ValueError(f"unknown Generation Profile: {key}")
        return dict(self.profiles[key]) | {"name": key}

    def ensure_dirs(self) -> None:
        for path in (self.data_root, self.run_root, self.upload_root):
            path.mkdir(parents=True, exist_ok=True)
