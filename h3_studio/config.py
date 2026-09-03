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


def _resolve(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


@dataclass(frozen=True)
class StudioConfig:
    repo_root: Path
    studio_host: str
    studio_port: int
    runtime_root: Path
    worker_pool: dict[str, Any]
    data_root: Path
    runtime_lock: dict[str, Any]
    asset_manifest: dict[str, Any]
    profiles: dict[str, Any]
    profile_aliases: dict[str, str]
    default_profile: str

    @classmethod
    def from_env(cls, repo_root: Path | None = None, env: dict[str, str] | None = None) -> "StudioConfig":
        env = os.environ if env is None else env
        root = (repo_root or REPO_ROOT).resolve()
        runtime_lock = load_json(root / "config" / "runtime-lock.json")
        asset_manifest = load_json(root / "config" / "asset-manifest.json")
        profile_doc = load_json(root / "config" / "generation-profiles.json")
        net = runtime_lock.get("network_defaults", {})
        pool_path = _resolve(root, env.get("H3_WORKER_POOL_CONFIG", "config/worker-pool.json"))
        return cls(
            repo_root=root,
            studio_host=env.get("H3_STUDIO_HOST", str(net.get("studio_host", "127.0.0.1"))),
            studio_port=int(env.get("H3_STUDIO_PORT", str(net.get("studio_port", 30210)))),
            runtime_root=_resolve(root, env.get("H3_RUNTIME_ROOT", "var/runtime")),
            worker_pool=load_json(pool_path),
            data_root=_resolve(root, env.get("H3_STUDIO_DATA", "var/h3-studio")),
            runtime_lock=runtime_lock,
            asset_manifest=asset_manifest,
            profiles=profile_doc["profiles"],
            profile_aliases=dict(profile_doc.get("aliases", {})),
            default_profile=str(profile_doc["default_profile"]),
        )

    @property
    def run_root(self) -> Path:
        return self.data_root / "runs"

    @property
    def upload_root(self) -> Path:
        return self.data_root / "uploads"

    def profile(self, name: str | None) -> dict[str, Any]:
        key = name or self.default_profile
        key = self.profile_aliases.get(key, key)
        if key not in self.profiles:
            raise ValueError(f"unknown Generation Profile: {name}")
        return dict(self.profiles[key]) | {"name": key}

    def ensure_dirs(self) -> None:
        for path in (self.data_root, self.run_root, self.upload_root):
            path.mkdir(parents=True, exist_ok=True)
