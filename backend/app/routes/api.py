import uuid
from fastapi import APIRouter, HTTPException

from app.models import ProcessRequest, JobResponse, StatusResponse, ResultResponse
from app.services.transcript import get_transcript, merge_chunks

router = APIRouter()

# In-memory job store (swap for Redis/DB later if needed)
jobs: dict[str, dict] = {}


@router.post("/process", response_model=JobResponse)
async def process_video(request: ProcessRequest):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "progress": "Extracting transcript",
        "youtube_url": request.youtube_url,
        "result": None,
    }
    # TODO: kick off LangGraph pipeline in background
    return JobResponse(job_id=job_id)


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return StatusResponse(status=job["status"], progress=job["progress"])


@router.get("/result/{job_id}", response_model=ResultResponse)
async def get_result(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Job not complete yet")
    return job["result"]


@router.post("/test-transcript")
async def test_transcript(request: ProcessRequest):
    """Test endpoint — fetch and chunk a YouTube transcript."""
    try:
        raw_chunks = get_transcript(request.youtube_url)
        merged = merge_chunks(raw_chunks)
        return {
            "raw_chunk_count": len(raw_chunks),
            "merged_chunk_count": len(merged),
            "sample_raw": raw_chunks[:3],
            "sample_merged": merged[:2],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate-third/{job_id}")
async def generate_third(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # TODO: trigger video generation for 3rd concept
    return {"video_url": None, "message": "Not implemented yet"}
