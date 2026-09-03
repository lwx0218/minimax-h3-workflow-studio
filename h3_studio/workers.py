from __future__ import annotations

import json
import threading
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .comfy import ComfyClient, flatten_history_outputs
from .store import RunStore, utc_now

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
ACTIVE_STATUSES = {"submitting", "queued", "running"}


class NoWorkerAvailable(RuntimeError):
    def __init__(self, reason: str, pool_status: dict[str, Any]):
        super().__init__(reason)
        self.reason = reason
        self.pool_status = pool_status


@dataclass(frozen=True)
class WorkerSpec:
    id: str
    gpu: str
    host: str
    port: int
    url: str
    output_namespace: str
    temp_namespace: str
    log_namespace: str

    @classmethod
    def from_doc(cls, item: dict[str, Any]) -> "WorkerSpec":
        raw_url = str(item.get("url") or "").rstrip("/")
        parsed = urllib.parse.urlparse(raw_url) if raw_url else None
        parsed_port = None
        if parsed:
            if parsed.scheme not in {"http", "https"}:
                raise ValueError(f"worker {item.get('id', '<unknown>')} URL must use http or https")
            try:
                parsed_port = parsed.port
            except ValueError as exc:
                raise ValueError(f"worker {item.get('id', '<unknown>')} URL must include a valid port") from exc
            if parsed_port is None:
                raise ValueError(f"worker {item.get('id', '<unknown>')} URL must include a port")
        host = str(item.get("host") or (parsed.hostname if parsed else None) or "127.0.0.1")
        raw_port = item.get("port")
        port = int(raw_port if raw_port not in (None, "") else (parsed_port or 0))
        if parsed_port is not None and raw_port not in (None, "") and port != parsed_port:
            raise ValueError(f"worker {item.get('id', '<unknown>')} URL port and port field disagree")
        if port <= 0 or port > 65535:
            raise ValueError(f"worker {item.get('id', '<unknown>')} must define a valid port or URL with port")
        url = raw_url or f"http://{host}:{port}"
        worker_id = str(item.get("id") or f"worker-gpu{item.get('gpu', port)}")
        return cls(
            id=worker_id,
            gpu=str(item.get("gpu", "")),
            host=host,
            port=port,
            url=url,
            output_namespace=str(item.get("output_namespace") or worker_id),
            temp_namespace=str(item.get("temp_namespace") or worker_id),
            log_namespace=str(item.get("log_namespace") or worker_id),
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "gpu": self.gpu,
            "host": self.host,
            "port": self.port,
            "url": self.url,
            "output_namespace": self.output_namespace,
            "temp_namespace": self.temp_namespace,
            "log_namespace": self.log_namespace,
        }


def load_worker_pool_doc(repo_root: Path, fallback_url: str) -> dict[str, Any]:
    path = repo_root / "config" / "worker-pool.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "safe_concurrent_runs": 1,
        "host_ram_abort_gib": 230,
        "host_ram_hard_gib": 235,
        "assignment_policy": "single_worker_fail_closed",
        "workers": [{"id": "worker-gpu0", "gpu": "0", "url": fallback_url}],
    }


def host_memory_status() -> dict[str, Any]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, rest = line.split(":", 1)
            values[key] = int(rest.strip().split()[0]) * 1024
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", 0)
        used = max(total - available, 0)
        gib = 1024**3
        return {
            "total_gib": round(total / gib, 3),
            "available_gib": round(available / gib, 3),
            "used_gib": round(used / gib, 3),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


class WorkerPool:
    """Thin Worker coordination for Replica Execution.

    The pool does not inspect or execute ComfyUI graphs. It chooses one healthy
    ComfyUI Worker for an independent Run, records the lease in Run metadata,
    and refuses submissions when the measured safety envelope is full.
    """

    def __init__(self, pool_doc: dict[str, Any], store: RunStore):
        self.pool_doc = pool_doc
        self.store = store
        self.safe_concurrent_runs = int(pool_doc.get("safe_concurrent_runs", 1))
        self.host_ram_abort_gib = float(pool_doc.get("host_ram_abort_gib", 230))
        self.host_ram_hard_gib = float(pool_doc.get("host_ram_hard_gib", 235))
        self.assignment_policy = str(pool_doc.get("assignment_policy", "least_recent_healthy_idle_fail_closed"))
        self.workers = [WorkerSpec.from_doc(item) for item in pool_doc.get("workers", [])]
        if not self.workers:
            raise ValueError("worker pool must define at least one worker")
        self._lock = threading.Lock()
        self._last_assigned: dict[str, float] = {}
        self._reservations: dict[str, str] = {}

    def client(self, worker: WorkerSpec | dict[str, Any]) -> ComfyClient:
        url = worker.url if isinstance(worker, WorkerSpec) else str(worker["url"])
        return ComfyClient(url)

    def active_runs(self) -> list[dict[str, Any]]:
        return self.store.list_by_status(ACTIVE_STATUSES)

    def worker_for_record(self, record: dict[str, Any]) -> WorkerSpec:
        worker = record.get("worker") or {}
        worker_id = worker.get("id")
        for spec in self.workers:
            if spec.id == worker_id:
                return spec
        url = worker.get("url")
        for spec in self.workers:
            if spec.url == url:
                return spec
        if url:
            return WorkerSpec.from_doc({"id": worker_id or "external-worker", "gpu": worker.get("gpu", ""), "url": url, "port": 0})
        return self.workers[0]

    def discover(self, *, timeout: float = 3.0) -> list[dict[str, Any]]:
        active = self.active_runs()
        by_worker: dict[str, list[dict[str, Any]]] = {}
        for run in active:
            worker = run.get("worker") or {}
            by_worker.setdefault(str(worker.get("id") or worker.get("url") or "unknown"), []).append(run)
        for worker_id, run_id in self._reservations.items():
            by_worker.setdefault(worker_id, []).append({"run_id": run_id, "status": "reserved", "worker": {"id": worker_id}})
        docs = []
        for spec in self.workers:
            item = spec.as_record()
            item["active_runs"] = [r.get("run_id") for r in by_worker.get(spec.id, [])]
            item["busy"] = bool(item["active_runs"])
            try:
                stats = ComfyClient(spec.url).system_stats()
                item["healthy"] = True
                item["system_stats"] = stats
            except Exception as exc:  # noqa: BLE001
                item["healthy"] = False
                item["error"] = repr(exc)
            docs.append(item)
        return docs

    def status(self, *, include_health: bool = True) -> dict[str, Any]:
        active = self.active_runs()
        reservation_docs = [{"run_id": run_id, "status": "reserved", "worker": {"id": worker_id}} for worker_id, run_id in self._reservations.items()]
        mem = host_memory_status()
        over_abort = bool(mem.get("used_gib", 0) >= self.host_ram_abort_gib) if "used_gib" in mem else False
        over_hard = bool(mem.get("used_gib", 0) >= self.host_ram_hard_gib) if "used_gib" in mem else False
        workers = self.discover() if include_health else [w.as_record() for w in self.workers]
        return {
            "schema_version": 1,
            "worker_count": len(self.workers),
            "safe_concurrent_runs": self.safe_concurrent_runs,
            "active_run_count": len(active) + len(reservation_docs),
            "active_runs": [{"run_id": r.get("run_id"), "status": r.get("status"), "worker": r.get("worker")} for r in active] + reservation_docs,
            "host_memory": mem,
            "host_ram_abort_gib": self.host_ram_abort_gib,
            "host_ram_hard_gib": self.host_ram_hard_gib,
            "host_ram_over_abort": over_abort,
            "host_ram_over_hard": over_hard,
            "assignment_policy": self.assignment_policy,
            "workers": workers,
        }

    def acquire(self, run_id: str) -> WorkerSpec:
        with self._lock:
            pool_status = self.status(include_health=True)
            if "used_gib" not in pool_status.get("host_memory", {}):
                raise NoWorkerAvailable("host RAM status unavailable", pool_status)
            if pool_status.get("host_ram_over_hard"):
                raise NoWorkerAvailable("host RAM hard line reached", pool_status)
            if pool_status["host_ram_over_abort"]:
                raise NoWorkerAvailable("host RAM abort line reached", pool_status)
            if int(pool_status["active_run_count"]) >= self.safe_concurrent_runs:
                raise NoWorkerAvailable("safe concurrent Run limit reached", pool_status)
            candidates = [w for w in pool_status["workers"] if w.get("healthy") and not w.get("busy")]
            if not candidates:
                raise NoWorkerAvailable("no healthy idle Worker available", pool_status)
            candidates.sort(key=lambda w: self._last_assigned.get(str(w["id"]), 0.0))
            chosen_id = str(candidates[0]["id"])
            self._last_assigned[chosen_id] = time.monotonic()
            self._reservations[chosen_id] = run_id
            for spec in self.workers:
                if spec.id == chosen_id:
                    return spec
            raise NoWorkerAvailable(f"selected Worker {chosen_id} is not configured", pool_status)

    def release(self, run_id: str) -> None:
        with self._lock:
            for worker_id, reserved_run in list(self._reservations.items()):
                if reserved_run == run_id:
                    self._reservations.pop(worker_id, None)

    def recover_stale_runs(self, *, stale_after_s: int = 6 * 3600) -> dict[str, Any]:
        now = time.time()
        changed = []
        health = {w["id"]: w for w in self.discover()}
        for run in self.active_runs():
            updated = str(run.get("updated_at") or run.get("created_at") or "")
            try:
                ts = time.mktime(time.strptime(updated, "%Y-%m-%dT%H:%M:%SZ"))
            except Exception:
                ts = now
            worker_id = str((run.get("worker") or {}).get("id") or "")
            worker = health.get(worker_id)
            age_s = now - ts
            if worker and worker.get("healthy") and run.get("prompt_id"):
                try:
                    hist = self.client(worker).history(str(run["prompt_id"]))
                    entry = hist.get(str(run["prompt_id"]))
                    status = (entry or {}).get("status", {}) if isinstance(entry, dict) else {}
                    if status.get("completed") is True or status.get("status_str") == "success":
                        run["status"] = "completed"
                        client = self.client(worker)
                        artifacts = []
                        for idx, item in enumerate(flatten_history_outputs(entry or {})):
                            if str(item.get("filename", "")).lower().endswith((".mp4", ".webm", ".mkv", ".mov")):
                                artifacts.append({"artifact_id": f"a{idx}", **item, "view_url": client.view_url(item)})
                        run["artifacts"] = artifacts
                        run["history"] = entry
                        run["recovered_at"] = utc_now()
                        run["updated_at"] = utc_now()
                        self.store.write(run)
                        changed.append(run.get("run_id"))
                        continue
                    if status.get("status_str") == "error":
                        run["status"] = "failed"
                        run["failure_reason"] = "recovered terminal ComfyUI error"
                        run["recovered_at"] = utc_now()
                        run["updated_at"] = utc_now()
                        self.store.write(run)
                        changed.append(run.get("run_id"))
                        continue
                except Exception:  # noqa: BLE001
                    pass
            if age_s >= stale_after_s and (not worker or not worker.get("healthy") or run.get("status") in ACTIVE_STATUSES):
                run["status"] = "failed"
                run["failure_reason"] = "stale active Run exceeded recovery window"
                run["recovered_at"] = utc_now()
                run["updated_at"] = utc_now()
                self.store.write(run)
                changed.append(run.get("run_id"))
        return {"recovered": changed, "count": len(changed)}
