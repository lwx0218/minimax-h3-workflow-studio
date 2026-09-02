from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class RunStore:
    def __init__(self, run_root: Path):
        self.run_root = run_root
        self.run_root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        return self.run_root / run_id

    def run_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "run.json"

    def write(self, record: dict[str, Any]) -> None:
        run_id = str(record["run_id"])
        path = self.run_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def read(self, run_id: str) -> dict[str, Any]:
        path = self.run_path(run_id)
        if not path.exists():
            raise KeyError(run_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def list_recent(self, limit: int = 25) -> list[dict[str, Any]]:
        records = []
        for path in sorted(self.run_root.glob("*/run.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                records.append({
                    "run_id": data.get("run_id"),
                    "kind": data.get("kind"),
                    "status": data.get("status"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "prompt_id": data.get("prompt_id"),
                    "artifacts": data.get("artifacts", []),
                })
            except Exception:  # noqa: BLE001
                continue
        return records

    def update(self, run_id: str, **fields: Any) -> dict[str, Any]:
        record = self.read(run_id)
        record.update(fields)
        record["updated_at"] = utc_now()
        self.write(record)
        return record
