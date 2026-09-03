"""Studio tests against fake ComfyUI workers. Run: python3 -m unittest -v  (or pytest)."""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake_comfy import FakeComfyServer  # noqa: E402
from h3_studio.config import StudioConfig  # noqa: E402
from h3_studio.server import Handler  # noqa: E402
from h3_studio.service import StudioService  # noqa: E402
from h3_studio.workers import NoWorkerAvailable, WorkerPool, WorkerSpec  # noqa: E402
from h3_studio.workflows import build_prompt  # noqa: E402


def pool_doc(ports: list[int], cap: int = 2, **extra) -> dict:
    return {
        "safe_concurrent_runs": cap,
        "host_ram_abort_gib": 9999,
        "host_ram_hard_gib": 10000,
        "health_interval_s": 0.2,
        "worker_host": "127.0.0.1",
        "workers": [{"id": f"worker-gpu{i}", "gpu": str(i), "port": p} for i, p in enumerate(ports)],
        **extra,
    }


def make_config(tmp: str, pool: dict) -> StudioConfig:
    pool_path = Path(tmp) / "pool.json"
    pool_path.write_text(json.dumps(pool), encoding="utf-8")
    return StudioConfig.from_env(ROOT, env={"H3_STUDIO_DATA": tmp, "H3_WORKER_POOL_CONFIG": str(pool_path)})


def multipart(fields: dict[str, str], files: dict[str, bytes] | None = None) -> tuple[bytes, str]:
    boundary = "----test" + uuid.uuid4().hex
    chunks = []
    for k, v in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for k, data in (files or {}).items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{k}.png\"\r\nContent-Type: image/png\r\n\r\n".encode() + data + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


class WorkflowTests(unittest.TestCase):
    def test_build_prompt_patches_only_approved_inputs(self):
        cfg = StudioConfig.from_env(ROOT)
        profile = cfg.profile("draft")
        api = build_prompt(ROOT, kind="t2va", profile=profile, prompt="hello", seed=7, filename_prefix="h3_studio/run-x")
        self.assertEqual(api["5"]["inputs"]["prompt"], "hello")
        self.assertEqual(api["7"]["inputs"]["seed"], 7)
        self.assertEqual(api["7"]["inputs"]["sigma_points"], 9)
        self.assertEqual(api["10"]["inputs"]["filename_prefix"], "h3_studio/run-x")
        self.assertEqual(api["4"]["inputs"]["width"], 864)
        fl = build_prompt(ROOT, kind="fl2va_first_frame", profile=profile, prompt="p", seed=1, filename_prefix="x", first_frame_name="f.png")
        self.assertEqual(fl["4"]["inputs"]["image"], "f.png")
        with self.assertRaises(ValueError):
            build_prompt(ROOT, kind="fl2va_first_frame", profile=profile, prompt="p", seed=1, filename_prefix="x")

    def test_profile_aliases(self):
        cfg = StudioConfig.from_env(ROOT)
        self.assertEqual(cfg.profile("balanced-r2-a5000")["name"], "balanced")
        self.assertEqual(cfg.profile(None)["name"], "balanced")
        with self.assertRaises(ValueError):
            cfg.profile("nope")


class PoolTests(unittest.TestCase):
    def test_spec_validation(self):
        for bad in ({"id": "a", "port": 70000}, {"id": "a", "port": "x"}, {"id": "a"}):
            with self.assertRaises(ValueError):
                WorkerSpec.from_doc(bad)
        with self.assertRaises(ValueError):
            WorkerPool({"workers": [{"id": "a", "port": 1}, {"id": "a", "port": 2}]})
        with self.assertRaises(ValueError):
            WorkerPool({"workers": [{"id": "a", "port": 1}, {"id": "b", "port": 1}]})

    def test_acquire_lru_cap_and_memory_gate(self):
        mem = {"used_gib": 10.0, "total_gib": 100.0, "available_gib": 90.0}
        pool = WorkerPool(pool_doc([1, 2, 3], cap=2), memory_probe=lambda: dict(mem))
        with self.assertRaises(NoWorkerAvailable) as ctx:
            pool.acquire("r0")
        self.assertEqual(ctx.exception.reason, "no healthy idle worker")
        for w in pool.workers:
            pool._health[w.id] = {"healthy": True}
        a = pool.acquire("r1")
        b = pool.acquire("r2")
        self.assertNotEqual(a.id, b.id)
        with self.assertRaises(NoWorkerAvailable) as ctx:
            pool.acquire("r3")
        self.assertEqual(ctx.exception.reason, "safe concurrent Run limit reached")
        pool.release("r1")
        c = pool.acquire("r3")
        self.assertEqual(c.id, "worker-gpu2", "least recently used idle worker should be chosen")
        mem["used_gib"] = 9999
        pool.release("r2")
        with self.assertRaises(NoWorkerAvailable) as ctx:
            pool.acquire("r4")
        self.assertIn("host RAM", ctx.exception.reason)
        pool2 = WorkerPool(pool_doc([1]), memory_probe=lambda: {"error": "x"})
        pool2._health["worker-gpu0"] = {"healthy": True}
        with self.assertRaises(NoWorkerAvailable) as ctx:
            pool2.acquire("r5")
        self.assertEqual(ctx.exception.reason, "host RAM status unavailable")


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.fakes = [FakeComfyServer().start() for _ in range(3)]
        self.tmp = tempfile.TemporaryDirectory(prefix="h3-studio-test-")
        self.cfg = make_config(self.tmp.name, pool_doc([f.port for f in self.fakes], cap=2))
        self.service = StudioService(self.cfg, poll_interval_s=0.2)
        self.service.pool.check_health()

    def tearDown(self):
        self.service.stop()
        for f in self.fakes:
            f.stop()
        self.tmp.cleanup()

    def fake_for(self, record) -> FakeComfyServer:
        port = record["worker"]["port"]
        return next(f for f in self.fakes if f.port == port)

    def submit(self, **fields):
        base = {"kind": "t2va", "profile": "balanced", "prompt": "mock rain", "seed": "1"}
        return self.service.submit(base | fields, {})

    def test_fifo_queue_and_dispatch(self):
        r1, r2, r3 = self.submit(seed="1"), self.submit(seed="2"), self.submit(seed="3")
        self.assertEqual(r1["status"], "queued")
        self.assertEqual(r2["status"], "queued")
        self.assertNotEqual(r1["worker"]["id"], r2["worker"]["id"])
        self.assertEqual(r3["status"], "pending")
        self.assertEqual(r3["queue_position"], 1)
        self.assertEqual(r3["queue_reason"], "safe concurrent Run limit reached")
        # Worker starts executing r1 -> running
        self.assertEqual(self.service.refresh(r1["run_id"])["status"], "running")
        self.fake_for(r1).state.finish(r1["prompt_id"])
        done = self.service.refresh(r1["run_id"])
        self.assertEqual(done["status"], "completed")
        self.assertEqual(len(done["artifacts"]), 1)
        self.assertTrue(done["artifacts"][0]["download_url"].startswith("/api/runs/"))
        self.assertIn("created_to_completed_s", done["timing"])
        r3 = self.service.refresh(r3["run_id"])
        self.assertIn(r3["status"], {"queued", "running"}, "pending Run must be dispatched once capacity frees")
        self.assertIsNone(r3["queue_position"])
        self.assertEqual(self.service.pool.status()["active_run_count"], 2)

    def test_worker_error_marks_failed_and_releases(self):
        r1 = self.submit()
        self.fake_for(r1).state.finish(r1["prompt_id"], error=True)
        done = self.service.refresh(r1["run_id"])
        self.assertEqual(done["status"], "failed")
        self.assertIn("ComfyUI execution error", done["failure_reason"])
        self.assertEqual(self.service.pool.status()["active_run_count"], 0)

    def test_cancel_pending_queued_and_running(self):
        r1, r2, r3 = self.submit(seed="1"), self.submit(seed="2"), self.submit(seed="3")
        # pending: no worker involved
        c3 = self.service.cancel(r3["run_id"])
        self.assertEqual(c3["status"], "cancelled")
        self.assertNotIn("worker", c3)
        # queued on the same fake as a running one -> queue delete, no interrupt
        fake1 = self.fake_for(r1)
        r4 = self.submit(seed="4")  # cap freed by cancelling r3? no: r1,r2 still active -> pending
        self.assertEqual(r4["status"], "pending")
        # make r1 running then submit an extra prompt directly on that worker to emulate a native queue neighbour
        self.assertEqual(self.service.refresh(r1["run_id"])["status"], "running")
        before = fake1.state.interrupts
        c1 = self.service.cancel(r1["run_id"])
        self.assertEqual(c1["status"], "cancelled")
        self.assertEqual(c1["cancel_action"], "interrupt")
        self.assertEqual(fake1.state.interrupts, before + 1)
        # cancelling again is a no-op
        self.service.cancel(r1["run_id"])
        self.assertEqual(fake1.state.interrupts, before + 1)
        # r4 should have been dispatched after r1 released
        r4 = self.service.refresh(r4["run_id"])
        self.assertIn(r4["status"], {"queued", "running"})
        # queued-but-not-executing cancel uses queue delete
        fake4 = self.fake_for(r4)
        extra = fake4.state.submit({"10": {"inputs": {"filename_prefix": "x/y"}}}, "someone-else")  # native canvas job
        fake4.state.running = extra if fake4.state.running == r4["prompt_id"] else fake4.state.running
        fake4.state.pending = [r4["prompt_id"]] if r4["prompt_id"] not in fake4.state.pending else fake4.state.pending
        before = fake4.state.interrupts
        c4 = self.service.cancel(r4["run_id"])
        self.assertEqual(c4["cancel_action"], "queue_delete")
        self.assertEqual(fake4.state.interrupts, before, "cancelling a queued Run must not interrupt the worker's current job")

    def test_cancel_during_submit_withdraws_prompt_and_releases_lease(self):
        for f in self.fakes:
            f.state.prompt_delay_s = 1.0
        results = {}
        t = threading.Thread(target=lambda: results.setdefault("rec", self.submit(seed="9")))
        t.start()
        time.sleep(0.3)  # dispatch is now inside POST /prompt
        pending = self.service.store.list_by_status({"submitting"})
        self.assertEqual(len(pending), 1)
        run_id = pending[0]["run_id"]
        cancelled = self.service.cancel(run_id)
        self.assertEqual(cancelled["status"], "cancelled")
        t.join(5)
        final = self.service.store.read(run_id)
        self.assertEqual(final["status"], "cancelled", "late /prompt reply must not resurrect a cancelled Run")
        self.assertEqual(final["cancel_action"], "withdrawn_after_submit")
        self.assertEqual(self.service.pool.leases(), {}, "lease must be released exactly once")
        fake = next(f for f in self.fakes if f.port == final["worker"]["port"])
        self.assertNotIn(final["prompt_id"], fake.state.pending)
        self.assertNotEqual(fake.state.running, final["prompt_id"])

    def test_interrupted_on_worker_becomes_cancelled_and_lost_prompt_fails(self):
        r1 = self.submit()
        fake = self.fake_for(r1)
        # someone hit "interrupt" in the canvas
        fake.state.interrupts += 0
        fake.state.history[r1["prompt_id"]] = {"status": {"status_str": "error", "completed": False, "messages": [["execution_interrupted", {}]]}, "outputs": {}}
        fake.state.running = None
        self.assertEqual(self.service.refresh(r1["run_id"])["status"], "cancelled")
        # worker restarted and forgot the prompt entirely
        r2 = self.submit()
        fake2 = self.fake_for(r2)
        fake2.state.running = None; fake2.state.pending = []
        self.assertIn(self.service.refresh(r2["run_id"])["status"], {"queued", "running"}, "inside the grace window nothing changes")
        self.service.store.update(r2["run_id"], last_seen_at="2000-01-01T00:00:00Z", submitted_at="2000-01-01T00:00:00Z")
        self.assertEqual(self.service.refresh(r2["run_id"])["status"], "failed")
        self.assertEqual(self.service.pool.leases(), {})

    def test_fl2va_uploads_first_frame_at_dispatch(self):
        png = Path(self.tmp.name) / "frame.png"
        png.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de0000000c49444154789c63606060000000040001f61738550000000049454e44ae426082"))
        rec = self.service.submit({"kind": "fl2va_first_frame", "profile": "draft", "prompt": "p", "seed": "5"}, {"first_frame": png})
        self.assertEqual(rec["status"], "queued")
        fake = self.fake_for(rec)
        self.assertTrue(fake.state.uploads and fake.state.uploads[0].startswith(rec["run_id"]))
        full = self.service.store.read(rec["run_id"])
        self.assertEqual(full["workflow_api"]["4"]["inputs"]["image"], fake.state.uploads[0])
        with self.assertRaises(ValueError):
            self.service.submit({"kind": "fl2va_first_frame", "prompt": "p"}, {})

    def test_recover_after_restart(self):
        r1, r2 = self.submit(seed="1"), self.submit(seed="2")
        self.fake_for(r1).state.finish(r1["prompt_id"])
        # Simulate a Studio restart: new service over the same data dir, r1 finished meanwhile, r2 still running.
        self.service.stop()
        svc2 = StudioService(self.cfg, poll_interval_s=0.2)
        svc2.pool.check_health()
        result = svc2.recover()
        self.assertEqual(result["changed"][r1["run_id"]], "completed")
        self.assertIn(result["changed"][r2["run_id"]], {"queued", "running"})
        self.assertEqual(svc2.pool.leases().get(r2["worker"]["id"]), r2["run_id"])
        # A run whose worker forgot it fails
        self.fake_for(r2).state.running = None
        self.fake_for(r2).state.pending = []
        svc3 = StudioService(self.cfg, poll_interval_s=0.2)
        svc3.pool.check_health()
        res3 = svc3.recover()
        self.assertEqual(res3["changed"][r2["run_id"]], "failed")
        svc2.stop(); svc3.stop()

    def test_unhealthy_worker_is_skipped(self):
        self.fakes[0].stop()
        self.service.pool.check_health()
        r1 = self.submit()
        self.assertNotEqual(r1["worker"]["port"], self.fakes[0].port)
        status = self.service.pool.status()
        self.assertEqual(status["healthy_count"], 2)


class HttpTests(unittest.TestCase):
    """The HTTP layer: multipart submit, artifact Range streaming, canvas proxy, websocket proxy."""

    def setUp(self):
        self.fakes = [FakeComfyServer().start() for _ in range(2)]
        self.tmp = tempfile.TemporaryDirectory(prefix="h3-studio-http-")
        self.cfg = make_config(self.tmp.name, pool_doc([f.port for f in self.fakes], cap=2))
        self.service = StudioService(self.cfg, poll_interval_s=0.2)
        self.service.pool.check_health()
        handler = type("H", (Handler,), {"service": self.service})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close()
        self.service.stop()
        for f in self.fakes:
            f.stop()
        self.tmp.cleanup()

    def get(self, path, headers=None):
        req = urllib.request.Request(self.base + path, headers=headers or {})
        return urllib.request.urlopen(req, timeout=10)

    def post_form(self, fields, files=None):
        body, boundary = multipart(fields, files)
        req = urllib.request.Request(self.base + "/api/runs", data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())

    def test_index_config_and_submit(self):
        with self.get("/") as resp:
            self.assertIn(b"MiniMax H3 Studio", resp.read())
        cfg = json.loads(self.get("/api/config").read())
        self.assertIn("balanced", cfg["profiles"])
        self.assertTrue(cfg["canvas_url"].startswith("/canvas/worker-gpu"))
        status, rec = self.post_form({"kind": "t2va", "profile": "draft", "prompt": "hi", "seed": "3"})
        self.assertEqual(status, 201)
        self.assertEqual(rec["status"], "queued")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post_form({"kind": "t2va", "prompt": ""})
        self.assertEqual(ctx.exception.code, 400)
        runs = json.loads(self.get("/api/runs").read())["runs"]
        self.assertEqual(runs[0]["run_id"], rec["run_id"])
        self.assertEqual(runs[0]["worker"], rec["worker"]["id"])

    def test_artifact_streaming_supports_range(self):
        _, rec = self.post_form({"kind": "t2va", "prompt": "hi", "seed": "3"})
        fake = next(f for f in self.fakes if f.port == rec["worker"]["port"])
        fake.state.finish(rec["prompt_id"])
        done = json.loads(self.get(f"/api/runs/{rec['run_id']}").read())
        url = done["artifacts"][0]["download_url"]
        with self.get(url) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers["Content-Type"], "video/mp4")
            self.assertEqual(resp.read(), fake.state.video)
        with self.get(url, {"Range": "bytes=10-19"}) as resp:
            self.assertEqual(resp.status, 206)
            self.assertEqual(resp.headers["Content-Range"], f"bytes 10-19/{len(fake.state.video)}")
            self.assertEqual(resp.read(), fake.state.video[10:20])

    def test_canvas_http_proxy_rewrites_origin(self):
        with self.get("/canvas/worker-gpu1/", {"Origin": f"http://127.0.0.1:{self.port}"}) as resp:
            body = resp.read().decode()
        port = self.fakes[1].port
        self.assertIn(f"Origin=http://127.0.0.1:{port}", body)
        self.assertIn(f"Host=127.0.0.1:{port}", body)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/canvas/nope/")
        self.assertEqual(ctx.exception.code, 404)
        # bare /canvas redirects to the first healthy worker
        opener = urllib.request.build_opener(NoRedirect)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            opener.open(self.base + "/canvas", timeout=10)
        self.assertEqual(ctx.exception.code, 302)
        self.assertEqual(ctx.exception.headers["Location"], "/canvas/worker-gpu0/")

    def test_canvas_websocket_refusal_is_relayed_and_closed(self):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        s.sendall(b"GET /canvas/worker-gpu0/ws?deny=1 HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n")
        got = b""
        deadline = time.time() + 5
        while time.time() < deadline:
            chunk = s.recv(4096)
            if not chunk:
                break
            got += chunk
        self.assertTrue(got.startswith(b"HTTP/1.1 403"), got)
        self.assertLess(time.time(), deadline, "proxy must close the client connection after a refused upgrade")
        s.close()

    def test_canvas_websocket_proxy_pumps_bytes(self):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        s.sendall(b"GET /canvas/worker-gpu0/ws?clientId=abc HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n")
        head = b""
        while b"\r\n\r\n" not in head:
            head += s.recv(1024)
        self.assertTrue(head.startswith(b"HTTP/1.1 101"), head)
        self.assertIn(b"X-Client-Id: abc", head)
        s.sendall(b"ping")
        deadline = time.time() + 5
        got = b""
        while b"echo:ping" not in got and time.time() < deadline:
            got += s.recv(1024)
        self.assertIn(b"echo:ping", got)
        s.close()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


if __name__ == "__main__":
    unittest.main()
