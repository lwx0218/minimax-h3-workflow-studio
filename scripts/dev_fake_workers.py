#!/usr/bin/env python3
"""Run the Studio against fake ComfyUI workers (no GPU) to develop or demo the UI.

    python3 scripts/dev_fake_workers.py [--workers 5] [--cap 2] [--port 30210] [--finish-after 20]

Fake workers "complete" a prompt --finish-after seconds after it starts executing and
return a tiny placeholder mp4. Everything else (queue, cancel, canvas proxy) is real.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fake_comfy import FakeComfyServer  # noqa: E402
from h3_studio.config import StudioConfig  # noqa: E402
from h3_studio.server import Handler  # noqa: E402
from h3_studio.service import StudioService  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--cap", type=int, default=2)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=30210)
    ap.add_argument("--finish-after", type=float, default=20.0)
    args = ap.parse_args()

    fakes = [FakeComfyServer().start() for _ in range(args.workers)]
    tmp = tempfile.mkdtemp(prefix="h3-studio-dev-")
    pool = {
        "safe_concurrent_runs": args.cap,
        "host_ram_abort_gib": 9999,
        "host_ram_hard_gib": 10000,
        "health_interval_s": 2,
        "workers": [{"id": f"worker-gpu{i}", "gpu": str(i), "port": f.port} for i, f in enumerate(fakes)],
    }
    pool_path = Path(tmp) / "pool.json"
    pool_path.write_text(json.dumps(pool), encoding="utf-8")
    cfg = StudioConfig.from_env(ROOT, env={"H3_STUDIO_DATA": tmp, "H3_WORKER_POOL_CONFIG": str(pool_path), "H3_STUDIO_HOST": args.host, "H3_STUDIO_PORT": str(args.port)})
    service = StudioService(cfg, poll_interval_s=1.0)
    service.start()

    def auto_finish() -> None:
        started: dict[str, float] = {}
        while True:
            for fake in fakes:
                with fake.state.lock:
                    running = fake.state.running
                if running and running not in started:
                    started[running] = time.time()
                if running and time.time() - started[running] >= args.finish_after:
                    fake.state.finish(running)
            time.sleep(0.5)

    threading.Thread(target=auto_finish, daemon=True).start()
    Handler.service = service
    httpd = ThreadingHTTPServer((cfg.studio_host, cfg.studio_port), Handler)
    httpd.daemon_threads = True
    print(f"Dev Studio with {args.workers} fake workers (cap {args.cap}): http://{cfg.studio_host}:{cfg.studio_port}/  data={tmp}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
        for fake in fakes:
            fake.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
