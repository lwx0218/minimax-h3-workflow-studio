# var/

Everything under `var/` is ignored by Git. Layout:

```
var/
├── runtime/        # ComfyUI checkout + venv (scripts/prepare_runtime.py)
├── h3-studio/      # runs/<run_id>/run.json, uploads/
├── outputs/<worker-id>/   # ComfyUI output namespace per worker
├── tmp/<worker-id>/       # ComfyUI temp namespace per worker
├── logs/           # comfyui-<worker-id>.log, h3-studio.log, *.pid
├── cache/          # HF_HOME, TORCH_HOME, tools (ffmpeg/ffprobe)
└── manifests/      # prepare/start evidence json
```

Older checkouts used `var/runtimes/r3-single-worker-product/`; move it with
`mv var/runtimes/r3-single-worker-product var/runtime` or set `H3_RUNTIME_ROOT`.
