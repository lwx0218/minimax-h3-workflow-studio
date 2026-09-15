#!/usr/bin/env python3
"""Prepare local VAE containers for native ComfyUI; no downloads or engine edits.

Audio legacy weight_norm is materialized with PyTorch's identical operation.
Normalization buffers come only from the existing release sidecar config.
"""
import argparse
import json
import os
from pathlib import Path


def convert(source: Path, config: Path, destination: Path) -> None:
    import torch
    from safetensors.torch import load_file, save_file
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    sd = load_file(source, device='cpu')
    cfg = json.loads(config.read_text())
    for suffix in ('mean', 'std'):
        key = 'latents_' + suffix
        value = torch.tensor(cfg[key], dtype=torch.float32)
        if value.shape != (cfg['latent_channels'],) or not torch.isfinite(value).all():
            raise ValueError(f'Invalid sidecar {key}')
        if suffix == 'std' and not (value > 0).all():
            raise ValueError('Invalid normalization std')
        if key in sd:
            raise ValueError(f'Unexpected existing {key}')
        sd[key] = value
    for key in list(sd):
        if key.endswith('.weight_g'):
            prefix = key[:-len('weight_g')]
            g = sd.pop(key)
            v = sd.pop(prefix + 'weight_v')
            if v.dtype != torch.float32 or g.dtype != torch.float32:
                raise ValueError('Only original FP32 weight_norm is supported')
            if prefix + 'weight' in sd:
                raise ValueError('Duplicate weight')
            sd[prefix + 'weight'] = torch._weight_norm(v, g, 0).contiguous()
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + '.partial')
    # Reserve without clobbering an interrupted conversion.
    with partial.open('xb'):
        pass
    save_file(sd, partial)
    os.link(partial, destination)
    partial.unlink()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('config', type=Path)
    p.add_argument('destination', type=Path)
    a = p.parse_args()
    convert(a.source, a.config, a.destination)
