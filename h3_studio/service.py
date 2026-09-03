"""Studio service: Run lifecycle, FIFO queue and dispatch onto the worker pool.

Threads touching a Run: HTTP handlers (submit/refresh/cancel), the poll loop
(tick) and whichever thread is submitting to a worker. Every status transition
goes through RunStore.update_if (compare-and-set on status) so a cancel and a
late worker reply cannot overwrite each other.
"""
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

from .comfy import ComfyError, history_error, history_status, video_artifacts
from .config import StudioConfig
from .store import (ACTIVE_STATUSES, CANCELLED, COMPLETED, FAILED, PENDING, QUEUED, RUNNING, SUBMITTING,
                    TERMINAL_STATUSES, RunStore, parse_utc, utc_now)
from .workers import NoWorkerAvailable, WorkerPool, WorkerSpec
from .workflows import KINDS, build_prompt, workflow_summary

LOST_PROMPT_GRACE_S = 30       # prompt neither queued nor in history for this long -> failed
DEAD_WORKER_GRACE_S = 300      # worker continuously unhealthy for this long -> its Runs fail


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
        self._pick_lock = threading.Lock()   # held only while choosing the next pending Run + leasing a worker
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
        """Refresh every active Run (one thread per worker) and drain the queue."""
        by_worker: dict[str, list[dict[str, Any]]] = {}
        for record in self.store.list_by_status(ACTIVE_STATUSES):
            by_worker.setdefault(str((record.get("worker") or {}).get("id")), []).append(record)

        def poll(records: list[dict[str, Any]]) -> None:
            for record in records:
                try:
                    self._sync_with_worker(record)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()

        threads = [threading.Thread(target=poll, args=(recs,), daemon=True) for recs in by_worker.values()]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
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
        record = {
            "schema_version": 2,
            "run_id": run_id,
            "kind": kind,
            "status": PENDING,
            "created_at": utc_now(),
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

    def _pick_next(self) -> tuple[dict[str, Any], WorkerSpec] | None:
        """Under the pick lock: lease a worker for the oldest pending Run and mark it submitting."""
        with self._pick_lock:
            pending = sorted(self.store.list_by_status({PENDING}), key=lambda r: str(r.get("created_at", "")))
            if not pending:
                return None
            head = pending[0]
            run_id = str(head["run_id"])
            try:
                worker = self.pool.acquire(run_id)
            except NoWorkerAvailable as exc:
                for position, rec in enumerate(pending):
                    self.store.update(str(rec["run_id"]), queue_position=position + 1, queue_reason=exc.reason)
                return None
            moved = self.store.update_if(run_id, PENDING, status=SUBMITTING, worker=worker.as_record(), queue_position=None, queue_reason=None)
            if not moved:  # cancelled between listing and leasing
                self.pool.release(run_id)
                return self._pick_next()
            for position, rec in enumerate(pending[1:]):
                self.store.update(str(rec["run_id"]), queue_position=position + 1)
            return self.store.read(run_id), worker

    def dispatch(self) -> list[str]:
        """Assign pending Runs (FIFO) to workers while capacity allows. Worker I/O happens outside the lock."""
        started: list[str] = []
        while True:
            picked = self._pick_next()
            if picked is None:
                return started
            record, worker = picked
            run_id = str(record["run_id"])
            try:
                self._submit_to_worker(record, worker)
                started.append(run_id)
            except Exception as exc:  # noqa: BLE001
                detail = f"{exc.body[:800]}" if isinstance(exc, ComfyError) and exc.body else repr(exc)
                self.store.update_if(run_id, SUBMITTING, status=FAILED, failure_reason=f"submit failed: {detail}", completed_at=utc_now())
                self.pool.release(run_id)

    def _submit_to_worker(self, record: dict[str, Any], worker: WorkerSpec) -> None:
        run_id = str(record["run_id"])
        comfy = self.pool.client(worker)
        first_frame_name = None
        for item in record["inputs"].get("files", []):
            if item.get("role") == "first_frame":
                local = Path(item["path"])
                upload_name = f"{run_id}_first_frame{local.suffix}"
                upload = comfy.upload_image(local, upload_name=upload_name)
                first_frame_name = upload.get("name") or upload_name
                item["comfy_upload"] = upload
        if self.store.read(run_id).get("status") != SUBMITTING:  # cancelled during upload
            self.pool.release(run_id)
            return
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
        prompt_id = str(submit.get("prompt_id"))
        now = utc_now()
        moved = self.store.update_if(
            run_id, SUBMITTING,
            status=QUEUED,
            inputs=record["inputs"],
            workflow_api=api_prompt,
            workflow_summary=workflow_summary(api_prompt),
            prompt_id=prompt_id,
            submit_response=submit,
            submitted_at=now,
            last_seen_at=now,
        )
        if not moved:
            # Cancelled while /prompt was in flight: take the prompt back off the worker.
            self._withdraw(comfy, prompt_id)
            self.store.update(run_id, prompt_id=prompt_id, cancel_action="withdrawn_after_submit")
            self.pool.release(run_id)

    @staticmethod
    def _withdraw(comfy, prompt_id: str) -> str:
        try:
            state = comfy.queue_state(prompt_id)
            if state == "pending":
                comfy.delete_queued(prompt_id)
                return "queue_delete"
            if state == "running":
                comfy.interrupt()
                return "interrupt"
            return "none"
        except Exception as exc:  # noqa: BLE001
            return f"error: {exc!r}"

    # ----- observation ------------------------------------------------------
    def refresh(self, run_id: str, *, dispatch: bool = True) -> dict[str, Any]:
        record = self.store.read(run_id)
        if record.get("status") in {QUEUED, RUNNING}:
            self._sync_with_worker(record)
            record = self.store.read(run_id)
        if dispatch and record.get("status") in TERMINAL_STATUSES:
            self.dispatch()
        return self.decorate(record)

    def _finish(self, run_id: str, **fields: Any) -> bool:
        """Terminal transition from any active status; releases the lease when it wins."""
        fields.setdefault("completed_at", utc_now())
        won = self.store.update_if(run_id, ACTIVE_STATUSES, **fields)
        if won:
            self.pool.release(run_id)
        return won

    def _sync_with_worker(self, record: dict[str, Any]) -> None:
        run_id = str(record["run_id"])
        prompt_id = record.get("prompt_id")
        worker_id = str((record.get("worker") or {}).get("id") or "")
        if record.get("status") == SUBMITTING or not prompt_id:
            return  # the submitting thread owns this Run until it is queued
        dead_for = self.pool.unhealthy_for(worker_id)
        if dead_for > DEAD_WORKER_GRACE_S:
            self._finish(run_id, status=FAILED, failure_reason=f"worker {worker_id} unreachable for {int(dead_for)} s")
            return
        comfy = self.pool.client(worker_id)
        prompt_id = str(prompt_id)
        try:
            state = comfy.queue_state(prompt_id)          # queue first, history second:
            entry = comfy.history(prompt_id).get(prompt_id)  # a prompt moves queue -> history, never back
        except Exception as exc:  # noqa: BLE001
            self.store.update(run_id, last_poll_error=repr(exc))
            return
        outcome = history_status(entry)
        if outcome == COMPLETED:
            artifacts = video_artifacts(entry, comfy)
            completed_at = utc_now()
            fields: dict[str, Any] = {
                "status": COMPLETED if artifacts else FAILED,
                "artifacts": artifacts,
                "comfy_status": entry.get("status"),
                "last_poll_error": None,
                "timing": {
                    "created_to_completed_s": _elapsed_seconds(str(record.get("created_at", "")), completed_at),
                    "submitted_to_completed_s": _elapsed_seconds(str(record.get("submitted_at", "")), completed_at),
                },
            }
            if not artifacts:
                fields["failure_reason"] = "ComfyUI reported success but produced no video output"
            self._finish(run_id, completed_at=completed_at, **fields)
            return
        if outcome == "interrupted":
            self._finish(run_id, status=CANCELLED, comfy_status=entry.get("status"), cancel_action=record.get("cancel_action") or "interrupted_on_worker")
            return
        if outcome == FAILED:
            self._finish(run_id, status=FAILED, comfy_status=entry.get("status"), failure_reason=f"ComfyUI execution error: {history_error(entry)}")
            return
        now = utc_now()
        if state == "running":
            self.store.update_if(run_id, {QUEUED, RUNNING}, status=RUNNING, last_poll_error=None, last_seen_at=now)
        elif state == "pending":
            self.store.update_if(run_id, {QUEUED, RUNNING}, status=QUEUED, last_poll_error=None, last_seen_at=now)
        else:
            last_seen = parse_utc(str(record.get("last_seen_at") or record.get("submitted_at") or "")) or time.time()
            if time.time() - last_seen > LOST_PROMPT_GRACE_S:
                self._finish(run_id, status=FAILED, failure_reason="prompt vanished from worker queue and history (worker restarted or interrupted from the canvas?)")

    def cancel(self, run_id: str) -> dict[str, Any]:
        while True:
            record = self.store.read(run_id)
            status = record.get("status")
            if status in TERMINAL_STATUSES:
                return self.decorate(record)
            if status == PENDING:
                if self.store.update_if(run_id, PENDING, status=CANCELLED, completed_at=utc_now(), queue_position=None, cancel_action="dequeued"):
                    break
                continue  # dispatch grabbed it first; re-read
            if status == SUBMITTING:
                # The submitting thread notices the status change and withdraws the prompt + releases the lease.
                if self.store.update_if(run_id, SUBMITTING, status=CANCELLED, completed_at=utc_now(), cancel_action="cancelled_during_submit"):
                    break
                continue
            comfy = self.pool.client(self.pool.worker_for_record(record))
            action = self._withdraw(comfy, str(record["prompt_id"]))
            self._finish(run_id, status=CANCELLED, cancel_action=action)
            break
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
            if healthy and prompt_id and record.get("status") != SUBMITTING:
                try:
                    comfy = self.pool.client(worker_id)
                    state = comfy.queue_state(str(prompt_id))
                    outcome = history_status(comfy.history(str(prompt_id)).get(str(prompt_id)))
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
