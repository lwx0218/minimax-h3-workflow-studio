#!/usr/bin/env python3
"""Run one bounded R1 MiniMax-H3 service/generation attempt and capture evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GIB = 1024**3


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def request_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: int = 30) -> tuple[int, bytes]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def meminfo() -> tuple[int, int, int]:
    values: dict[str, int] = {}
    with open("/proc/meminfo", encoding="ascii") as handle:
        for line in handle:
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024
    total = values["MemTotal"]
    available = values["MemAvailable"]
    return total, available, total - available


def process_group_rss(pgid: int) -> int:
    page_size = os.sysconf("SC_PAGE_SIZE")
    total = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="ascii")
            fields = stat[stat.rfind(")") + 2 :].split()
            if int(fields[2]) != pgid:
                continue
            resident_pages = int((entry / "statm").read_text(encoding="ascii").split()[1])
            total += resident_pages * page_size
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError, IndexError):
            continue
    return total


def gpu_sample() -> dict[int, tuple[int, int, float, str]]:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,memory.used,temperature.gpu,power.draw,pstate",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise RuntimeError(f"nvidia-smi sampling failed with exit {result.returncode}: {result.stderr.strip()}")
    samples: dict[int, tuple[int, int, float, str]] = {}
    for line in result.stdout.splitlines():
        fields = [item.strip() for item in line.split(",")]
        if len(fields) != 5:
            continue
        try:
            samples[int(fields[0])] = (int(fields[1]), int(fields[2]), float(fields[3]), fields[4])
        except ValueError:
            continue
    return samples


class ResourceMonitor(threading.Thread):
    def __init__(self, path: Path, pgid: int, visible_gpus: list[int], stop_event: threading.Event, abort_bytes: int):
        super().__init__(daemon=True)
        self.path = path
        self.pgid = pgid
        self.visible_gpus = visible_gpus
        self.stop_event = stop_event
        self.abort_bytes = abort_bytes
        self.safety_exceeded = threading.Event()
        self.monitor_failed = threading.Event()
        self.ready = threading.Event()
        self.monitor_error: str | None = None
        self.sample_count = 0
        self.peak_host_used = 0
        self.peak_process_rss = 0
        self.peak_gpu_mib = {gpu: 0 for gpu in visible_gpus}
        self.peak_temperature_c = {gpu: 0 for gpu in visible_gpus}

    def run(self) -> None:
        try:
            with self.path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "utc",
                        "host_total_bytes",
                        "host_available_bytes",
                        "host_used_bytes",
                        "process_group_rss_bytes",
                        "gpu_index",
                        "gpu_memory_used_mib",
                        "gpu_temperature_c",
                        "gpu_power_w",
                        "gpu_pstate",
                    ]
                )
                handle.flush()
                while not self.stop_event.is_set():
                    total, available, used = meminfo()
                    rss = process_group_rss(self.pgid)
                    gpu_values = gpu_sample()
                    missing_gpus = sorted(set(self.visible_gpus) - set(gpu_values))
                    if missing_gpus:
                        raise RuntimeError(f"nvidia-smi sample missing visible GPUs: {missing_gpus}")
                    self.peak_host_used = max(self.peak_host_used, used)
                    self.peak_process_rss = max(self.peak_process_rss, rss)
                    stamp = utc_now()
                    for gpu in self.visible_gpus:
                        memory, temperature, power, pstate = gpu_values[gpu]
                        self.peak_gpu_mib[gpu] = max(self.peak_gpu_mib[gpu], memory)
                        self.peak_temperature_c[gpu] = max(self.peak_temperature_c[gpu], temperature)
                        writer.writerow([stamp, total, available, used, rss, gpu, memory, temperature, power, pstate])
                    handle.flush()
                    self.sample_count += 1
                    self.ready.set()
                    if used >= self.abort_bytes:
                        self.safety_exceeded.set()
                        try:
                            os.killpg(self.pgid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        return
                    self.stop_event.wait(1)
        except Exception as error:
            self.monitor_error = f"{type(error).__name__}: {error}"
            self.monitor_failed.set()
            try:
                with self.path.open("a", newline="", encoding="utf-8") as handle:
                    csv.writer(handle).writerow([utc_now(), "monitor_error", self.monitor_error])
            except OSError:
                pass
            try:
                os.killpg(self.pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def parse_official_request(path: Path, model_path: str) -> tuple[dict[str, Any], str]:
    source = path.read_text(encoding="utf-8")
    match = re.search(r"<<'JSON'\n(?P<body>\{.*?\})\nJSON", source, flags=re.DOTALL)
    if not match:
        raise ValueError(f"could not find official JSON heredoc in {path}")
    source_request = json.loads(match.group("body"))
    prompt = source_request["prompt"]
    request = {
        "task": "t2va",
        "prompt": prompt,
        "conditions": [],
        "target": {"short_edge": 768, "aspect_ratio": "16:9", "duration_seconds": 5.0},
        "seed": 0,
        "model": model_path,
        "seconds": 5,
        "num_outputs_per_prompt": 1,
        "num_inference_steps": 50,
        "flow_shift": 12.0,
        "audio_flow_shift": 3.0,
    }
    return request, hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def canonical_request_sha256(request: dict[str, Any], model_placeholder: str) -> str:
    normalized = dict(request)
    normalized["model"] = model_placeholder
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sanitized_command(command: list[str], model_path: str, model_path_placeholder: str, project_root: Path) -> str:
    rendered = " ".join(subprocess.list2cmdline([part]) for part in command)
    rendered = rendered.replace(model_path, model_path_placeholder)
    rendered = rendered.replace(str(project_root), ".")
    return rendered


def command_option(command: list[str], name: str) -> str | None:
    for index, part in enumerate(command):
        if part == name and index + 1 < len(command):
            return command[index + 1]
        if part.startswith(name + "="):
            return part.split("=", 1)[1]
    return None


def unexpected_sensitive_environment(environment: dict[str, str], expected: dict[str, str]) -> list[str]:
    prefixes = ("NCCL_", "TORCH_NCCL_", "SGLANG_", "MINIMAX_H3_", "COMFY_KITCHEN_", "KITCHEN_")
    exact_names = {"CUDA_VISIBLE_DEVICES", "PYTORCH_CUDA_ALLOC_CONF", "TORCHINDUCTOR_CACHE_DIR", "TRITON_CACHE_DIR"}
    return sorted(
        name
        for name in environment
        if (name.startswith(prefixes) or name in exact_names) and name not in expected
    )


def ensure_monitor_healthy(monitor: ResourceMonitor, phase: str) -> None:
    if monitor.monitor_failed.is_set():
        raise RuntimeError(f"resource monitor failed during {phase}: {monitor.monitor_error}")
    if monitor.safety_exceeded.is_set():
        raise RuntimeError(f"host memory abort threshold reached during {phase}")
    if not monitor.is_alive():
        raise RuntimeError(f"resource monitor stopped unexpectedly during {phase}")


def stop_monitor_for_success(monitor: ResourceMonitor, stop_event: threading.Event, timeout: int = 30) -> None:
    stop_event.set()
    monitor.join(timeout=timeout)
    if monitor.is_alive():
        raise RuntimeError("resource monitor did not stop before success gate")
    if monitor.monitor_failed.is_set():
        raise RuntimeError(f"resource monitor failed before success gate: {monitor.monitor_error}")
    if monitor.safety_exceeded.is_set():
        raise RuntimeError("host memory abort threshold reached before success gate")
    if monitor.sample_count < 1:
        raise RuntimeError("resource monitor recorded no samples before success gate")


def prepare_attempt_root(output_root: Path, attempt_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", attempt_id):
        raise ValueError(f"invalid attempt ID: {attempt_id!r}")
    output_root.mkdir(parents=True, exist_ok=True)
    attempt_root = (output_root / attempt_id).resolve()
    if not attempt_root.is_relative_to(output_root):
        raise ValueError(f"attempt path escapes output root: {attempt_root}")
    if attempt_root.exists():
        raise FileExistsError(f"attempt evidence already exists and cannot be overwritten: {attempt_root}")
    attempt_root.mkdir()
    return attempt_root


def session_process_ids(session_id: int) -> list[int]:
    result = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="ascii")
            fields = stat[stat.rfind(")") + 2 :].split()
            if int(fields[3]) == session_id:
                result.append(int(entry.name))
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError, IndexError):
            continue
    return sorted(result)


def stop_process(process: subprocess.Popen[bytes], grace_seconds: int = 30) -> int | None:
    session_id = process.pid
    members = session_process_ids(session_id)
    for pid in members:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline and session_process_ids(session_id):
        time.sleep(0.25)
    for pid in session_process_ids(session_id):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    return process.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--visible-gpus", required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--model-path-placeholder", default="$H3_MODEL_PATH")
    parser.add_argument("--request-source", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--ffprobe", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--authorization-manifest", required=True, type=Path)
    parser.add_argument("--port", type=int, default=30010)
    parser.add_argument("--load-timeout-seconds", type=int, default=3600)
    parser.add_argument("--generation-timeout-seconds", type=int, default=3600)
    parser.add_argument("--host-memory-limit-gib", type=int, default=235)
    parser.add_argument("--host-memory-abort-gib", type=int, default=230)
    parser.add_argument("server_command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.server_command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("server command is required after --")

    project_root = Path.cwd().resolve()
    output_root = args.output_root.resolve()
    visible_gpus = [int(item) for item in args.visible_gpus.split(",")]
    authorization_path = args.authorization_manifest.resolve()
    if not authorization_path.is_relative_to(project_root):
        raise ValueError("authorization manifest must be inside the project")
    authorization_data = json.loads(authorization_path.read_text(encoding="utf-8"))
    authorization_list = authorization_data.get("executions", [])
    authorization_ids = [entry.get("id") for entry in authorization_list]
    if len(authorization_ids) != len(set(authorization_ids)):
        raise ValueError("authorization manifest contains duplicate execution IDs")
    authorization = next((entry for entry in authorization_list if entry.get("id") == args.attempt_id), None)
    if authorization is None or authorization.get("state") != "authorized_pending":
        raise ValueError(f"attempt is not authorized_pending in manifest: {args.attempt_id}")
    launch_contract = authorization.get("launch_contract")
    if not isinstance(launch_contract, dict):
        raise ValueError(f"attempt lacks launch_contract: {args.attempt_id}")
    if command != launch_contract.get("server_argv"):
        raise ValueError("server argv does not exactly match the authorized launch contract")
    if visible_gpus != launch_contract.get("visible_gpus"):
        raise ValueError("visible GPUs do not exactly match the authorized launch contract")
    exact_controls = {
        "load_timeout_seconds": args.load_timeout_seconds,
        "generation_timeout_seconds": args.generation_timeout_seconds,
        "host_memory_limit_gib": args.host_memory_limit_gib,
        "host_memory_abort_gib": args.host_memory_abort_gib,
        "port": args.port,
    }
    if exact_controls != launch_contract.get("controls"):
        raise ValueError("timeouts/memory controls do not exactly match the authorized launch contract")
    expected_environment = launch_contract.get("environment", {})
    actual_environment = {name: os.environ.get(name) for name in expected_environment}
    if actual_environment != expected_environment:
        raise ValueError("process environment does not exactly match the authorized launch contract")
    if unexpected := unexpected_sensitive_environment(dict(os.environ), expected_environment):
        raise ValueError(f"unexpected contract-sensitive environment variables: {unexpected}")
    for argument_name, supplied_path in (
        ("output_root", args.output_root),
        ("model_path", Path(args.model_path)),
        ("request_source", args.request_source),
        ("ffprobe", args.ffprobe),
        ("ffmpeg", args.ffmpeg),
    ):
        expected_path = (project_root / launch_contract[argument_name]).resolve()
        if supplied_path.resolve() != expected_path:
            raise ValueError(f"{argument_name} does not match the authorized path")
        if argument_name in {"output_root", "ffprobe", "ffmpeg"} and not expected_path.is_relative_to(project_root):
            raise ValueError(f"{argument_name} must resolve inside the project")
    request_body, prompt_hash = parse_official_request(args.request_source, args.model_path)
    if prompt_hash != launch_contract.get("prompt_sha256"):
        raise ValueError("request prompt hash does not match the authorized launch contract")
    canonical_request_hash = canonical_request_sha256(request_body, args.model_path_placeholder)
    if canonical_request_hash != launch_contract.get("canonical_request_sha256"):
        raise ValueError("canonical request does not match the authorized launch contract")
    provenance = launch_contract.get("provenance", {})
    source_contract = provenance.get("sglang_source")
    if source_contract:
        source_path = (project_root / source_contract["path"]).resolve()
        source_head = subprocess.run(
            ["git", "-C", str(source_path), "rev-parse", "HEAD"], check=False, capture_output=True, text=True, timeout=30
        )
        source_status = subprocess.run(
            ["git", "-C", str(source_path), "status", "--porcelain"], check=False, capture_output=True, text=True, timeout=30
        )
        if source_head.returncode != 0 or source_head.stdout.strip() != source_contract["commit"]:
            raise ValueError("SGLang source commit does not match launch provenance")
        if source_status.returncode != 0 or source_status.stdout.strip():
            raise ValueError("SGLang source tree is not clean")
    model_contract = provenance.get("model_files", {})
    observed_model_hashes = {}
    for relative_name, expected_hash in model_contract.items():
        model_file = (Path(args.model_path) / relative_name).resolve()
        observed_hash = hashlib.sha256(model_file.read_bytes()).hexdigest()
        if observed_hash != expected_hash:
            raise ValueError(f"model fingerprint mismatch: {relative_name}")
        observed_model_hashes[relative_name] = observed_hash
    attempt_root = prepare_attempt_root(output_root, args.attempt_id)
    recorded_environment = {}
    for name in (
        "NCCL_NET",
        "NCCL_IB_DISABLE",
        "NCCL_P2P_DISABLE",
        "NCCL_CUMEM_ENABLE",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
    ):
        if name in os.environ:
            recorded_environment[name] = os.environ[name]
    metadata: dict[str, Any] = {
        "attempt_id": args.attempt_id,
        "started_at": utc_now(),
        "visible_gpus": visible_gpus,
        "environment": recorded_environment,
        "command": sanitized_command(command, args.model_path, args.model_path_placeholder, project_root),
        "load_timeout_seconds": args.load_timeout_seconds,
        "generation_timeout_seconds": args.generation_timeout_seconds,
        "host_memory_limit_bytes": args.host_memory_limit_gib * GIB,
        "host_memory_abort_bytes": args.host_memory_abort_gib * GIB,
        "status": "starting",
        "generation_submitted": False,
    }
    metadata["prompt_sha256"] = prompt_hash
    metadata["canonical_request_sha256"] = canonical_request_hash
    metadata["authorization_manifest"] = str(authorization_path.relative_to(project_root))
    metadata["authorization_state_at_launch"] = authorization["state"]
    metadata["launch_provenance"] = {
        "sglang_source": source_contract,
        "model_files": observed_model_hashes,
    }
    (attempt_root / "request.json").write_text(json.dumps(request_body, indent=2) + "\n", encoding="utf-8")

    environment = os.environ.copy()
    environment["CUDA_VISIBLE_DEVICES"] = args.visible_gpus
    environment["PYTHONUNBUFFERED"] = "1"
    tool_directories = [str(args.ffprobe.resolve().parent), str(args.ffmpeg.resolve().parent)]
    environment["PATH"] = os.pathsep.join(dict.fromkeys(tool_directories + [environment.get("PATH", "")]))
    server_log_path = attempt_root / "server.log"
    stop_event = threading.Event()
    process: subprocess.Popen[bytes] | None = None
    monitor: ResourceMonitor | None = None
    result_code = 1

    try:
        if not 0 < args.host_memory_abort_gib < args.host_memory_limit_gib:
            raise ValueError("host memory abort threshold must be positive and below the safety limit")
        server_output_value = command_option(command, "--output-path")
        if not server_output_value:
            raise ValueError("server command must set --output-path inside the R1 output root")
        server_output_path = Path(server_output_value)
        if not server_output_path.is_absolute():
            server_output_path = (project_root / server_output_path).resolve()
        else:
            server_output_path = server_output_path.resolve()
        if not server_output_path.is_relative_to(output_root):
            raise ValueError(f"server output path escapes R1 output root: {server_output_path}")
        server_output_path.mkdir(parents=True, exist_ok=True)
        metadata["server_output_path"] = str(server_output_path.relative_to(project_root))

        tool_versions = {}
        for tool in ("ffprobe", "ffmpeg"):
            executable = shutil.which(tool, path=environment["PATH"])
            supplied_tool = (args.ffprobe if tool == "ffprobe" else args.ffmpeg).resolve()
            if executable is None:
                raise RuntimeError(f"{tool} is absent from the exact server PATH")
            if Path(executable).resolve() != supplied_tool:
                raise RuntimeError(f"{tool} PATH resolution does not match the supplied project-local executable")
            check = subprocess.run(
                [tool, "-version"], env=environment, check=False, capture_output=True, text=True, timeout=30
            )
            if check.returncode != 0:
                raise RuntimeError(f"{tool} preflight failed with exit {check.returncode}")
            tool_versions[tool] = check.stdout.splitlines()[0]
        metadata["server_tool_preflight"] = tool_versions

        with server_log_path.open("wb") as server_log:
            process = subprocess.Popen(
                command,
                stdout=server_log,
                stderr=subprocess.STDOUT,
                env=environment,
                start_new_session=True,
            )
            metadata["server_pid"] = process.pid
            monitor = ResourceMonitor(
                attempt_root / "resources.csv",
                process.pid,
                visible_gpus,
                stop_event,
                args.host_memory_abort_gib * GIB,
            )
            monitor.start()
            if not monitor.ready.wait(timeout=30):
                if monitor.monitor_failed.is_set():
                    raise RuntimeError(f"resource monitor failed during setup: {monitor.monitor_error}")
                if not monitor.is_alive():
                    raise RuntimeError("resource monitor stopped before its first sample")
                raise RuntimeError("resource monitor did not become ready within 30 seconds")
            ensure_monitor_healthy(monitor, "service setup")
            base_url = f"http://127.0.0.1:{args.port}"
            load_started = time.monotonic()
            liveness_seen = False
            while True:
                ensure_monitor_healthy(monitor, "service load")
                if process.poll() is not None:
                    raise RuntimeError(f"server exited during load with code {process.returncode}")
                elapsed = time.monotonic() - load_started
                if elapsed > args.load_timeout_seconds:
                    raise TimeoutError("service load timeout")
                try:
                    live_status, live_body = request_json("GET", base_url + "/liveness", timeout=5)
                    if live_status == 200:
                        liveness_seen = True
                        (attempt_root / "liveness.txt").write_bytes(live_body)
                    health_status, health_body = request_json("GET", base_url + "/health", timeout=5)
                    if health_status == 200:
                        (attempt_root / "health.txt").write_bytes(health_body)
                        break
                except (URLError, TimeoutError):
                    pass
                time.sleep(5)
            metadata["liveness_seen"] = liveness_seen
            metadata["load_elapsed_seconds"] = round(time.monotonic() - load_started, 3)
            metadata["health_status"] = 200

            capability: dict[str, Any] = {}
            for name, endpoint in (("models", "/v1/models"), ("openapi", "/openapi.json")):
                status, body = request_json("GET", base_url + endpoint, timeout=30)
                capability[name] = {"status": status, "bytes": len(body)}
                (attempt_root / f"{name}.json").write_bytes(body)
            openapi = json.loads((attempt_root / "openapi.json").read_text(encoding="utf-8"))
            paths = openapi.get("paths", {})
            capability["video_endpoint_present"] = "/v1/videos" in paths
            metadata["capability"] = capability
            if capability["models"]["status"] != 200 or not capability["video_endpoint_present"]:
                raise RuntimeError(f"capability probe failed: {capability}")

            submit_started = time.monotonic()
            status, body = request_json("POST", base_url + "/v1/videos", request_body, timeout=60)
            (attempt_root / "submit-response.json").write_bytes(body)
            metadata["submit_http_status"] = status
            if status < 200 or status >= 300:
                raise RuntimeError(f"generation request rejected with HTTP {status}")
            response = json.loads(body)
            video_id = response.get("id")
            if not video_id:
                raise RuntimeError("generation response did not include id")
            metadata["generation_submitted"] = True
            metadata["video_id"] = video_id
            terminal_status = ""
            with (attempt_root / "status.ndjson").open("w", encoding="utf-8") as status_log:
                while True:
                    ensure_monitor_healthy(monitor, "generation")
                    if process.poll() is not None:
                        raise RuntimeError(f"server exited during generation with code {process.returncode}")
                    elapsed = time.monotonic() - submit_started
                    if elapsed > args.generation_timeout_seconds:
                        raise TimeoutError("generation timeout")
                    poll_status, poll_body = request_json("GET", base_url + f"/v1/videos/{video_id}", timeout=30)
                    record: dict[str, Any] = {"utc": utc_now(), "http_status": poll_status}
                    try:
                        payload = json.loads(poll_body)
                        record["body"] = payload
                        terminal_status = str(payload.get("status", "")).lower()
                        metadata["terminal_status"] = terminal_status
                        metadata["terminal_response"] = payload
                        metadata["generation_elapsed_seconds"] = round(time.monotonic() - submit_started, 3)
                    except json.JSONDecodeError:
                        record["body_text"] = poll_body.decode("utf-8", errors="replace")
                    status_log.write(json.dumps(record) + "\n")
                    status_log.flush()
                    if terminal_status in {"completed", "succeeded"}:
                        break
                    if terminal_status in {"failed", "cancelled", "canceled"}:
                        raise RuntimeError(f"generation entered terminal status {terminal_status}")
                    time.sleep(5)
            metadata["terminal_status"] = terminal_status
            metadata["generation_elapsed_seconds"] = round(time.monotonic() - submit_started, 3)

            content_status, content = request_json("GET", base_url + f"/v1/videos/{video_id}/content", timeout=300)
            metadata["content_http_status"] = content_status
            output_path = attempt_root / "probe.mp4"
            output_path.write_bytes(content)
            metadata["output_bytes"] = len(content)
            metadata["output_sha256"] = hashlib.sha256(content).hexdigest()
            if content_status < 200 or content_status >= 300 or not content:
                raise RuntimeError(f"content endpoint failed with HTTP {content_status} and {len(content)} bytes")

            probe = subprocess.run(
                [str(args.ffprobe), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
            (attempt_root / "ffprobe.json").write_text(probe.stdout, encoding="utf-8")
            (attempt_root / "ffprobe.stderr.txt").write_text(probe.stderr, encoding="utf-8")
            metadata["ffprobe_exit"] = probe.returncode
            if probe.returncode != 0:
                raise RuntimeError("ffprobe failed")
            probe_data = json.loads(probe.stdout)
            streams = probe_data.get("streams", [])
            video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
            audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
            metadata["video_stream_count"] = len(video_streams)
            metadata["audio_stream_count"] = len(audio_streams)
            metadata["ffprobe_summary"] = {
                "format_name": probe_data.get("format", {}).get("format_name"),
                "duration_seconds": probe_data.get("format", {}).get("duration"),
                "video": video_streams[0] if video_streams else None,
                "audio": audio_streams[0] if audio_streams else None,
            }
            if not video_streams or not audio_streams:
                raise RuntimeError("MP4 does not contain both video and audio streams")

            decode = subprocess.run(
                [str(args.ffmpeg), "-v", "error", "-i", str(output_path), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
                check=False,
                capture_output=True,
                text=True,
                timeout=600,
            )
            (attempt_root / "decode.stderr.txt").write_text(decode.stderr, encoding="utf-8")
            metadata["decode_exit"] = decode.returncode
            if decode.returncode != 0:
                raise RuntimeError("video/audio decode check failed")
            stop_monitor_for_success(monitor, stop_event)

            metadata["status"] = "succeeded"
            result_code = 0
    except Exception as error:
        metadata["status"] = "failed"
        metadata["error"] = f"{type(error).__name__}: {error}"
    finally:
        if process is not None:
            metadata["server_exit_after_stop"] = stop_process(process)
        stop_event.set()
        if monitor is not None:
            monitor.join(timeout=30)
            metadata["peak_host_used_bytes"] = monitor.peak_host_used
            metadata["peak_process_group_rss_bytes"] = monitor.peak_process_rss
            metadata["peak_gpu_memory_mib"] = monitor.peak_gpu_mib
            metadata["peak_gpu_temperature_c"] = monitor.peak_temperature_c
            metadata["memory_abort_triggered"] = monitor.safety_exceeded.is_set()
            metadata["memory_safety_exceeded"] = monitor.peak_host_used >= args.host_memory_limit_gib * GIB
            metadata["resource_monitor_failed"] = monitor.monitor_failed.is_set()
            metadata["resource_monitor_error"] = monitor.monitor_error
        try:
            cleanup_apps = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_memory", "--format=csv,noheader"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            cleanup_gpus = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,memory.used,memory.free,temperature.gpu", "--format=csv,noheader,nounits"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if cleanup_apps.returncode != 0 or cleanup_gpus.returncode != 0:
                raise RuntimeError("post-stop nvidia-smi snapshot failed")
            compute_apps = cleanup_apps.stdout.splitlines()
            gpu_lines = cleanup_gpus.stdout.splitlines()
            if compute_apps:
                raise RuntimeError(f"post-stop residual compute processes: {compute_apps}")
            gpu_memory = {int(line.split(",")[0].strip()): int(line.split(",")[1].strip()) for line in gpu_lines}
            elevated = {gpu: gpu_memory.get(gpu) for gpu in visible_gpus if gpu_memory.get(gpu, 10**9) > 10}
            if elevated:
                raise RuntimeError(f"post-stop visible GPU memory remains elevated: {elevated}")
            metadata["post_stop_gpu_snapshot"] = {
                "captured_at": utc_now(),
                "compute_apps": compute_apps,
                "gpus": gpu_lines,
            }
        except Exception as cleanup_error:
            metadata["post_stop_gpu_snapshot_error"] = f"{type(cleanup_error).__name__}: {cleanup_error}"
            if metadata.get("status") == "succeeded":
                metadata["status"] = "failed"
                metadata["error"] = metadata["post_stop_gpu_snapshot_error"]
                result_code = 1
        if server_log_path.exists():
            server_log = server_log_path.read_text(encoding="utf-8", errors="replace")
            patterns = re.compile(r"(?i)(out of memory|\boom\b|xid|nccl.*(?:error|failed)|traceback|segmentation fault|segfault)")
            metadata["server_error_markers"] = sorted(set(match.group(0) for match in patterns.finditer(server_log)))
        metadata["finished_at"] = utc_now()
        (attempt_root / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(metadata, indent=2, sort_keys=True))
    return result_code


if __name__ == "__main__":
    sys.exit(main())
