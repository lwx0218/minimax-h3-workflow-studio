"""Worker pool: discovery, health cache and lease bookkeeping.

The pool never inspects or executes ComfyUI graphs. It knows which isolated
ComfyUI worker is healthy, which one currently holds a Run, and whether the
host is inside its measured memory envelope.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .comfy import ComfyClient


class NoWorkerAvailable(RuntimeError):
    def __init__(self, reason: str, pool_status: dict[str, Any] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.pool_status = pool_status or {}


@dataclass(frozen=True)
class WorkerSpec:
    id: str
    gpu: str
    host: str
    port: int

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @classmethod
    def from_doc(cls, item: dict[str, Any], default_host: str = "127.0.0.1") -> "WorkerSpec":
        worker_id = str(item.get("id") or f"worker-gpu{item.get('gpu', '')}")
        try:
            port = int(item.get("port", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"worker {worker_id}: port must be an integer") from exc
        if not 0 < port < 65536:
            raise ValueError(f"worker {worker_id}: port {port} out of range")
        return cls(id=worker_id, gpu=str(item.get("gpu", "")), host=str(item.get("host") or default_host), port=port)

    def as_record(self) -> dict[str, Any]:
        return {"id": self.id, "gpu": self.gpu, "host": self.host, "port": self.port, "url": self.url}


def host_memory_status() -> dict[str, Any]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, rest = line.split(":", 1)
            values[key] = int(rest.strip().split()[0]) * 1024
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", 0)
        gib = 1024**3
        return {
            "total_gib": round(total / gib, 3),
            "available_gib": round(available / gib, 3),
            "used_gib": round(max(total - available, 0) / gib, 3),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


class WorkerPool:
    def __init__(self, pool_doc: dict[str, Any], *, client_factory=ComfyClient, memory_probe=host_memory_status):
        self.doc = pool_doc
        self.safe_concurrent_runs = int(pool_doc.get("safe_concurrent_runs", 1))
        self.host_ram_abort_gib = float(pool_doc.get("host_ram_abort_gib", 230))
        self.host_ram_hard_gib = float(pool_doc.get("host_ram_hard_gib", 235))
        self.health_interval_s = float(pool_doc.get("health_interval_s", 5))
        default_host = str(pool_doc.get("worker_host", "127.0.0.1"))
        self.workers = [WorkerSpec.from_doc(item, default_host) for item in pool_doc.get("workers", [])]
        if not self.workers:
            raise ValueError("worker pool must define at least one worker")
        if len({w.id for w in self.workers}) != len(self.workers):
            raise ValueError("worker ids must be unique")
        if len({(w.host, w.port) for w in self.workers}) != len(self.workers):
            raise ValueError("worker host:port pairs must be unique")
        self._by_id = {w.id: w for w in self.workers}
        self._client_factory = client_factory
        self._memory_probe = memory_probe
        self._lock = threading.Lock()
        self._leases: dict[str, str] = {}  # worker_id -> run_id
        self._last_assigned: dict[str, float] = {}
        self._health: dict[str, dict[str, Any]] = {w.id: {"healthy": False, "checked_at": None} for w in self.workers}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ----- clients / lookup -------------------------------------------------
    def client(self, worker: WorkerSpec | dict[str, Any] | str) -> ComfyClient:
        if isinstance(worker, WorkerSpec):
            return self._client_factory(worker.url)
        if isinstance(worker, str):
            return self._client_factory(self.get(worker).url)
        return self._client_factory(str(worker["url"]))

    def get(self, worker_id: str) -> WorkerSpec:
        if worker_id not in self._by_id:
            raise KeyError(f"unknown worker: {worker_id}")
        return self._by_id[worker_id]

    def worker_for_record(self, record: dict[str, Any]) -> WorkerSpec:
        worker_id = str((record.get("worker") or {}).get("id") or "")
        return self.get(worker_id)

    # ----- health -----------------------------------------------------------
    def check_health(self) -> dict[str, dict[str, Any]]:
        """Probe every worker once (blocking, ~5 s worst case per dead worker)."""
        for spec in self.workers:
            item: dict[str, Any] = {"checked_at": time.time()}
            try:
                stats = self.client(spec).system_stats()
                item.update(healthy=True, system_stats=stats, error=None)
            except Exception as exc:  # noqa: BLE001
                item.update(healthy=False, error=repr(exc))
            with self._lock:
                self._health[spec.id] = item
        return dict(self._health)

    def start_health_thread(self) -> None:
        if self._thread is not None:
            return

        def loop() -> None:
            while not self._stop.is_set():
                try:
                    self.check_health()
                except Exception:  # noqa: BLE001
                    pass
                self._stop.wait(self.health_interval_s)

        self._thread = threading.Thread(target=loop, name="worker-health", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def is_healthy(self, worker_id: str) -> bool:
        with self._lock:
            return bool(self._health.get(worker_id, {}).get("healthy"))

    def first_healthy(self) -> WorkerSpec | None:
        for spec in self.workers:
            if self.is_healthy(spec.id):
                return spec
        return None

    # ----- memory envelope --------------------------------------------------
    def memory_gate(self) -> tuple[dict[str, Any], str | None]:
        mem = self._memory_probe()
        if "used_gib" not in mem:
            return mem, "host RAM status unavailable"
        if mem["used_gib"] >= self.host_ram_hard_gib:
            return mem, "host RAM hard line reached"
        if mem["used_gib"] >= self.host_ram_abort_gib:
            return mem, "host RAM abort line reached"
        return mem, None

    # ----- leases -----------------------------------------------------------
    def leases(self) -> dict[str, str]:
        with self._lock:
            return dict(self._leases)

    def acquire(self, run_id: str) -> WorkerSpec:
        """Lease the least-recently-used healthy idle worker, or raise NoWorkerAvailable."""
        mem, reason = self.memory_gate()
        if reason:
            raise NoWorkerAvailable(reason, {"host_memory": mem})
        with self._lock:
            if len(self._leases) >= self.safe_concurrent_runs:
                raise NoWorkerAvailable("safe concurrent Run limit reached", {"leases": dict(self._leases)})
            candidates = [
                w for w in self.workers
                if w.id not in self._leases and self._health.get(w.id, {}).get("healthy")
            ]
            if not candidates:
                raise NoWorkerAvailable("no healthy idle worker", {"leases": dict(self._leases)})
            candidates.sort(key=lambda w: self._last_assigned.get(w.id, 0.0))
            chosen = candidates[0]
            self._leases[chosen.id] = run_id
            self._last_assigned[chosen.id] = time.monotonic()
            return chosen

    def restore_lease(self, worker_id: str, run_id: str) -> None:
        """Re-attach a lease after restart for a Run that is still active on a worker."""
        with self._lock:
            self._leases[worker_id] = run_id

    def release(self, run_id: str) -> None:
        with self._lock:
            for worker_id, held in list(self._leases.items()):
                if held == run_id:
                    del self._leases[worker_id]

    # ----- status -----------------------------------------------------------
    def status(self) -> dict[str, Any]:
        mem, reason = self.memory_gate()
        with self._lock:
            leases = dict(self._leases)
            health = {k: dict(v) for k, v in self._health.items()}
        workers = []
        for spec in self.workers:
            h = health.get(spec.id, {})
            workers.append({
                **spec.as_record(),
                "healthy": bool(h.get("healthy")),
                "error": h.get("error"),
                "checked_at": h.get("checked_at"),
                "current_run": leases.get(spec.id),
                "gpu_stats": ((h.get("system_stats") or {}).get("devices") or [None])[0],
            })
        return {
            "worker_count": len(self.workers),
            "healthy_count": sum(1 for w in workers if w["healthy"]),
            "safe_concurrent_runs": self.safe_concurrent_runs,
            "active_run_count": len(leases),
            "host_memory": mem,
            "host_ram_abort_gib": self.host_ram_abort_gib,
            "host_ram_hard_gib": self.host_ram_hard_gib,
            "memory_block_reason": reason,
            "workers": workers,
        }
