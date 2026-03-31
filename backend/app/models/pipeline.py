from pydantic import BaseModel


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
