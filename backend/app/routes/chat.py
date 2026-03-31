from fastapi import APIRouter
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.models import ChatRequest, ChatResponse, SourceChunk
from app.services.transcript import extract_video_id, get_transcript, semantic_chunk_transcript
from app.services.vector_store import query_chunks, is_video_ingested, ingest_chunks, get_video_metadata
from app.services.metadata import fetch_video_metadata

log = get_logger("api.chat")
router = APIRouter(tags=["chat"])


def _format_metadata_context(meta: dict) -> str:
    """Format video metadata into a readable context block for the LLM."""
    parts = []
    if meta.get("title"):
        parts.append(f"Title: {meta['title']}")
    if meta.get("channel"):
        parts.append(f"Channel/Creator: {meta['channel']}")
    if meta.get("upload_date"):
        parts.append(f"Upload Date: {meta['upload_date']}")
    if meta.get("duration"):
        mins, secs = divmod(int(meta["duration"]), 60)
        parts.append(f"Duration: {mins}m {secs}s")
    if meta.get("language"):
        parts.append(f"Language: {meta['language']}")
    if meta.get("description"):
        parts.append(f"Description: {meta['description']}")
    if meta.get("tags"):
        tags = meta["tags"] if isinstance(meta["tags"], list) else [meta["tags"]]
        parts.append(f"Tags: {', '.join(tags)}")
    if meta.get("categories"):
        cats = meta["categories"] if isinstance(meta["categories"], list) else [meta["categories"]]
        parts.append(f"Categories: {', '.join(cats)}")
    if meta.get("view_count"):
        parts.append(f"Views: {meta['view_count']:,}")
    if meta.get("like_count"):
        parts.append(f"Likes: {meta['like_count']:,}")
    return "\n".join(parts)


@router.post("/chat", response_model=ChatResponse)
async def chat_about_video(request: ChatRequest):
    """Ask a question about a YouTube video using RAG."""
    video_id = extract_video_id(request.youtube_url)
    log.info("Chat request for video %s: %.80s", video_id, request.question)

    # Auto-ingest if not already in vector DB
    if not is_video_ingested(video_id):
        log.info("Auto-ingesting video %s for chat", video_id)
        video_meta = fetch_video_metadata(request.youtube_url)
        raw = get_transcript(request.youtube_url)
        chunks = semantic_chunk_transcript(raw)
        ingest_chunks(video_id, request.youtube_url, chunks, video_meta)

    # Get video metadata from ChromaDB collection
    video_meta = get_video_metadata(video_id)
    meta_context = _format_metadata_context(video_meta) if video_meta else ""

    relevant = query_chunks(video_id, request.question, n_results=5)

    transcript_context = "\n\n".join(
        f"[{c['start_time']:.0f}s - {c['end_time']:.0f}s]: {c['text']}"
        for c in relevant
    )

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )

    log.info("Calling %s for chat answer...", settings.llm_model)
    response = await llm.ainvoke([
        {"role": "system", "content": (
            "You answer questions about a YouTube video. You have access to the video's "
            "metadata and relevant transcript excerpts. Use both to answer accurately.\n"
            "Cite timestamps in your answer using [MM:SS] format when referencing transcript content.\n"
            "If the available information doesn't cover the question, say so."
        )},
        {"role": "user", "content": (
            f"Question: {request.question}\n\n"
            f"--- Video Info ---\n{meta_context}\n\n"
            f"--- Transcript Excerpts ---\n{transcript_context}"
        )},
    ])

    log.info("Chat response generated for video %s", video_id)
    return ChatResponse(
        answer=response.content,
        sources=[
            SourceChunk(
                text=c["text"][:200],
                start_time=c["start_time"],
                end_time=c["end_time"],
            )
            for c in relevant
        ],
    )
