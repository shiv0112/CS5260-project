from typing import TypedDict
from pydantic import BaseModel


# --- LangGraph State ---

class YTSageState(TypedDict):
    youtube_url: str
    transcript_chunks: list[dict]   # {text, start_time, end_time}
    top_concepts: list[dict]        # {title, segments, timestamps, rank}
    scripts: list[dict]             # {concept_title, script_text, segments_used}
    citations: list[dict]           # {concept_title, claims: [{text, timestamp, url}]}
    video_urls: list[dict]          # {concept_title, video_url}
    status: str                     # processing | complete | error
    error_message: str


# --- API Request/Response Models ---

class ProcessRequest(BaseModel):
    youtube_url: str


class JobResponse(BaseModel):
    job_id: str


class StatusResponse(BaseModel):
    status: str
    progress: str


class ClaimCitation(BaseModel):
    claim: str
    timestamp: int
    url: str


class ConceptResult(BaseModel):
    title: str
    script: str
    citations: list[ClaimCitation]
    video_url: str | None = None


class ResultResponse(BaseModel):
    concepts: list[ConceptResult]
    third_concept: ConceptResult | None = None
