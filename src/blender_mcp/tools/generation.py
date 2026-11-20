"""AI text/image-to-3D generation tools (Meshy, Tripo)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.exceptions import BlenderMCPError
from blender_mcp.security.permissions import require_tool_group
from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.utils.results import fail_from_exception, ok

SUPPORTED = ("meshy", "tripo")


def register(mcp: FastMCP, ctx: AppContext) -> None:
    from blender_mcp.providers.ai_3d import generation as gen

    def _key(provider: str) -> str:
        p = ctx.settings.providers()
        enabled = getattr(p, provider, False)
        key = getattr(p, f"{provider}_api_key", "")
        if not (enabled and key):
            raise BlenderMCPError(
                f"{provider} is not set up. Enable it and set BLENDER_MCP_{provider.upper()}"
                "_API_KEY (or the matching config.toml entry)."
            )
        return key

    def _pick(provider: str | None) -> str:
        if provider:
            name = provider.lower()
            if name not in SUPPORTED:
                raise BlenderMCPError(f"Unsupported generator {provider!r}; use one of {SUPPORTED}")
            return name
        p = ctx.settings.providers()
        for name in SUPPORTED:
            if getattr(p, name) and getattr(p, f"{name}_api_key"):
                return name
        raise BlenderMCPError("No 3D generator configured (Meshy or Tripo API key needed)")

    async def _finish(job: Any, target_size: float | None, collection: str | None):
        if job.status == "succeeded" and job.imported is None:
            result = await call_blender(
                ctx,
                "import_local_asset",
                {
                    "kind": "model",
                    "path": job.path,
                    "source": job.provider,
                    "asset_id": job.id,
                    "target_size": target_size,
                    "ground": True,
                    "collection": collection,
                },
                group="assets",
            )
            if result.get("success") is False:
                return result
            job.imported = result.get("result", result)
            job.status = "imported"
        summary = job.summary()
        if job.status == "running":
            summary["next_step"] = (
                f"Still generating. Call get_generation_status(job_id='{job.id}') later; "
                "keep working on the rest of the scene meanwhile."
            )
        return ok(summary)

    @mcp.tool(name="generate_3d")
    async def generate_3d(
        prompt: str | None = None,
        image_url: str | None = None,
        provider: str | None = None,
        texture: bool = True,
        target_size: float | None = None,
        collection: str | None = None,
        wait_seconds: float = 90,
    ) -> dict[str, Any]:
        """Generate ONE new textured 3D model from a text prompt or an image, then import it.

        Takes 1-3 minutes and may use a paid provider credit. Generate single objects, never
        whole scenes or the ground. ``target_size`` (meters) sets the longest side; the model
        is placed on the ground. If it isn't done within ``wait_seconds`` you get a job_id to
        pass to get_generation_status.
        """
        try:
            require_tool_group(ctx.settings, "assets")
            name = _pick(provider)
            key = _key(name)
            job = await gen.start(name, key, prompt=prompt, image_url=image_url, texture=texture)
            job.target_size = target_size
            job.collection = collection
            await gen.wait(job, key, wait_seconds)
            return await _finish(job, target_size, collection)
        except Exception as exc:  # noqa: BLE001
            return fail_from_exception(exc)

    @mcp.tool(name="get_generation_status")
    async def get_generation_status(job_id: str, wait_seconds: float = 30) -> dict[str, Any]:
        """Check a generate_3d job; imports the model into Blender once it is ready."""
        try:
            job = gen.JOBS.get(job_id)
            if job is None:
                raise BlenderMCPError(f"Unknown generation job: {job_id}")
            await gen.wait(job, _key(job.provider), wait_seconds)
            return await _finish(job, job.target_size, job.collection)
        except Exception as exc:  # noqa: BLE001
            return fail_from_exception(exc)

    @mcp.tool(name="list_generation_jobs")
    async def list_generation_jobs() -> dict[str, Any]:
        """List 3D generation jobs started in this session."""
        return ok([job.summary() for job in gen.JOBS.values()])
