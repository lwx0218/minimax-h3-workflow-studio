#!/usr/bin/env python3
"""Verify the static R1 blocked decision and, optionally, local runtime evidence."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
GIB = 1024**3
CANONICAL_REQUEST_SHA256 = "9f45f24ffa888ce021cc5615240ff42ed97e42fbbfdc66080f6148907f58ab8b"
G4_LAUNCH_CONTRACT_SHA256 = "1b60cfb1a6cd0efab5a365628fae5faf964ee4dea71d9c3b50855528247679af"
G4_CORRECTION_CONTRACT_SHA256 = "d82467acda98bfa82b0d1bd53d9317891bed2262838d0f2d13381b74fab5fdbe"
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FORBIDDEN_CANDIDATE_RE = re.compile(
    r"(^|/)(?:\.env\.local|var/(?!README\.md)|\.venv(?:-h3)?/)|"
    r"\.(?:safetensors|ckpt|pt|pth|bin|onnx|gguf|engine|sqlite3?|db|"
    r"mp4|mov|webm|mkv|avi|wav|mp3|m4a|flac)$"
)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def contains_argv_sequence(argv: list[str], expected: list[str]) -> bool:
    if not expected:
        return True
    width = len(expected)
    return any(argv[index : index + width] == expected for index in range(len(argv) - width + 1))


def candidate_names() -> list[str]:
    result = run("git", "ls-files", "--cached", "--others", "--exclude-standard")
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return sorted(line for line in result.stdout.splitlines() if line)


def verify_static(errors: list[str]) -> None:
    baseline = run("git", "merge-base", "--is-ancestor", "aa2c2b1", "HEAD")
    require(baseline.returncode == 0, "HEAD does not contain aa2c2b1", errors)
    print(f"CHECK baseline_ancestor exit={baseline.returncode}")

    diff = run("git", "diff", "--check")
    require(diff.returncode == 0, f"git diff --check failed: {diff.stdout}{diff.stderr}", errors)
    print(f"CHECK diff_whitespace exit={diff.returncode}")

    names = candidate_names()
    print(f"CHECK candidate_list count={len(names)}")
    for name in names:
        if FORBIDDEN_CANDIDATE_RE.search(name):
            errors.append(f"forbidden candidate path: {name}")
            continue
        path = ROOT / name
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"unknown binary candidate is not allowlisted: {name}")
            continue
        except OSError as error:
            errors.append(f"cannot inspect candidate {name}: {error}")
            continue
        host_path_pattern = re.compile("/" + r"(?:home|Users)/[^\s)`\"']+|[A-Z]:[\\/][^\s]+")
        if host_path_pattern.search(text):
            errors.append(f"host absolute path in candidate: {name}")
        for line_number, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                errors.append(f"trailing whitespace: {name}:{line_number}")
        if name.endswith(".md"):
            for target in MARKDOWN_LINK_RE.findall(text):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                relative = target.split("#", 1)[0]
                if relative and not (path.parent / relative).resolve().exists():
                    errors.append(f"missing markdown target: {name} -> {target}")

    for ignored_path in (
        ".env.local",
        ".venv-h3/bin/python",
        "var/cache/r1-feasibility/venv-lock2/bin/python",
        "var/logs/r1-feasibility/test.log",
        "var/outputs/r1-feasibility/test.mp4",
        "var/tmp/r1-feasibility/test.tmp",
    ):
        ignored = run("git", "check-ignore", "--no-index", "--", ignored_path)
        require(ignored.returncode == 0, f"expected ignored path: {ignored_path}", errors)
        print(f"CHECK ignored:{ignored_path} exit={ignored.returncode}")

    plan = (ROOT / "operations/planning/initialization-plan.md").read_text(encoding="utf-8")
    report = (ROOT / "operations/reviews/2026-08-21-r1-feasibility-report.md").read_text(encoding="utf-8")
    work_log = (ROOT / "operations/work_logs/2026-08-21-r1-h3-feasibility.md").read_text(encoding="utf-8")
    require("| R1 | H3 本地真实 T2VA 可行性 | `blocked` |" in plan, "R1 ledger is not blocked", errors)
    require("Round Status：`blocked`" in report, "feasibility report lacks blocked round status", errors)
    require("Feasibility Decision：`feasible_with_constraints`" in report, "feasibility report lacks successful constrained decision", errors)
    require("Status：`blocked`" in work_log, "work log lacks blocked status", errors)
    require("not verified" in report, "report does not state missing ffprobe result", errors)
    require("236.91 GiB" in report and "safety-line breach" in report, "B1 breach is not explicitly disclosed", errors)
    require("235.87 GiB" in report and "G4-TP4Q" in report, "G4 safety breach is not explicitly disclosed", errors)
    require("project-root `outputs/`" in report, "legacy output-path deviation is not disclosed", errors)

    manifest_path = ROOT / "operations/reviews/r1-attempt-manifest.json"
    require(manifest_path.is_file(), "missing R1 attempt manifest", errors)
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        executions = manifest.get("executions", [])
        execution_ids = [entry.get("id") for entry in executions]
        require(len(execution_ids) == len(set(execution_ids)), "manifest contains duplicate execution IDs", errors)
        slots = [entry for entry in executions if entry.get("kind") == "profile_slot"]
        exceptions = [entry for entry in executions if entry.get("kind") == "owner_exception_profile_slot"]
        followups = [entry for entry in executions if entry.get("kind") == "owner_authorized_performance_followup"]
        corrections = [entry for entry in executions if entry.get("kind") == "owner_authorized_performance_correction"]
        require(len(slots) == 6, f"manifest must preserve exactly 6 original profile slots, found {len(slots)}", errors)
        require({entry.get("profile") for entry in slots} == {"A", "B", "C"}, "manifest profile set mismatch", errors)
        require(len(exceptions) == 1 and exceptions[0].get("id") == "C3-owner-exception", "manifest must contain exactly the authorized C3 exception", errors)
        require(exceptions[0].get("state") == "executed", "C3 authorization state is invalid", errors)
        require(len(followups) == 1 and followups[0].get("id") == "G4-TP4Q", "manifest must contain exactly the authorized 4-GPU follow-up", errors)
        require(followups[0].get("state") in {"authorized_pending", "executed"}, "4-GPU follow-up state is invalid", errors)
        if len(followups) == 1:
            g4 = followups[0]
            contract = g4.get("launch_contract", {})
            contract_digest = hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
            require(contract_digest == G4_LAUNCH_CONTRACT_SHA256, "G4 complete launch contract digest mismatch", errors)
            require(contract.get("canonical_request_sha256") == CANONICAL_REQUEST_SHA256, "G4 canonical request digest mismatch", errors)
            argv = contract.get("server_argv", [])
            required_sequences = (
                ["--backend", "sglang"],
                ["--num-gpus", "4"],
                ["--tp-size", "4"],
                ["--ulysses-degree", "1"],
                ["--encoder-parallel", "fold"],
                ["--quantization", "kitchen_int8"],
                ["--output-path", "./var/outputs/r1-feasibility/G4-TP4Q/server"],
            )
            require(all(contains_argv_sequence(argv, sequence) for sequence in required_sequences), "G4 exact topology/backend argv contract mismatch", errors)
            require(contract.get("visible_gpus") == [0, 1, 2, 3], "G4 visible GPU contract mismatch", errors)
            require(contract.get("controls") == {"load_timeout_seconds": 3600, "generation_timeout_seconds": 3600, "host_memory_limit_gib": 235, "host_memory_abort_gib": 230, "port": 30010}, "G4 timeout/memory contract mismatch", errors)
            require(contract.get("environment") == {"NCCL_NET": "Socket", "NCCL_IB_DISABLE": "1", "NCCL_P2P_DISABLE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}, "G4 environment contract mismatch", errors)
            require(contract.get("provenance", {}).get("sglang_source", {}).get("commit") == "44806dc507835746b67abebad041726c422030ea", "G4 SGLang provenance mismatch", errors)
            require(set(contract.get("provenance", {}).get("model_files", {})) == {"model_index.json", "configuration.json", "FL2VA/model_index.json"}, "G4 model fingerprint set mismatch", errors)
        require(len(corrections) == 1 and corrections[0].get("id") == "G4-TP4Q-adaln", "manifest must contain exactly one G4 correction", errors)
        require(corrections[0].get("state") in {"authorized_pending", "executed", "preflight_rejected"}, "G4 correction state is invalid", errors)
        if len(corrections) == 1:
            correction_contract = corrections[0].get("launch_contract", {})
            correction_digest = hashlib.sha256(json.dumps(correction_contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
            require(correction_digest == G4_CORRECTION_CONTRACT_SHA256, "G4 correction complete contract digest mismatch", errors)
            correction_argv = correction_contract.get("server_argv", [])
            require(contains_argv_sequence(correction_argv, ["--minimax-h3-adaln-online", "true"]), "G4 correction AdaLN flag missing", errors)
            require(correction_contract.get("controls", {}).get("host_memory_abort_gib") == 220, "G4 correction early-abort margin mismatch", errors)
            incompatible_quant_adaln = contains_argv_sequence(correction_argv, ["--quantization", "kitchen_int8"]) and contains_argv_sequence(correction_argv, ["--minimax-h3-adaln-online", "true"])
            if corrections[0].get("state") == "preflight_rejected":
                require(incompatible_quant_adaln and "rejects AdaLN online" in corrections[0].get("preflight_decision", ""), "G4 rejected correction lacks incompatibility disposition", errors)
            else:
                require(not incompatible_quant_adaln, "authorized/executed G4 contract uses incompatible kitchen_int8 + AdaLN online", errors)

    locks = sorted((ROOT / "operations/reviews").glob("r1-dependency-lock-*.txt"))
    require(len(locks) == 2, f"expected exactly 2 dependency locks, found {len(locks)}", errors)
    if len(locks) == 2:
        lock1 = locks[0].read_text(encoding="utf-8")
        lock2 = locks[1].read_text(encoding="utf-8")
        require("sglang==0.5.17" in lock1 and "torch==2.11.0" in lock1, "lock 1 key versions missing", errors)
        require("44806dc507835746b67abebad041726c422030ea" in lock2, "lock 2 source commit missing", errors)
        require("torch==2.13.0" in lock2 and "comfy-kitchen==0.2.31" in lock2, "lock 2 key versions missing", errors)
    print(f"CHECK dependency_locks count={len(locks)}")

    compile_result = run(
        sys.executable,
        "-m",
        "py_compile",
        "scripts/run_r1_h3_attempt.py",
        "scripts/verify_r1.py",
        "scripts/test_r1_hardening.py",
        "scripts/verify_r1_media.py",
    )
    require(compile_result.returncode == 0, f"Python compile failed: {compile_result.stderr}", errors)
    print(f"CHECK python_compile exit={compile_result.returncode}")

    hardening_tests = run(sys.executable, "scripts/test_r1_hardening.py")
    require(hardening_tests.returncode == 0, f"R1 hardening tests failed: {hardening_tests.stdout}{hardening_tests.stderr}", errors)
    print(f"CHECK hardening_tests exit={hardening_tests.returncode}")


def verify_runtime(errors: list[str]) -> None:
    root = ROOT / "var/outputs/r1-feasibility"
    manifest = json.loads((ROOT / "operations/reviews/r1-attempt-manifest.json").read_text(encoding="utf-8"))
    execution_list = manifest["executions"]
    execution_ids = [entry["id"] for entry in execution_list]
    require(len(execution_ids) == len(set(execution_ids)), "manifest contains duplicate execution IDs", errors)
    if len(execution_ids) != len(set(execution_ids)):
        return
    non_runtime_states = {"authorized_pending", "preflight_rejected"}
    pending = {entry["id"]: entry for entry in execution_list if entry.get("state") in non_runtime_states}
    entries = {entry["id"]: entry for entry in execution_list if entry.get("state") not in non_runtime_states}
    discovered = {
        path.parent.name: path
        for path in root.glob("*/metadata.json")
    }
    require(not (set(discovered) & set(pending)), f"pending execution already has runtime evidence: {sorted(set(discovered) & set(pending))}", errors)
    require(set(discovered) == set(entries), f"runtime execution set mismatch: discovered={sorted(discovered)} expected={sorted(entries)}", errors)
    if set(discovered) != set(entries) or set(discovered) & set(pending):
        return

    metadata = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in discovered.items()}
    prompt_hash = manifest["prompt_sha256"]
    for name, entry in entries.items():
        item = metadata[name]
        command = item.get("command", "")
        argv = shlex.split(command)
        require(item.get("attempt_id") == name, f"duplicate/mismatched attempt id: directory={name} metadata={item.get('attempt_id')}", errors)
        require(item.get("visible_gpus") == entry["visible_gpus"], f"visible GPUs mismatch for {name}", errors)
        require(item.get("generation_submitted") is entry["generation_submitted"], f"generation submission mismatch for {name}", errors)
        require(item.get("status") == entry["expected_status"], f"status mismatch for {name}", errors)
        require(item.get("prompt_sha256") == prompt_hash, f"prompt hash mismatch for {name}", errors)
        require(item.get("load_timeout_seconds") == 3600, f"load timeout mismatch for {name}", errors)
        require(item.get("generation_timeout_seconds") == 3600, f"generation timeout mismatch for {name}", errors)
        require(contains_argv_sequence(argv, ["--model-variant", "fl2va"]), f"FL2VA variant missing for {name}", errors)
        require(contains_argv_sequence(argv, ["--enable-torch-compile", "false"]), f"torch compile is not disabled for {name}", errors)
        for token in entry.get("required_command_tokens", []):
            required_argv = shlex.split(token)
            require(contains_argv_sequence(argv, required_argv), f"required argv sequence missing for {name}: {required_argv}", errors)
        for token in entry.get("forbidden_command_tokens", []):
            forbidden_argv = shlex.split(token)
            require(not contains_argv_sequence(argv, forbidden_argv), f"forbidden argv sequence in {name}: {forbidden_argv}", errors)
        if entry["lock"] == 1:
            require("venv-lock2" not in command, f"lock mapping mismatch for {name}: expected lock 1", errors)
        else:
            require("venv-lock2" in command, f"lock mapping mismatch for {name}: expected lock 2", errors)
        if expected := entry.get("expected_error_contains"):
            require(expected in item.get("error", ""), f"expected error missing for {name}: {expected}", errors)
        if expected_terminal := entry.get("expected_terminal_status"):
            require(item.get("terminal_status") == expected_terminal, f"terminal status mismatch for {name}", errors)
        if expected_checksum := entry.get("expected_output_sha256"):
            require(item.get("output_sha256") == expected_checksum, f"output checksum metadata mismatch for {name}", errors)
        if evidence := entry.get("expected_error_evidence"):
            log_text = (root / name / "server.log").read_text(encoding="utf-8", errors="replace")
            require(evidence in log_text, f"server error evidence missing for {name}: {evidence}", errors)

        request = json.loads((root / name / "request.json").read_text(encoding="utf-8"))
        request_prompt_hash = hashlib.sha256(request.get("prompt", "").encode("utf-8")).hexdigest()
        require(request_prompt_hash == prompt_hash, f"request prompt content hash mismatch for {name}", errors)
        normalized_request = dict(request)
        normalized_request["model"] = "$H3_MODEL_ALIAS"
        canonical_request_hash = hashlib.sha256(json.dumps(normalized_request, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        require(canonical_request_hash == CANONICAL_REQUEST_SHA256, f"canonical request mismatch for {name}", errors)
        if item.get("canonical_request_sha256") is not None:
            require(item["canonical_request_sha256"] == CANONICAL_REQUEST_SHA256, f"metadata canonical request digest mismatch for {name}", errors)
        require(request.get("task") == "t2va" and request.get("seed") == 0, f"fixed task/seed mismatch for {name}", errors)
        target = request.get("target", {})
        require(target == {"short_edge": 768, "aspect_ratio": "16:9", "duration_seconds": 5.0}, f"fixed target mismatch for {name}", errors)
        resource_trace = (root / name / "resources.csv").read_text(encoding="utf-8", errors="replace")
        require("monitor_error" not in resource_trace, f"resource monitor error recorded for {name}", errors)
        require(item.get("resource_monitor_failed") is not True, f"resource monitor marked failed for {name}", errors)

        started = datetime.fromisoformat(item["started_at"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(item["finished_at"].replace("Z", "+00:00"))
        wall_seconds = (finished - started).total_seconds()
        if "service load timeout" in item.get("error", ""):
            require(wall_seconds <= 3610, f"load-timeout shutdown grace too large for {name}: {wall_seconds}s", errors)
        if item.get("load_elapsed_seconds") is not None:
            require(item["load_elapsed_seconds"] <= 3600, f"load elapsed exceeds limit for {name}", errors)
        status_path = root / name / "status.ndjson"
        if status_path.is_file():
            status_lines = status_path.read_text(encoding="utf-8").splitlines()
            first = datetime.fromisoformat(json.loads(status_lines[0])["utc"].replace("Z", "+00:00"))
            last = datetime.fromisoformat(json.loads(status_lines[-1])["utc"].replace("Z", "+00:00"))
            require((last - first).total_seconds() <= 3600, f"generation polling exceeds limit for {name}", errors)

    slots = [entry for entry in entries.values() if entry["kind"] == "profile_slot"]
    exceptions = [entry for entry in entries.values() if entry["kind"] == "owner_exception_profile_slot"]
    followups = [entry for entry in entries.values() if entry["kind"] == "owner_authorized_performance_followup"]
    corrections = [entry for entry in entries.values() if entry["kind"] == "owner_authorized_performance_correction"]
    performance_executions = followups + corrections
    require(len(slots) == 6, f"expected 6 original profile slots, found {len(slots)}", errors)
    for profile in ("A", "B", "C"):
        profile_slots = sorted(entry["slot"] for entry in slots if entry["profile"] == profile)
        require(profile_slots == [1, 2], f"profile {profile} slots mismatch: {profile_slots}", errors)
    require(
        len(exceptions) == 1
        and exceptions[0]["id"] == "C3-owner-exception"
        and exceptions[0]["profile"] == "C"
        and exceptions[0]["slot"] == 3,
        "executed Owner exception does not match authorized C3",
        errors,
    )
    require({entry["lock"] for entry in entries.values()} == {1, 2}, "runtime lock set mismatch", errors)
    submissions = sum(bool(item.get("generation_submitted")) for item in metadata.values())
    require(submissions <= manifest["generation_submission_limit"], f"generation submission limit exceeded: {submissions}", errors)
    for profile in ("A", "B", "C"):
        original_count = sum(metadata[entry["id"]].get("generation_submitted", False) for entry in slots if entry["profile"] == profile)
        require(original_count <= manifest["profile_slot_limit"], f"original profile {profile} generation limit exceeded: {original_count}", errors)
    require(sum(metadata[entry["id"]].get("generation_submitted", False) for entry in exceptions) == 1, "authorized C3 submission count mismatch", errors)
    require(len(followups) == 1, "initial 4-GPU follow-up execution missing", errors)
    require(len(corrections) <= 1, "more than one 4-GPU correction execution found", errors)

    require(metadata["B1"].get("memory_safety_exceeded") is True, "B1 safety-line breach evidence missing", errors)
    require(metadata["B1"].get("peak_host_used_bytes", 0) > 235 * GIB, "B1 peak does not show the disclosed breach", errors)
    require(metadata["B2"].get("host_memory_abort_bytes", 10**30) < 235 * GIB, "B2 abort threshold is not below hard line", errors)
    require(metadata["B2"].get("memory_safety_exceeded") is False, "B2 crossed hard safety line", errors)
    for name, item in metadata.items():
        expected_breach = entries[name].get("expected_safety_line_breach", False)
        if expected_breach:
            require(item.get("memory_safety_exceeded") is True and item.get("peak_host_used_bytes", 0) >= 235 * GIB, f"expected host safety breach evidence missing for {name}", errors)
        else:
            require(item.get("peak_host_used_bytes", 10**30) < 235 * GIB, f"unexpected host safety breach for {name}", errors)
    require(metadata["C1"].get("peak_gpu_memory_mib", {}).get("0", 0) >= 23000, "C1 GPU OOM peak evidence missing", errors)
    require(metadata["C2"].get("peak_gpu_memory_mib", {}).get("0", 0) >= 22000, "C2 GPU peak evidence missing", errors)

    b2_output = metadata["B2"].get("server_output_path", "")
    require(b2_output.startswith("var/outputs/r1-feasibility/B2/"), "B2 compliant server output path missing", errors)
    c3 = metadata["C3-owner-exception"]
    require(c3.get("server_output_path", "").startswith("var/outputs/r1-feasibility/C3-owner-exception/"), "C3 compliant server output path missing", errors)
    require(c3.get("authorization_state_at_launch") == "authorized_pending", "C3 launch authorization evidence missing", errors)
    require(c3.get("server_tool_preflight", {}).keys() == {"ffmpeg", "ffprobe"}, "C3 exact media-tool preflight missing", errors)
    require(c3.get("video_stream_count") == 1 and c3.get("audio_stream_count") == 1, "C3 stream gates failed", errors)
    require(c3.get("ffprobe_exit") == 0 and c3.get("decode_exit") == 0, "C3 ffprobe/decode gate failed", errors)
    require(c3.get("content_http_status") == 200 and c3.get("output_bytes", 0) > 0, "C3 content gate failed", errors)
    require(c3.get("resource_monitor_failed") is False and c3.get("memory_safety_exceeded") is False, "C3 monitor/safety gate failed", errors)
    c3_media = root / "C3-owner-exception/probe.mp4"
    require(c3_media.is_file(), "C3 retained probe MP4 missing", errors)
    if c3_media.is_file():
        require(hashlib.sha256(c3_media.read_bytes()).hexdigest() == c3.get("output_sha256"), "C3 retained media checksum mismatch", errors)
    independent_probe = root / "C3-owner-exception/ffprobe-independent.json"
    require(independent_probe.is_file(), "C3 independent ffprobe artifact missing", errors)
    if independent_probe.is_file():
        independent_data = json.loads(independent_probe.read_text(encoding="utf-8"))
        stream_types = [stream.get("codec_type") for stream in independent_data.get("streams", [])]
        require(stream_types.count("video") == 1 and stream_types.count("audio") == 1, "C3 independent stream count mismatch", errors)
    media_verification_path = root / "C3-owner-exception/independent-media-verification.json"
    require(media_verification_path.is_file(), "C3 reproducible media verification artifact missing", errors)
    if media_verification_path.is_file():
        media_verification = json.loads(media_verification_path.read_text(encoding="utf-8"))
        require(media_verification.get("input", {}).get("sha256") == c3.get("output_sha256"), "C3 media verification input checksum mismatch", errors)
        require(media_verification.get("stream_counts") == {"video": 1, "audio": 1}, "C3 media verification stream counts mismatch", errors)
        require(all(check.get("exit_code") == 0 for check in media_verification.get("checks", {}).values()), "C3 independent media command failed", errors)
    cleanup_path = root / "C3-owner-exception/post-stop-gpu-snapshot.json"
    require(cleanup_path.is_file(), "C3 post-stop GPU snapshot missing", errors)
    if cleanup_path.is_file():
        cleanup = json.loads(cleanup_path.read_text(encoding="utf-8"))
        require(cleanup.get("checks", {}).get("compute_apps", {}).get("stdout_lines") == [], "C3 residual compute process found", errors)
        gpu_lines = cleanup.get("checks", {}).get("gpus", {}).get("stdout_lines", [])
        require(len(gpu_lines) == 5 and all(int(line.split(",")[1].strip()) <= 10 for line in gpu_lines), "C3 post-stop GPU memory did not return to idle", errors)
        cleanup_time = datetime.fromisoformat(cleanup["captured_at"].replace("Z", "+00:00"))
        c3_finished = datetime.fromisoformat(c3["finished_at"].replace("Z", "+00:00"))
        require(cleanup_time >= c3_finished, "C3 cleanup snapshot predates attempt completion", errors)
    for g4_entry in performance_executions:
        g4 = metadata[g4_entry["id"]]
        g4_contract = g4_entry["launch_contract"]
        require(g4.get("environment") == g4_contract["environment"], f"{g4_entry['id']} runtime environment differs from launch contract", errors)
        require(g4.get("launch_provenance") == g4_contract["provenance"], f"{g4_entry['id']} runtime provenance differs from launch contract", errors)
        require(g4.get("server_output_path", "").startswith(f"var/outputs/r1-feasibility/{g4_entry['id']}/"), f"{g4_entry['id']} compliant output path missing", errors)
        if g4.get("status") == "succeeded":
            require(g4.get("terminal_status") in {"completed", "succeeded"}, f"{g4_entry['id']} terminal success status missing", errors)
            require(g4.get("video_stream_count") == 1 and g4.get("audio_stream_count") == 1, f"{g4_entry['id']} stream gates failed", errors)
            g4_probe_summary = g4.get("ffprobe_summary", {})
            g4_video = g4_probe_summary.get("video") or {}
            g4_audio = g4_probe_summary.get("audio") or {}
            require(g4_video.get("width") == 1344 and g4_video.get("height") == 768, f"{g4_entry['id']} output geometry mismatch", errors)
            require(g4_video.get("r_frame_rate") == "24/1" and g4_video.get("nb_frames") == "124", f"{g4_entry['id']} frame rate/count mismatch", errors)
            require(g4_audio.get("channels") == 2 and g4_audio.get("sample_rate") == "32000", f"{g4_entry['id']} audio shape mismatch", errors)
            require(5.0 <= float(g4_probe_summary.get("duration_seconds", 0)) <= 5.3, f"{g4_entry['id']} duration alignment mismatch", errors)
            require(g4.get("ffprobe_exit") == 0 and g4.get("decode_exit") == 0, f"{g4_entry['id']} ffprobe/decode gate failed", errors)
            require(g4.get("content_http_status") == 200 and g4.get("output_bytes", 0) > 0, f"{g4_entry['id']} content gate failed", errors)
            require(g4.get("post_stop_gpu_snapshot", {}).get("compute_apps") == [], f"{g4_entry['id']} residual compute process found", errors)
            g4_media = root / g4_entry["id"] / "probe.mp4"
            require(g4_media.is_file(), f"{g4_entry['id']} retained probe MP4 missing", errors)
            if g4_media.is_file():
                require(hashlib.sha256(g4_media.read_bytes()).hexdigest() == g4.get("output_sha256"), f"{g4_entry['id']} retained media checksum mismatch", errors)

    for name in ("C1", "C2"):
        response = json.loads((root / name / "submit-response.json").read_text(encoding="utf-8"))
        require("/outputs/" in response.get("file_path", "") and "/var/outputs/" not in response.get("file_path", ""), f"legacy output deviation evidence missing for {name}", errors)

    terminal = json.loads((root / "C2/status.ndjson").read_text(encoding="utf-8").splitlines()[-1])["body"]
    require(terminal.get("status") == "failed", "C2 terminal status is not failed", errors)
    require("ffprobe is required" in terminal.get("error", {}).get("message", ""), "C2 terminal ffprobe error missing", errors)
    media_paths = {path.relative_to(root).as_posix() for path in root.glob("**/*.mp4")}
    allowed_media_prefixes = ("C3-owner-exception/", "G4-TP4Q/", "G4-TP4Q-adaln/")
    require(media_paths and all(path.startswith(allowed_media_prefixes) for path in media_paths), f"unexpected retained MP4 path: {sorted(media_paths)}", errors)

    project_bytes = int(run("du", "-sx", "--block-size=1", ".").stdout.split()[0])
    baseline_bytes = 942080
    delta = project_bytes - baseline_bytes
    require(delta < manifest["disk_delta_limit_gib"] * GIB, f"R1 disk delta exceeds budget: {delta}", errors)
    print(f"CHECK runtime_executions count={len(metadata)} profile_slots={len(slots)} generation_submissions={submissions}")
    print(f"CHECK disk_delta bytes={delta} limit={manifest['disk_delta_limit_gib'] * GIB}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-evidence", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    verify_static(errors)
    if args.runtime_evidence:
        verify_runtime(errors)
    if errors:
        print("RESULT FAIL")
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print("RESULT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
