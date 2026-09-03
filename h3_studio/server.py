from __future__ import annotations

import cgi
import hashlib
import json
import mimetypes
import shutil
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
import urllib.request

from .assets import validate_assets
from .comfy import flatten_history_outputs
from .config import StudioConfig
from .store import RunStore, utc_now
from .workers import NoWorkerAvailable, TERMINAL_STATUSES, WorkerPool


def _elapsed_seconds(start_iso: str, end_iso: str) -> float | None:
    try:
        start = datetime.strptime(start_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return round((end - start).total_seconds(), 3)
    except Exception:
        return None
from .workflows import build_prompt, workflow_summary


INDEX_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>MiniMax H3 Studio — R4</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; background:#10131a; color:#edf2ff; }
    body { margin:0; padding:24px; }
    main { max-width: 1120px; margin: 0 auto; }
    .grid { display:grid; grid-template-columns: minmax(360px, 1fr) minmax(360px, 1fr); gap:20px; }
    section, .card { background:#171c28; border:1px solid #2a3346; border-radius:14px; padding:18px; box-shadow:0 10px 24px #0004; }
    label { display:block; margin-top:12px; font-weight:650; }
    input, textarea, select, button { width:100%; box-sizing:border-box; border-radius:10px; border:1px solid #3b4660; padding:10px; background:#0f1420; color:#edf2ff; }
    textarea { min-height:140px; }
    button { margin-top:16px; background:#4f7cff; border:0; cursor:pointer; font-weight:750; }
    button:disabled { opacity:.5; cursor:not-allowed; }
    a { color:#8ab4ff; }
    code, pre { background:#0e1320; border-radius:8px; padding:2px 5px; }
    .muted { color:#a9b4c7; } .ok { color:#8ef0b5; } .bad { color:#ff9e9e; }
    video { width:100%; margin-top:12px; border-radius:12px; background:#000; }
    table { width:100%; border-collapse:collapse; } td,th { border-bottom:1px solid #2a3346; padding:8px; text-align:left; }
  </style>
</head>
<body>
<main>
  <h1>MiniMax H3 Studio — Worker Pool</h1>
  <p class=\"muted\">Guided Mode submits native ComfyUI H3 API workflows to isolated Workers. Advanced Canvas opens pinned ComfyUI frontends.</p>
  <div class=\"grid\">
    <section>
      <h2>Guided Mode</h2>
      <form id=\"runForm\">
        <label>Workflow</label>
        <select name=\"kind\" id=\"kind\"><option value=\"t2va\">T2VA — text to video+audio</option><option value=\"fl2va_first_frame\">FL2VA — first frame to video+audio</option></select>
        <label>Generation Profile</label><select name=\"profile\" id=\"profileSelect\"></select>
        <label>Prompt</label><textarea name=\"prompt\">A five-second cinematic 16:9 shot of a small paper boat gliding through a rain-lit city gutter at night. Reflections ripple across the water, a distant train passes, and the ambient rain and wheel noise stay synchronized with the movement. Natural camera motion, no subtitles, no logos.</textarea>
        <label>Seed</label><input name=\"seed\" type=\"number\" value=\"42\" />
        <label id=\"frameLabel\" style=\"display:none\">First frame image (FL2VA)</label><input id=\"firstFrame\" name=\"first_frame\" type=\"file\" accept=\"image/*\" style=\"display:none\" />
        <button id=\"submitBtn\">Submit Run</button>
      </form>
      <p>Advanced Canvas: <a id=\"canvasLink\" target=\"_blank\">open first healthy ComfyUI frontend</a></p>
      <p class=\"muted\">Load UI workflows from <code>workflows/comfy-ui/</code>; each Worker uses isolated ports, logs, temp and output namespaces.</p>
      <p class=\"muted\">Use Guided Mode for Worker-Pool scheduling and Run traceability. Direct Advanced Canvas submissions use that Worker's native ComfyUI queue.</p>
    </section>
    <section>
      <h2>Status / Progress</h2>
      <pre id=\"statusBox\">No run submitted.</pre>
      <button id=\"cancelBtn\" disabled>Cancel current Run</button>
      <div id=\"artifactBox\"></div>
    </section>
  </div>
  <section style=\"margin-top:20px\"><h2>Worker Pool</h2><pre id=\"poolBox\">Loading...</pre></section>
  <section style=\"margin-top:20px\"><h2>Recent Runs</h2><div id=\"recent\"></div></section>
</main>
<script>
let currentRun = null; let timer = null; let ws = null;
async function api(path, opts={}) { const r = await fetch(path, opts); if(!r.ok) throw new Error(await r.text()); return await r.json(); }
async function init(){ const s=await api('/api/config'); document.getElementById('canvasLink').href=s.advanced_canvas_url; const ps=document.getElementById('profileSelect'); ps.innerHTML=Object.entries(s.profiles).map(([id,p])=>`<option value=\"${id}\">${p.label||id}</option>`).join(''); drawRecent(); drawPool(); }
function setStatus(obj){ document.getElementById('statusBox').textContent=JSON.stringify(obj,null,2); }
function connectWs(wsBase, clientId, promptId){ try { if(ws) ws.close(); ws = new WebSocket(wsBase + '?clientId=' + encodeURIComponent(clientId)); ws.onmessage = (ev)=>{ const msg=JSON.parse(ev.data); if(msg.type==='progress' || msg.type==='executing' || msg.type==='status') { const cur=JSON.parse(document.getElementById('statusBox').textContent || '{}'); cur.websocket_event=msg; setStatus(cur); } }; } catch(e) { console.warn(e); } }
async function drawRecent(){ const rows=(await api('/api/runs')).runs; document.getElementById('recent').innerHTML='<table><tr><th>Run</th><th>Kind</th><th>Status</th><th>Worker</th><th>Artifacts</th></tr>'+rows.map(r=>`<tr><td><code>${r.run_id}</code></td><td>${r.kind}</td><td>${r.status}</td><td>${(r.worker&&r.worker.id)||''}</td><td>${(r.artifacts||[]).length}</td></tr>`).join('')+'</table>'; }
async function drawPool(){ try { const p=await api('/api/workers'); document.getElementById('poolBox').textContent=JSON.stringify(p,null,2); } catch(e){ document.getElementById('poolBox').textContent=String(e); } }
async function poll(){ if(!currentRun) return; const r=await api('/api/runs/'+currentRun); setStatus(r); document.getElementById('cancelBtn').disabled = ['completed','failed','cancelled'].includes(r.status); if(r.artifacts && r.artifacts.length){ document.getElementById('artifactBox').innerHTML = r.artifacts.map(a=>`<p><a href=\"${a.download_url}\" target=\"_blank\">${a.filename}</a></p><video controls src=\"${a.download_url}\"></video>`).join(''); } if(['completed','failed','cancelled'].includes(r.status)){ clearInterval(timer); drawRecent(); drawPool(); } }
document.getElementById('kind').onchange = (ev)=>{ const fl=ev.target.value==='fl2va_first_frame'; document.getElementById('frameLabel').style.display=fl?'block':'none'; document.getElementById('firstFrame').style.display=fl?'block':'none'; };
document.getElementById('runForm').onsubmit = async (ev)=>{ ev.preventDefault(); const fd=new FormData(ev.target); document.getElementById('submitBtn').disabled=true; try { const res=await api('/api/runs',{method:'POST', body:fd}); currentRun=res.run_id; setStatus(res); connectWs(res.worker_ws_url, res.client_id, res.prompt_id); timer=setInterval(poll, 2500); poll(); } finally { document.getElementById('submitBtn').disabled=false; } };
document.getElementById('cancelBtn').onclick = async ()=>{ if(currentRun) await api('/api/runs/'+currentRun+'/cancel',{method:'POST'}); };
init().catch(e=>setStatus({error:String(e)}));
</script>
</body>
</html>
"""


class StudioService:
    def __init__(self, config: StudioConfig):
        self.config = config
        self.config.ensure_dirs()
        self.store = RunStore(config.run_root)
        self.pool = WorkerPool(config.worker_pool, self.store)
        self.pool.recover_stale_runs()

    def workers(self) -> dict[str, Any]:
        return self.pool.status(include_health=True)

    def health(self) -> dict[str, Any]:
        pool = self.workers()
        healthy = [w for w in pool["workers"] if w.get("healthy")]
        return {"ok": bool(healthy) and not pool.get("host_ram_over_abort") and not pool.get("host_ram_over_hard"), "pool": pool}

    def _advanced_canvas_url(self) -> str:
        for worker in self.pool.discover():
            if worker.get("healthy"):
                return str(worker["url"]) + "/"
        return self.pool.workers[0].url + "/"

    def submit(self, fields: dict[str, str], files: dict[str, Path]) -> dict[str, Any]:
        kind = fields.get("kind", "t2va")
        profile_name = fields.get("profile") or self.config.default_profile
        profile = self.config.profile(profile_name)
        prompt_text = (fields.get("prompt") or "").strip()
        if not prompt_text:
            raise ValueError("prompt is required")
        if kind == "fl2va_first_frame" and files.get("first_frame") is None:
            raise ValueError("FL2VA requires first_frame image")
        if kind not in {"t2va", "fl2va_first_frame"}:
            raise ValueError(f"unsupported kind: {kind}")
        seed = int(fields.get("seed") or 42)
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        worker = self.pool.acquire(run_id)
        comfy = self.pool.client(worker)
        record: dict[str, Any] | None = None
        try:
            client_id = f"h3-studio-{run_id}"
            run_dir = self.store.run_dir(run_id)
            input_dir = run_dir / "inputs"
            input_dir.mkdir(parents=True, exist_ok=True)
            first_frame_name = None
            input_files: list[dict[str, Any]] = []
            if kind == "fl2va_first_frame":
                src = files["first_frame"]
                suffix = src.suffix.lower() if src.suffix else ".png"
                local = input_dir / f"first_frame{suffix}"
                shutil.copy2(src, local)
                digest = hashlib.sha256(local.read_bytes()).hexdigest()
                upload_name = f"{run_id}_first_frame{suffix}"
                upload = comfy.upload_image(local, upload_name=upload_name)
                first_frame_name = upload.get("name") or upload_name
                input_files.append({"role": "first_frame", "sha256": digest, "bytes": local.stat().st_size, "comfy_upload": upload})
            filename_prefix = f"h3_studio/{run_id}"
            api_prompt = build_prompt(
                self.config.repo_root,
                kind=kind,
                profile=profile,
                prompt=prompt_text,
                seed=seed,
                filename_prefix=filename_prefix,
                first_frame_name=first_frame_name,
            )
            created = utc_now()
            record = {
                "schema_version": 1,
                "run_id": run_id,
                "kind": kind,
                "status": "submitting",
                "created_at": created,
                "updated_at": created,
                "profile": profile,
                "model_runtime_identity": {
                    "runtime_lock": self.config.runtime_lock,
                    "asset_manifest": self.config.asset_manifest,
                    "worker_pool": self.config.worker_pool,
                },
                "inputs": {"prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest(), "seed": seed, "files": input_files},
                "workflow_api": api_prompt,
                "workflow_summary": workflow_summary(api_prompt),
                "artifacts": [],
                "worker": worker.as_record(),
                "client_id": client_id,
            }
            self.store.write(record)
            submit = comfy.submit_prompt(api_prompt, client_id=client_id)
            record.update({"status": "queued", "prompt_id": submit.get("prompt_id"), "number": submit.get("number"), "submit_response": submit, "updated_at": utc_now()})
            self.store.write(record)
            self.pool.release(run_id)
            return self.decorate(record)
        except Exception as exc:
            if record is not None:
                record["status"] = "failed"
                record["failure_reason"] = repr(exc)
                record["updated_at"] = utc_now()
                self.store.write(record)
            self.pool.release(run_id)
            raise

    def refresh(self, run_id: str) -> dict[str, Any]:
        record = self.store.read(run_id)
        prompt_id = record.get("prompt_id")
        comfy = self.pool.client(self.pool.worker_for_record(record))
        if not prompt_id:
            return self.decorate(record)
        try:
            hist = comfy.history(str(prompt_id))
        except Exception as exc:  # noqa: BLE001
            record["last_poll_error"] = repr(exc)
            record["updated_at"] = utc_now()
            self.store.write(record)
            return self.decorate(record)
        if prompt_id in hist:
            entry = hist[prompt_id]
            status = entry.get("status", {})
            record["comfy_status"] = status
            if status.get("completed") is True or status.get("status_str") == "success":
                record["status"] = "completed"
                artifacts = []
                for idx, item in enumerate(flatten_history_outputs(entry)):
                    if str(item.get("filename", "")).lower().endswith((".mp4", ".webm", ".mkv", ".mov")):
                        artifacts.append({"artifact_id": f"a{idx}", **item, "view_url": comfy.view_url(item)})
                record["artifacts"] = artifacts
                completed_at = record.setdefault("completed_at", utc_now())
                elapsed = _elapsed_seconds(str(record.get("created_at", "")), str(completed_at))
                if elapsed is not None:
                    record["timing"] = {"created_to_completed_s": elapsed}
            elif status.get("status_str") == "error":
                record["status"] = "failed"
            else:
                record["status"] = "running"
            record["history"] = entry
        else:
            record["status"] = "running" if record.get("status") == "queued" else record.get("status", "unknown")
        record["updated_at"] = utc_now()
        self.store.write(record)
        if record.get("status") in {"completed", "failed", "cancelled"}:
            self.pool.release(run_id)
        return self.decorate(record)

    def cancel(self, run_id: str) -> dict[str, Any]:
        record = self.store.read(run_id)
        if record.get("status") in TERMINAL_STATUSES:
            self.pool.release(run_id)
            return self.decorate(record)
        if record.get("prompt_id"):
            comfy = self.pool.client(self.pool.worker_for_record(record))
            record["cancel_response"] = comfy.interrupt()
        record["status"] = "cancelled"
        record["updated_at"] = utc_now()
        self.store.write(record)
        self.pool.release(run_id)
        return self.decorate(record)

    def decorate(self, record: dict[str, Any]) -> dict[str, Any]:
        copy = json.loads(json.dumps(record))
        worker = self.pool.worker_for_record(copy)
        comfy = self.pool.client(worker)
        for item in copy.get("artifacts", []):
            item["download_url"] = f"/api/runs/{copy['run_id']}/artifacts/{item['artifact_id']}/file"
        copy["worker_ws_url"] = comfy.websocket_url
        copy["advanced_canvas_url"] = worker.url + "/"
        return copy

    def proxy_artifact(self, run_id: str, artifact_id: str) -> tuple[str, bytes]:
        record = self.store.read(run_id)
        comfy = self.pool.client(self.pool.worker_for_record(record))
        for item in record.get("artifacts", []):
            if item.get("artifact_id") == artifact_id:
                with urllib.request.urlopen(comfy.view_url(item), timeout=120) as resp:
                    return resp.headers.get_content_type() or "application/octet-stream", resp.read()
        raise KeyError(artifact_id)


class Handler(BaseHTTPRequestHandler):
    service: StudioService

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_json(self, data: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def send_text(self, text: str, status: int = 200, ctype: str = "text/html; charset=utf-8") -> None:
        raw = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        try:
            if parsed.path == "/":
                return self.send_text(INDEX_HTML)
            if parsed.path == "/api/config":
                return self.send_json({"advanced_canvas_url": self.service._advanced_canvas_url(), "worker_pool": self.service.pool.status(include_health=False), "profiles": self.service.config.profiles})
            if parsed.path == "/api/workers":
                return self.send_json(self.service.workers())
            if parsed.path == "/api/health":
                return self.send_json(self.service.health())
            if parsed.path == "/api/assets/check":
                qs = parse_qs(parsed.query)
                return self.send_json(validate_assets(self.service.config.asset_manifest, compute_sha=qs.get("sha256", ["0"])[0] == "1"))
            if parsed.path == "/api/runs":
                return self.send_json({"runs": self.service.store.list_recent()})
            if len(parts) == 3 and parts[:2] == ["api", "runs"]:
                return self.send_json(self.service.refresh(parts[2]))
            if len(parts) == 6 and parts[:2] == ["api", "runs"] and parts[3] == "artifacts" and parts[5] == "file":
                ctype, raw = self.service.proxy_artifact(parts[2], parts[4])
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            return self.send_text("not found", status=404, ctype="text/plain")
        except Exception as exc:  # noqa: BLE001
            return self.send_json({"error": repr(exc)}, status=500)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        try:
            if parsed.path == "/api/runs":
                form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", "")})
                fields: dict[str, str] = {}
                files: dict[str, Path] = {}
                temp_dir = self.service.config.upload_root / f"upload-{uuid.uuid4().hex}"
                temp_dir.mkdir(parents=True, exist_ok=True)
                try:
                    for key in form.keys():
                        item = form[key]
                        if isinstance(item, list):
                            item = item[0]
                        if getattr(item, "filename", None):
                            suffix = Path(item.filename).suffix or ".bin"
                            safe_key = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in str(key)) or "upload"
                            dest = temp_dir / f"{safe_key}{suffix}"
                            with dest.open("wb") as f:
                                shutil.copyfileobj(item.file, f)
                            files[key] = dest
                        else:
                            fields[key] = item.value
                    return self.send_json(self.service.submit(fields, files), status=201)
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            if len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "cancel":
                return self.send_json(self.service.cancel(parts[2]))
            return self.send_text("not found", status=404, ctype="text/plain")
        except NoWorkerAvailable as exc:
            return self.send_json({"error": "no_worker_available", "reason": exc.reason, "pool": exc.pool_status}, status=503)
        except Exception as exc:  # noqa: BLE001
            return self.send_json({"error": repr(exc)}, status=400)


def run_server(config: StudioConfig | None = None) -> None:
    cfg = config or StudioConfig.from_env()
    service = StudioService(cfg)
    Handler.service = service
    httpd = ThreadingHTTPServer((cfg.studio_host, cfg.studio_port), Handler)
    print(f"H3 Studio listening on http://{cfg.studio_host}:{cfg.studio_port}")
    print(f"Worker Pool: {len(service.pool.workers)} configured worker(s), safe_concurrent_runs={service.pool.safe_concurrent_runs}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
