from pydantic import BaseModel


class ChatRequest(BaseModel):
    youtube_url: str
    question: str


class SourceChunk(BaseModel):
    text: str
    start_time: float
    end_time: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
