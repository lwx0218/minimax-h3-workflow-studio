"""Opt-in frontend adapter; uses only ComfyUI's existing HTTP stack."""
from pathlib import Path

from aiohttp import web
from server import PromptServer

NODE_CLASS_MAPPINGS = {}
WEB_DIRECTORY = "./web"
WORKFLOW = Path(__file__).resolve().parents[2] / "workflows/comfy-ui/director-single-t2v.json"


@PromptServer.instance.routes.get("/h3-director/workflow")
async def director_workflow(_request):
    # Fixed project asset, never a request-supplied path or URL.
    return web.FileResponse(WORKFLOW, headers={"Cache-Control": "no-store"})
