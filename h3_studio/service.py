"""Studio service: Run lifecycle, FIFO queue and dispatch onto the worker pool."""
from __future__ import annotations

import hashlib
import shutil
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .comfy import history_status, video_artifacts
from .config import StudioConfig
from .store import (ACTIVE_STATUSES, CANCELLED, COMPLETED, FAILED, PENDING, QUEUED, RUNNING, SUBMITTING,
                    TERMINAL_STATUSES, RunStore, parse_utc, utc_now)
from .workers import NoWorkerAvailable, WorkerPool
from .workflows import KINDS, build_prompt, workflow_summary


def _elapsed_seconds(start_iso: str, end_iso: str) -> float | None:
    try:
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        start = datetime.strptime(start_iso, fmt).replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_iso, fmt).replace(tzinfo=timezone.utc)
        return round((end - start).total_seconds(), 3)
    except Exception:  # noqa: BLE001
        return None


class StudioService:
    def __init__(self, config: StudioConfig, pool: WorkerPool | None = None, *, poll_interval_s: float = 3.0):
        self.config = config
        self.config.ensure_dirs()
        self.store = RunStore(config.run_root)
        self.pool = pool or WorkerPool(config.worker_pool)
        self.poll_interval_s = poll_interval_s
        self._dispatch_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ----- lifecycle --------------------------------------------------------
    def start(self) -> None:
        self.pool.start_health_thread()
        self.pool.check_health()
        self.recover()
        self._thread = threading.Thread(target=self._poll_loop, name="studio-poll", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.pool.stop()

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            self._stop.wait(self.poll_interval_s)

    def tick(self) -> None:
        """Refresh every active Run and drain the queue. Safe to call from tests."""
        for record in self.store.list_by_status(ACTIVE_STATUSES):
            try:
                self.refresh(str(record["run_id"]), dispatch=False)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
        self.dispatch()

    # ----- submission -------------------------------------------------------
    def submit(self, fields: dict[str, str], files: dict[str, Path]) -> dict[str, Any]:
        kind = fields.get("kind", "t2va")
        if kind not in KINDS:
            raise ValueError(f"unsupported kind: {kind}")
        profile = self.config.profile(fields.get("profile"))
        prompt_text = (fields.get("prompt") or "").strip()
        if not prompt_text:
            raise ValueError("prompt is required")
        try:
            seed = int(fields.get("seed") or 42)
        except ValueError as exc:
            raise ValueError("seed must be an integer") from exc
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        run_dir = self.store.run_dir(run_id)
        input_files: list[dict[str, Any]] = []
        if "image" in KINDS[kind]:
            src = files.get("first_frame")
            if src is None:
                raise ValueError("FL2VA requires a first_frame image")
            input_dir = run_dir / "inputs"
            input_dir.mkdir(parents=True, exist_ok=True)
            suffix = src.suffix.lower() or ".png"
            local = input_dir / f"first_frame{suffix}"
            shutil.copy2(src, local)
            input_files.append({
                "role": "first_frame",
                "path": str(local),
                "sha256": hashlib.sha256(local.read_bytes()).hexdigest(),
                "bytes": local.stat().st_size,
            })
        created = utc_now()
        record = {
            "schema_version": 2,
            "run_id": run_id,
            "kind": kind,
            "status": PENDING,
            "created_at": created,
            "profile": profile,
            "inputs": {
                "prompt": prompt_text,
                "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest(),
                "seed": seed,
                "files": input_files,
            },
            "runtime_identity": {
                "runtime_lock": self.config.runtime_lock,
                "asset_manifest": self.config.asset_manifest,
            },
            "artifacts": [],
            "client_id": f"h3-studio-{run_id}",
        }
        self.store.write(record)
        self.dispatch()
        return self.decorate(self.store.read(run_id))

    def dispatch(self) -> list[str]:
        """Assign pending Runs (FIFO) to workers while capacity allows."""
        started: list[str] = []
        with self._dispatch_lock:
            pending = sorted(self.store.list_by_status({PENDING}), key=lambda r: str(r.get("created_at", "")))
            for position, record in enumerate(pending):
                run_id = str(record["run_id"])
                try:
                    worker = self.pool.acquire(run_id)
                except NoWorkerAvailable as exc:
                    # FIFO: everyone behind this Run waits too.
                    for later, rec in enumerate(pending[position:]):
                        self.store.update(str(rec["run_id"]), queue_position=later + 1, queue_reason=exc.reason)
                    break
                try:
                    self._submit_to_worker(record, worker)
                    started.append(run_id)
                except Exception as exc:  # noqa: BLE001
                    self.pool.release(run_id)
                    self.store.update(run_id, status=FAILED, failure_reason=f"submit failed: {exc!r}", completed_at=utc_now())
        return started

    def _submit_to_worker(self, record: dict[str, Any], worker) -> None:
        run_id = str(record["run_id"])
        comfy = self.pool.client(worker)
        self.store.update(run_id, status=SUBMITTING, worker=worker.as_record(), queue_position=None, queue_reason=None)
        first_frame_name = None
        for item in record["inputs"].get("files", []):
            if item.get("role") == "first_frame":
                local = Path(item["path"])
                upload_name = f"{run_id}_first_frame{local.suffix}"
                upload = comfy.upload_image(local, upload_name=upload_name)
                first_frame_name = upload.get("name") or upload_name
                item["comfy_upload"] = upload
        api_prompt = build_prompt(
            self.config.repo_root,
            kind=str(record["kind"]),
            profile=record["profile"],
            prompt=str(record["inputs"]["prompt"]),
            seed=int(record["inputs"]["seed"]),
            filename_prefix=f"h3_studio/{run_id}",
            first_frame_name=first_frame_name,
        )
        submit = comfy.submit_prompt(api_prompt, client_id=str(record["client_id"]))
        self.store.update(
            run_id,
            status=QUEUED,
            inputs=record["inputs"],
            workflow_api=api_prompt,
            workflow_summary=workflow_summary(api_prompt),
            prompt_id=submit.get("prompt_id"),
            submit_response=submit,
            submitted_at=utc_now(),
        )

    # ----- observation ------------------------------------------------------
    def refresh(self, run_id: str, *, dispatch: bool = True) -> dict[str, Any]:
        record = self.store.read(run_id)
        if record.get("status") in ACTIVE_STATUSES and record.get("prompt_id"):
            self._sync_with_worker(record)
            record = self.store.read(run_id)
        if dispatch and record.get("status") in TERMINAL_STATUSES:
            self.dispatch()
        return self.decorate(record)

    def _sync_with_worker(self, record: dict[str, Any]) -> None:
        run_id = str(record["run_id"])
        prompt_id = str(record["prompt_id"])
        comfy = self.pool.client(self.pool.worker_for_record(record))
        try:
            hist = comfy.history(prompt_id)
        except Exception as exc:  # noqa: BLE001
            self.store.update(run_id, last_poll_error=repr(exc))
            return
        entry = hist.get(prompt_id)
        outcome = history_status(entry)
        if outcome == COMPLETED:
            artifacts = video_artifacts(entry, comfy)
            completed_at = record.get("completed_at") or utc_now()
            fields: dict[str, Any] = {
                "status": COMPLETED,
                "artifacts": artifacts,
                "comfy_status": entry.get("status"),
                "completed_at": completed_at,
                "last_poll_error": None,
            }
            elapsed = _elapsed_seconds(str(record.get("created_at", "")), completed_at)
            if elapsed is not None:
                fields["timing"] = {"created_to_completed_s": elapsed, "submitted_to_completed_s": _elapsed_seconds(str(record.get("submitted_at", "")), completed_at)}
            if not artifacts:
                fields.update(status=FAILED, failure_reason="ComfyUI reported success but produced no video output")
            self.store.update(run_id, **fields)
            self.pool.release(run_id)
            return
        if outcome == FAILED:
            messages = (entry.get("status") or {}).get("messages") or []
            self.store.update(run_id, status=FAILED, comfy_status=entry.get("status"), failure_reason=f"ComfyUI execution error: {messages[-1] if messages else 'unknown'}", completed_at=utc_now())
            self.pool.release(run_id)
            return
        # Not in history yet: distinguish native queue pending vs executing.
        try:
            state = comfy.queue_state(prompt_id)
        except Exception as exc:  # noqa: BLE001
            self.store.update(run_id, last_poll_error=repr(exc))
            return
        if state == "running":
            self.store.update(run_id, status=RUNNING, last_poll_error=None)
        elif state == "pending":
            self.store.update(run_id, status=QUEUED, last_poll_error=None)
        else:
            # Neither queued nor in history: the worker lost it (restart, interrupt from the canvas, ...).
            age = time.time() - (parse_utc(str(record.get("submitted_at") or record.get("created_at") or "")) or time.time())
            if age > 30:
                self.store.update(run_id, status=FAILED, failure_reason="prompt vanished from worker queue and history", completed_at=utc_now())
                self.pool.release(run_id)

    def cancel(self, run_id: str) -> dict[str, Any]:
        record = self.store.read(run_id)
        status = record.get("status")
        if status in TERMINAL_STATUSES:
            return self.decorate(record)
        if status == PENDING:
            self.store.update(run_id, status=CANCELLED, completed_at=utc_now(), queue_position=None)
            return self.decorate(self.store.read(run_id))
        cancel_action = "none"
        prompt_id = record.get("prompt_id")
        if prompt_id:
            comfy = self.pool.client(self.pool.worker_for_record(record))
            try:
                state = comfy.queue_state(str(prompt_id))
                if state == "pending":
                    comfy.delete_queued(str(prompt_id))
                    cancel_action = "queue_delete"
                elif state == "running":
                    comfy.interrupt()
                    cancel_action = "interrupt"
            except Exception as exc:  # noqa: BLE001
                cancel_action = f"error: {exc!r}"
        self.store.update(run_id, status=CANCELLED, cancel_action=cancel_action, completed_at=utc_now())
        self.pool.release(run_id)
        self.dispatch()
        return self.decorate(self.store.read(run_id))

    # ----- restart recovery -------------------------------------------------
    def recover(self, *, stale_after_s: int = 6 * 3600) -> dict[str, Any]:
        """Reconcile Runs left active by a previous Studio process."""
        changed: dict[str, str] = {}
        for record in self.store.list_by_status(ACTIVE_STATUSES):
            run_id = str(record["run_id"])
            worker_id = str((record.get("worker") or {}).get("id") or "")
            prompt_id = record.get("prompt_id")
            healthy = worker_id in {w.id for w in self.pool.workers} and self.pool.is_healthy(worker_id)
            if healthy and prompt_id:
                try:
                    comfy = self.pool.client(worker_id)
                    outcome = history_status(comfy.history(str(prompt_id)).get(str(prompt_id)))
                    state = comfy.queue_state(str(prompt_id))
                except Exception:  # noqa: BLE001
                    outcome, state = None, "absent"
                if outcome or state in {"running", "pending"}:
                    self.pool.restore_lease(worker_id, run_id)
                    self._sync_with_worker(record)
                    changed[run_id] = self.store.read(run_id)["status"]
                    continue
            age = time.time() - (parse_utc(str(record.get("updated_at") or record.get("created_at") or "")) or 0)
            reason = "worker lost the Run during Studio restart" if age < stale_after_s else "stale active Run exceeded recovery window"
            self.store.update(run_id, status=FAILED, failure_reason=reason, recovered_at=utc_now(), completed_at=utc_now())
            changed[run_id] = FAILED
        self.dispatch()
        return {"changed": changed}

    # ----- views ------------------------------------------------------------
    def decorate(self, record: dict[str, Any]) -> dict[str, Any]:
        copy = dict(record)
        copy.pop("runtime_identity", None)
        copy.pop("workflow_api", None)
        for item in copy.get("artifacts", []):
            item["download_url"] = f"/api/runs/{copy['run_id']}/artifacts/{item['artifact_id']}/file"
        worker_id = (copy.get("worker") or {}).get("id")
        if worker_id:
            copy["canvas_url"] = f"/canvas/{worker_id}/"
            copy["ws_url"] = f"/canvas/{worker_id}/ws?clientId={copy['client_id']}"
        return copy

    def artifact_source(self, run_id: str, artifact_id: str) -> str:
        """Worker URL for an artifact file (proxied by the HTTP layer)."""
        record = self.store.read(run_id)
        for item in record.get("artifacts", []):
            if item.get("artifact_id") == artifact_id:
                return str(item["view_url"])
        raise KeyError(artifact_id)

    def config_view(self) -> dict[str, Any]:
        first = self.pool.first_healthy()
        return {
            "version": __import__("h3_studio").__version__,
            "profiles": self.config.profiles,
            "default_profile": self.config.default_profile,
            "kinds": sorted(KINDS),
            "canvas_url": f"/canvas/{first.id}/" if first else None,
            "pool": self.pool.status(),
        }
