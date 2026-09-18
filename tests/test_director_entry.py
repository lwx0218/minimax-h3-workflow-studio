"""No GPU: project adapter installation and executable JavaScript contracts."""
import asyncio
import importlib.util
import json
from types import SimpleNamespace
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_runtime

ROOT = Path(__file__).resolve().parents[1]


class DirectorEntryTests(unittest.TestCase):
    def test_javascript_behaviour(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("installed Node.js required for adapter behaviour test")
        result = subprocess.run(
            [node, "--experimental-vm-modules", str(ROOT / "tests/director_entry.test.mjs")],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fixed_workflow_route(self):
        routes = {}
        def register(path):
            def decorate(handler):
                routes[path] = handler
                return handler
            return decorate
        web = SimpleNamespace(FileResponse=lambda path, headers: (path, headers))
        server = SimpleNamespace(PromptServer=SimpleNamespace(instance=SimpleNamespace(routes=SimpleNamespace(get=register))))
        spec = importlib.util.spec_from_file_location("h3_entry", ROOT / "comfy_extensions/H3_Director_Entry/__init__.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"aiohttp": SimpleNamespace(web=web), "server": server}):
            spec.loader.exec_module(module)
        path, headers = asyncio.run(routes["/h3-director/workflow"]({"path": "../../secret"}))
        self.assertEqual(path, ROOT / "workflows/comfy-ui/director-single-t2v.json")
        self.assertEqual(json.loads(path.read_text())["nodes"][0]["type"], "UNETLoader")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(module.NODE_CLASS_MAPPINGS, {})

    def test_code_only_no_models_packages_and_safe_idempotent_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            shutil.copytree(ROOT / "config", repo / "config")
            shutil.copytree(ROOT / "comfy_extensions", repo / "comfy_extensions", symlinks=True)
            shutil.copytree(ROOT / "workflows/comfy-ui", repo / "workflows/comfy-ui")
            comfy = repo / "var/runtime/ComfyUI"
            target = comfy / "custom_nodes/H3_Director_Entry"
            with patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", ["prepare", "--repo", str(repo), "--code-only"]), patch.object(prepare_runtime, "project_python"), patch.object(prepare_runtime, "run") as run, patch.object(prepare_runtime, "normalize_qwen") as convert, patch.object(prepare_runtime, "git_checkout") as checkout:
                for _ in range(2):
                    self.assertEqual(prepare_runtime.main(), 0)
                self.assertEqual(target.resolve(), repo / "comfy_extensions/H3_Director_Entry")
                self.assertTrue((target / "web/director-entry.js").is_file())
                self.assertEqual(checkout.call_args.args[2], "eb9d274f707012346f23d20a3372fbd4cbc7a9f8")
                run.assert_not_called(); convert.assert_not_called()
                self.assertFalse((repo / "var/manifests").exists())
                target.unlink(); target.mkdir()
                checkout.reset_mock()
                with self.assertRaises(FileExistsError):
                    prepare_runtime.main()
                checkout.assert_not_called()
