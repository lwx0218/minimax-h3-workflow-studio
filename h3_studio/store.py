from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

PENDING = "pending"
SUBMITTING = "submitting"
QUEUED = "queued"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"

TERMINAL_STATUSES = {COMPLETED, FAILED, CANCELLED}
ACTIVE_STATUSES = {SUBMITTING, QUEUED, RUNNING}  # holds a worker
ALL_STATUSES = TERMINAL_STATUSES | ACTIVE_STATUSES | {PENDING}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_utc(value: str) -> float | None:
    try:
        return time.mktime(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
    except Exception:  # noqa: BLE001
        return None


class RunStore:
    """Run records: one JSON file per Run, mirrored in memory.

    Disk is the source of truth across restarts; the in-memory index keeps
    request handling from re-reading every run.json on each poll.
    """

    def __init__(self, run_root: Path):
        self.run_root = run_root
        self.run_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._records: dict[str, dict[str, Any]] = {}
        for path in self.run_root.glob("*/run.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._records[str(data["run_id"])] = data
            except Exception:  # noqa: BLE001
                continue

    def run_dir(self, run_id: str) -> Path:
        return self.run_root / run_id

    def write(self, record: dict[str, Any]) -> None:
        run_id = str(record["run_id"])
        record["updated_at"] = utc_now()
        path = self.run_dir(run_id) / "run.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        with self._lock:
            self._records[run_id] = record

    def read(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            if run_id not in self._records:
                raise KeyError(run_id)
            return json.loads(json.dumps(self._records[run_id]))

    def update(self, run_id: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            record = self.read(run_id)
            if all(record.get(k) == v for k, v in fields.items()):
                return record
            record.update(fields)
            self.write(record)
            return record

    def _sorted(self) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(self._records.values(), key=lambda r: str(r.get("created_at", "")), reverse=True)

    def list_by_status(self, statuses: set[str]) -> list[dict[str, Any]]:
        return [json.loads(json.dumps(r)) for r in self._sorted() if r.get("status") in statuses]

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return [summary(r) for r in self._sorted()[:limit]]


def summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record.get("run_id"),
        "kind": record.get("kind"),
        "status": record.get("status"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "completed_at": record.get("completed_at"),
        "profile": (record.get("profile") or {}).get("name"),
        "prompt_preview": str((record.get("inputs") or {}).get("prompt", ""))[:120],
        "seed": (record.get("inputs") or {}).get("seed"),
        "prompt_id": record.get("prompt_id"),
        "client_id": record.get("client_id"),
        "worker": (record.get("worker") or {}).get("id"),
        "queue_position": record.get("queue_position"),
        "progress": record.get("progress"),
        "failure_reason": record.get("failure_reason"),
        "artifacts": [
            {"artifact_id": a.get("artifact_id"), "filename": a.get("filename"), "download_url": a.get("download_url")}
            for a in record.get("artifacts", [])
        ],
        "timing": record.get("timing"),
    }
