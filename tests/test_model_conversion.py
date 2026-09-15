"""CPU-only conversion checks in the project interpreter; no GPU/model assets."""
from pathlib import Path
import subprocess
import unittest


class ModelConversionTests(unittest.TestCase):
    def test_vae_weight_norm_and_sidecar(self):
        repo = Path(__file__).resolve().parents[1]
        py = repo / '.venv/bin/python'
        if not py.exists():
            self.skipTest('project .venv required for safetensors/torch CPU check')
        code = '''
import json,tempfile,torch
from pathlib import Path
from safetensors.torch import save_file,load_file
from scripts.convert_vae import convert
torch.manual_seed(42)
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);v=torch.randn(6,4,3);g=torch.rand(6,1,1)
 save_file({'layer.weight_g':g,'layer.weight_v':v,'other':torch.ones(2)},p/'source')
 original=(p/'source').read_bytes()
 (p/'config').write_text(json.dumps({'latent_channels':2,'latents_mean':[1,2],'latents_std':[3,4]}))
 convert(p/'source',p/'config',p/'native')
 result=load_file(p/'native')
 assert torch.equal(result['layer.weight'],torch._weight_norm(v,g,0))
 assert torch.equal(result['latents_mean'],torch.tensor([1.,2.]))
 assert torch.equal(result['latents_std'],torch.tensor([3.,4.]))
 assert torch.equal(result['other'],torch.ones(2))
 assert (p/'source').read_bytes()==original
 try:convert(p/'source',p/'config',p/'native')
 except FileExistsError:pass
 else:raise AssertionError('overwrote existing output')
print('CPU weight_norm/normalization/source preservation PASS')
'''
        result = subprocess.run([str(py), '-E', '-s', '-c', code], cwd=repo,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
