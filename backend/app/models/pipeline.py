from pydantic import BaseModel


class ProcessRequest(BaseModel):
    youtube_url: str


class JobResponse(BaseModel):
    job_id: str


class StatusResponse(BaseModel):
    status: str
    progress: str


class ConceptResult(BaseModel):
    title: str
    description: str = ""
    start_time: float = 0
    end_time: float = 0
    infographic_urls: list[str] = []


class ResultResponse(BaseModel):
    youtube_url: str
    concepts: list[ConceptResult]
    slideshow_url: str | None = None
