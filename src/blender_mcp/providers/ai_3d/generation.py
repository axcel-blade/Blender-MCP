"""Text/image-to-3D generation jobs for Meshy and Tripo.

Jobs run on the provider; we poll them, and when one finishes we download the GLB so the
addon can import it. Job state lives in-process (keyed by a short id) so the model can
start a generation, keep working, and collect it later with ``get_generation_status``.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from blender_mcp.exceptions import AssetDownloadFailedError, BlenderMCPError
from blender_mcp.providers.downloads import asset_dir, fetch_file

MESHY_API = "https://api.meshy.ai/openapi"
TRIPO_API = "https://api.tripo3d.ai/v2/openapi"


@dataclass
class Job:
    id: str
    provider: str
    task_id: str
    endpoint: str
    prompt: str | None
    texture: bool
    stage: str = "preview"
    status: str = "running"
    progress: int = 0
    model_url: str | None = None
    path: str | None = None
    error: str | None = None
    imported: dict[str, Any] | None = None
    target_size: float | None = None
    collection: str | None = None
    started: float = field(default_factory=time.time)

    def summary(self) -> dict[str, Any]:
        return {
            "job_id": self.id,
            "provider": self.provider,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "elapsed_seconds": round(time.time() - self.started),
            "error": self.error,
            "imported": self.imported,
        }


JOBS: dict[str, Job] = {}


def _meshy_headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


async def start(
    provider: str,
    api_key: str,
    *,
    prompt: str | None,
    image_url: str | None,
    texture: bool = True,
) -> Job:
    if not prompt and not image_url:
        raise BlenderMCPError("Give a text prompt or an image_url")
    if image_url and not image_url.startswith(("https://", "data:image/")):
        raise BlenderMCPError("image_url must be an https:// URL or a data:image/ URI")
    async with httpx.AsyncClient(timeout=60.0) as client:
        if provider == "meshy":
            if image_url:
                endpoint = f"{MESHY_API}/v1/image-to-3d"
                body: dict[str, Any] = {"image_url": image_url, "should_texture": texture}
            else:
                endpoint = f"{MESHY_API}/v2/text-to-3d"
                body = {"mode": "preview", "prompt": prompt}
            resp = await client.post(endpoint, json=body, headers=_meshy_headers(api_key))
            resp.raise_for_status()
            task_id = resp.json()["result"]
        elif provider == "tripo":
            endpoint = f"{TRIPO_API}/task"
            if image_url:
                body = {"type": "image_to_model", "file": {"type": "png", "url": image_url}}
            else:
                body = {"type": "text_to_model", "prompt": prompt}
            body["texture"] = texture
            resp = await client.post(
                endpoint, json=body, headers={"Authorization": f"Bearer {api_key}"}
            )
            resp.raise_for_status()
            task_id = resp.json()["data"]["task_id"]
        else:
            raise BlenderMCPError(f"Unsupported generator: {provider}")
    job = Job(
        id=uuid.uuid4().hex[:8],
        provider=provider,
        task_id=task_id,
        endpoint=endpoint,
        prompt=prompt,
        texture=texture and not image_url,
    )
    JOBS[job.id] = job
    return job


async def poll(job: Job, api_key: str) -> Job:
    """Advance a job one step: check status, run the Meshy refine stage, download."""
    if job.status in {"succeeded", "failed", "imported"}:
        return job
    async with httpx.AsyncClient(timeout=60.0) as client:
        if job.provider == "meshy":
            resp = await client.get(
                f"{job.endpoint}/{job.task_id}", headers=_meshy_headers(api_key)
            )
            resp.raise_for_status()
            data = resp.json()
            job.progress = int(data.get("progress") or 0)
            status = data.get("status")
            if status in {"FAILED", "CANCELED", "EXPIRED"}:
                job.status = "failed"
                job.error = (data.get("task_error") or {}).get("message") or status
                return job
            if status != "SUCCEEDED":
                return job
            if job.texture and job.stage == "preview" and job.endpoint.endswith("text-to-3d"):
                refine = await client.post(
                    job.endpoint,
                    json={"mode": "refine", "preview_task_id": job.task_id},
                    headers=_meshy_headers(api_key),
                )
                refine.raise_for_status()
                job.task_id = refine.json()["result"]
                job.stage = "refine"
                job.progress = 0
                return job
            job.model_url = (data.get("model_urls") or {}).get("glb")
        else:
            resp = await client.get(
                f"{TRIPO_API}/task/{job.task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            job.progress = int(data.get("progress") or 0)
            status = data.get("status")
            if status in {"failed", "cancelled", "banned", "expired", "unknown"}:
                job.status = "failed"
                job.error = status
                return job
            if status != "success":
                return job
            output = data.get("output") or {}
            job.model_url = output.get("pbr_model") or output.get("model")
        if not job.model_url:
            job.status = "failed"
            job.error = "Provider finished but returned no model URL"
            return job
        out = asset_dir(job.provider, job.id)
        try:
            path = await fetch_file(client, job.model_url, Path(out) / f"{job.id}.glb")
        except AssetDownloadFailedError as exc:
            job.status = "failed"
            job.error = str(exc)
            return job
        job.path = str(path)
        job.status = "succeeded"
    return job


async def wait(job: Job, api_key: str, seconds: float, interval: float = 5.0) -> Job:
    deadline = time.time() + max(0.0, seconds)
    while True:
        await poll(job, api_key)
        if job.status != "running" or time.time() >= deadline:
            return job
        await asyncio.sleep(interval)
