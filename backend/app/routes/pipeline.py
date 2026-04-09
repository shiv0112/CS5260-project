import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.logger import get_logger
from app.models import (
    ProcessRequest,
    JobResponse,
    StatusResponse,
    ResultResponse,
    ConceptResult,
)
from app.agents.graph import build_graph

log = get_logger("api.pipeline")
router = APIRouter(tags=["pipeline"])

jobs: dict[str, dict] = {}

pipeline = build_graph()


async def _run_pipeline(job_id: str, youtube_url: str):
    """Background coroutine that runs the full LangGraph pipeline."""
    try:
        jobs[job_id]["progress"] = "Ingesting transcript"
        log.info("[pipeline:%s] Starting pipeline for %s", job_id[:8], youtube_url)

        initial_state = {
            "youtube_url": youtube_url,
            "video_id": "",
            "transcript_chunks": [],
            "top_concepts": [],
            "scripts": [],
            "citations": [],
            "video_urls": [],
            "slideshow_path": "",
            "status": "processing",
            "error_message": "",
        }

        # Update progress as pipeline runs
        jobs[job_id]["progress"] = "Ingesting transcript into vector DB"
        result = await pipeline.ainvoke(initial_state)

        if result.get("status") == "error":
            jobs[job_id]["status"] = "error"
            jobs[job_id]["progress"] = result.get("error_message", "Unknown error")
            log.error("[pipeline:%s] Pipeline error: %s", job_id[:8], result.get("error_message"))
            return

        # Map video_urls to concepts by matching concept_title
        video_url_map = {}
        for v in result.get("video_urls", []):
            video_url_map[v.get("concept_title", "")] = v.get("infographic_urls", [])

        concepts = []
        for concept in result.get("top_concepts", []):
            title = concept.get("title", "")
            concepts.append(ConceptResult(
                title=title,
                description=concept.get("description", ""),
                start_time=concept.get("start_time", 0),
                end_time=concept.get("end_time", 0),
                infographic_urls=video_url_map.get(title, []),
            ))

        slideshow_path = result.get("slideshow_path")

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["progress"] = "Done"
        jobs[job_id]["result"] = ResultResponse(
            youtube_url=youtube_url,
            concepts=concepts,
            slideshow_url=f"/api/slideshow/{job_id}" if slideshow_path else None,
        )
        jobs[job_id]["slideshow_path"] = slideshow_path
        log.info("[pipeline:%s] Pipeline complete: %d concepts", job_id[:8], len(concepts))

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["progress"] = f"Error: {str(e)}"
        log.error("[pipeline:%s] Pipeline failed: %s", job_id[:8], e, exc_info=True)


@router.post("/process", response_model=JobResponse)
async def process_video(request: ProcessRequest):
    """Submit a YouTube URL for full processing."""
    job_id = str(uuid.uuid4())
    log.info("Process requested for %s -> job %s", request.youtube_url, job_id[:8])
    jobs[job_id] = {
        "status": "processing",
        "progress": "Starting pipeline",
        "youtube_url": request.youtube_url,
        "result": None,
        "slideshow_path": None,
    }
    asyncio.create_task(_run_pipeline(job_id, request.youtube_url))
    return JobResponse(job_id=job_id)


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """Poll job status."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return StatusResponse(status=job["status"], progress=job["progress"])


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """Get completed job results."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Job not complete yet")
    return job["result"]


@router.get("/slideshow/{job_id}")
async def get_slideshow(job_id: str):
    """Serve the generated slideshow MP4."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    path = job.get("slideshow_path")
    if not path:
        raise HTTPException(status_code=404, detail="No slideshow available")
    return FileResponse(path, media_type="video/mp4", filename="slideshow.mp4")
