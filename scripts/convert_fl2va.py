#!/usr/bin/env python3
"""Lossless local RH grouped-QKV -> native contiguous-QKV container copy.

No engine patch, dequantization or precision change. Keeps all metadata/tensors;
only QKV rows and their per-row scales are permuted together. Never overwrites.
"""
import argparse
import json
from pathlib import Path
import struct
import os


def reorder_rows(data: bytes, heads: int = 56, head_dim: int = 128) -> bytes:
    rows = heads * 3 * head_dim
    if len(data) % rows:
        raise ValueError("QKV byte length is not divisible by row count")
    block = len(data) // rows * head_dim
    return b"".join(data[(h * 3 + q) * block:(h * 3 + q + 1) * block]
                    for q in range(3) for h in range(heads))


def convert(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        raise FileExistsError(dst)
    with src.open("rb") as source:
        size_bytes = source.read(8)
        size = struct.unpack("<Q", size_bytes)[0]
        if size > 100_000_000:
            raise ValueError("Invalid header size")
        raw = source.read(size)
        header = json.loads(raw)
        tensors = sorted((v['data_offsets'][0], v['data_offsets'][1], k, v)
                         for k, v in header.items() if k != '__metadata__')
        end = 0
        dtype_bytes = {'F32': 4, 'F16': 2, 'BF16': 2, 'I8': 1, 'U8': 1}
        for a, b, k, v in tensors:
            elements = 1
            for dimension in v['shape']:
                if not isinstance(dimension, int) or dimension < 0:
                    raise ValueError(f"Invalid shape: {k}")
                elements *= dimension
            if a != end or b - a != elements * dtype_bytes[v['dtype']]:
                raise ValueError(f"Invalid tensor coverage/length: {k}")
            end = b
        if len(tensors) != 1039 or sum(k.endswith('.comfy_quant') for a,b,k,v in tensors) != 252:
            raise ValueError('Unexpected local FL2VA tensor/quant collection')
        if size + 8 + end != src.stat().st_size:
            raise ValueError("Uncovered container bytes; refusing conversion")
        targets = [k for a,b,k,v in tensors if k.endswith(('attn.qkv_proj.weight', 'attn.qkv_proj.weight_scale'))]
        if len(targets) != 102:
            raise ValueError(f"Unexpected local FL2VA QKV tensor count: {len(targets)}")
        for a,b,k,v in tensors:
            if k in targets and v['shape'][0] != 21504:
                raise ValueError(f"Unexpected QKV rows: {k}")
            if k.endswith('attn.qkv_proj.weight') and v['dtype'] == 'I8':
                scale = header[k[:-6] + 'weight_scale']
                if scale['shape'] != [21504, 1] or scale['dtype'] != 'F32':
                    raise ValueError(f"Unsupported scale: {k}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        partial = dst.with_suffix(dst.suffix + '.partial')
        with partial.open('xb') as target:
            target.write(size_bytes + raw)
            for a,b,k,v in tensors:
                if k in targets:
                    data = source.read(b-a)
                    if len(data) != b-a:
                        raise EOFError(k)
                    target.write(reorder_rows(data))
                else:
                    left = b-a
                    while left:
                        data = source.read(min(left, 16*1024*1024))
                        if not data:
                            raise EOFError(k)
                        target.write(data)
                        left -= len(data)
        os.link(partial, dst)
        partial.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    convert(args.source, args.destination)
