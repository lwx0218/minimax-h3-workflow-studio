"""The legacy launcher must not inject fallback packages into its interpreter."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from h3_studio.workers import WorkerSpec
from scripts.start import worker_command, start_director, director_host
from scripts import prepare_runtime
import json
import shutil
import signal
import time


class LauncherTests(unittest.TestCase):
    def setUp(self):
        # Host tests must not inherit the operator's actual LAN configuration.
        env = patch.dict(os.environ, {'H3_DIRECTOR_HOST': '127.0.0.1'})
        env.start()
        self.addCleanup(env.stop)

    def test_director_host_default_explicit_and_invalid(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(director_host(), '127.0.0.1')
        with patch.dict(os.environ, {'H3_DIRECTOR_HOST': '127.0.0.2'}):
            self.assertEqual(director_host(), '127.0.0.2')
        for value in ('http://127.0.0.1', '127.0.0.1:30210', 'bad-host', '',
                      '0.0.0.0', '::1', '224.0.0.1', '255.255.255.255', '8.8.8.8'):
            with self.subTest(value=value), patch.dict(os.environ, {'H3_DIRECTOR_HOST': value}):
                with self.assertRaises(SystemExit):
                    director_host()

    def test_prepare_then_default_start_stop(self):
        """Real isolated interpreter and HTTP child; no GPU or external downloads."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = Path(__file__).resolve().parents[1]
            shutil.copytree(source / "config", repo / "config")
            shutil.copytree(source / "comfy_extensions", repo / "comfy_extensions", symlinks=True)
            shutil.copytree(source / "workflows/comfy-ui", repo / "workflows/comfy-ui")
            (repo / "config/requirements-lock.txt").write_text("")
            subprocess.run([sys.executable, "-m", "venv", str(repo / ".venv")], check=True, timeout=60)
            comfy = repo / "var/runtime/ComfyUI"
            comfy.mkdir(parents=True)
            (comfy / "main.py").write_text(
                "import os,sys,json,argparse\n"
                "from http.server import HTTPServer,BaseHTTPRequestHandler\n"
                "from pathlib import Path\n"
                "p=argparse.ArgumentParser();p.add_argument('--port',type=int);p.add_argument('--listen');a,_=p.parse_known_args()\n"
                "assert os.environ['CUDA_VISIBLE_DEVICES']=='0'\n"
                "assert sys.flags.ignore_environment and sys.flags.no_user_site\n"
                "Path('child.json').write_text(json.dumps({'python':sys.executable,'args':sys.argv}))\n"
                "class H(BaseHTTPRequestHandler):\n"
                " def do_GET(self):\n"
                "  self.send_response(200);self.end_headers();self.wfile.write(json.dumps(dict.fromkeys(['MiniMaxH3Director','UNETLoader','CLIPLoader','VAELoader','CreateVideo','SaveVideo'],{})).encode())\n"
                "HTTPServer((a.listen,a.port),H).serve_forever()\n"
            )
            for name in ('fl2va', 'qwen', 'MiniMax-H3-video_vae-native.safetensors', 'MiniMax-H3-audio_vae-native.safetensors'):
                (repo / name).write_bytes(b'model-test-fixture')
            import socket
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            env = dict(os.environ, H3_MODEL_ROOT=str(repo), H3_NATIVE_FL2VA=str(repo/'fl2va'),
                       H3_NATIVE_QWEN=str(repo/'qwen'), H3_RUNTIME_ROOT=str(repo/'var/runtime'),
                       H3_DIRECTOR_PORT=str(port), H3_GPU='0', H3_DIRECTOR_HOST='127.0.0.2',
                       http_proxy='http://127.0.0.1:1', HTTP_PROXY='http://127.0.0.1:1',
                       no_proxy='', NO_PROXY='')
            env.pop('H3_WORKER_POOL_CONFIG', None)
            with patch.dict(os.environ, env, clear=True), patch.object(sys, 'argv', ['prepare', '--repo', str(repo)]), patch.object(prepare_runtime, 'git_checkout'):
                self.assertEqual(prepare_runtime.main(), 0)
            manifest = json.loads((repo/'var/manifests/director-runtime.json').read_text())
            import select
            for attempt in range(2):  # Same port restart after complete shutdown.
                proc = subprocess.Popen([sys.executable, str(source/'scripts/start.py'), '--repo', str(repo), '--wait-ready', '15'], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                try:
                    self.assertTrue(select.select([proc.stdout], [], [], 20)[0])
                    ready = proc.stdout.readline()
                    self.assertIn(f'Director ready: http://127.0.0.2:{port}/', ready)
                    child_pid = int((repo/'var/logs/comfyui-director.pid').read_text())
                    child = json.loads((comfy/'child.json').read_text())
                    self.assertEqual(child['python'], manifest['python'])
                    self.assertEqual(child['args'][child['args'].index('--listen')+1], '127.0.0.2')
                    self.assertIn('--disable-all-custom-nodes', child['args'])
                    self.assertIn('ComfyUI_MiniMaxH3_Director', child['args'])
                    self.assertIn('H3_Director_Entry', child['args'])
                finally:
                    proc.send_signal(signal.SIGTERM)
                    output, _ = proc.communicate(timeout=30)
                self.assertEqual(proc.returncode, 130, output)
                with self.assertRaises(ProcessLookupError):
                    os.kill(child_pid, 0)
                with socket.socket() as sock:
                    self.assertNotEqual(sock.connect_ex(('127.0.0.2', port)), 0)
                self.assertFalse((repo/'var/logs/comfyui-director.pid').exists())
                self.assertFalse((repo/'var/logs/h3-studio.pid').exists())

    def test_readiness_failure_branches(self):
        import socket
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'main.py').touch()
            with socket.socket() as listener:
                listener.bind(('127.0.0.2', 0)); listener.listen()
                port = listener.getsockname()[1]
                with patch.dict(os.environ, {'H3_DIRECTOR_HOST': '127.0.0.2', 'H3_DIRECTOR_PORT': str(port), 'H3_GPU': '0'}), patch('scripts.prepare_runtime.project_python', return_value=Path(sys.executable)), patch('scripts.start.subprocess.Popen') as launch:
                    with self.assertRaises(OSError):
                        start_director(repo, repo, 1, [])
                    launch.assert_not_called()
            for timeout, poll, error in [(0, None, TimeoutError), (1, 7, RuntimeError)]:
                proc = MagicMock();proc.pid=123;proc.poll.return_value=poll
                with patch.dict(os.environ, {'H3_DIRECTOR_PORT': str(port), 'H3_GPU':'0'}), patch('scripts.prepare_runtime.project_python', return_value=Path(sys.executable)), patch('scripts.start.subprocess.Popen', return_value=proc), patch('scripts.start.signal.signal'), patch('scripts.start.terminate') as cleanup:
                    with self.assertRaises(error):
                        start_director(repo, repo, timeout, [])
                    cleanup.assert_called_once_with(proc)
                    self.assertFalse((repo/'var/logs/comfyui-director.pid').exists())

    def test_fake_node_discovery_and_missing_director(self):
        import urllib.request
        from tests.fake_comfy import FakeComfyServer
        server = FakeComfyServer().start()
        try:
            url = f'http://127.0.0.1:{server.port}/object_info'
            with urllib.request.urlopen(url) as response:
                self.assertIn('MiniMaxH3Director', json.load(response))
            del server.state.object_info['MiniMaxH3Director']
            with urllib.request.urlopen(url) as response:
                self.assertNotIn('MiniMaxH3Director', json.load(response))
        finally:
            server.stop()
        import io
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp); (repo/'main.py').touch()
            proc = MagicMock(); proc.pid=123; proc.poll.return_value=None
            response = MagicMock(); response.__enter__.return_value=io.StringIO('{}')
            with patch.dict(os.environ, {'H3_DIRECTOR_PORT':'0','H3_GPU':'0'}), patch('scripts.prepare_runtime.project_python', return_value=Path(sys.executable)), patch('scripts.start.subprocess.Popen', return_value=proc), patch('scripts.start.signal.signal'), patch('scripts.start.terminate') as cleanup, patch('urllib.request.OpenerDirector.open', return_value=response):
                with self.assertRaisesRegex(RuntimeError, 'Required Director nodes missing'):
                    start_director(repo,repo,1,[])
                cleanup.assert_called_once_with(proc)

    def test_observed_lock_cannot_install_packages(self):
        source = Path(__file__).resolve().parents[1]
        with patch.object(sys, 'argv', ['prepare', '--install-deps']), patch('scripts.prepare_runtime.project_python', return_value=source/'.venv/bin/python'), patch('scripts.prepare_runtime.run') as run:
            with self.assertRaisesRegex(SystemExit, 'Installation disabled'):
                prepare_runtime.main()
            run.assert_not_called()

    def test_qkv_row_permutation(self):
        from scripts.convert_fl2va import reorder_rows
        self.assertEqual(reorder_rows(bytes(range(12)), 2, 2), bytes([0,1,6,7,2,3,8,9,4,5,10,11]))
        with self.assertRaises(ValueError):
            reorder_rows(b'bad', 2, 2)

    def test_qwen_conversion_preserves_payload_and_quantization(self):
        import struct
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); src=root/'source'; dst=root/'native'
            header={f'model.language_model.layers.{i}.comfy_quant': {'dtype':'U8','shape':[1],'data_offsets':[i,i+1]} for i in range(350)}
            raw=json.dumps(header).encode();payload=bytes(i%256 for i in range(350))
            src.write_bytes(struct.pack('<Q',len(raw))+raw+payload)
            prepare_runtime.normalize_qwen(src,dst)
            with dst.open('rb') as f:
                new=json.loads(f.read(struct.unpack('<Q',f.read(8))[0]))
                self.assertEqual(f.read(),payload)
            self.assertEqual(len(new),350)
            self.assertEqual(new['model.layers.0.comfy_quant'],header['model.language_model.layers.0.comfy_quant'])
            with self.assertRaises(FileExistsError):
                prepare_runtime.normalize_qwen(src,dst)

    def test_worker_ignores_python_path_and_user_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            comfy = repo / "ComfyUI"
            comfy.mkdir()
            injected = repo / "injected"
            injected.mkdir()
            (comfy / "main.py").write_text(
                "import os, site, sys\n"
                "assert os.environ['PYTHONPATH'] not in sys.path\n"
                "assert not site.ENABLE_USER_SITE\n"
                "assert sys.flags.ignore_environment\n",
                encoding="utf-8",
            )
            env = dict(os.environ, PYTHONPATH=str(injected))
            worker = WorkerSpec("test", "0", "127.0.0.1", 30211)
            with patch("scripts.start.project_local_env", return_value=env):
                cmd, child_env, _ = worker_command(
                    Path(sys.executable), comfy, worker, repo, []
                )
            result = subprocess.run(cmd, env=child_env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(child_env["CUDA_VISIBLE_DEVICES"], "0")
