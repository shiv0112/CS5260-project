from fastapi import APIRouter, HTTPException, Query

from app.core.logger import get_logger
from app.services.vector_store import get_chroma_client, collection_name

log = get_logger("api.debug")
router = APIRouter(prefix="/debug", tags=["debug"])


def _normalize_video_id(video_id: str) -> str:
    """Strip the yt_ prefix if someone passes the full collection name."""
    if video_id.startswith("yt_"):
        return video_id[3:]
    return video_id


@router.get("/collections")
async def list_collections():
    """List all ChromaDB collections with chunk counts."""
    client = get_chroma_client()
    collections = client.list_collections()
    return {
        "count": len(collections),
        "collections": [
            {"name": c.name, "chunks": c.count()}
            for c in collections
        ],
    }


@router.get("/collections/{video_id}")
async def get_collection_info(video_id: str):
    """Get details about a video's collection. Accepts video ID or full collection name."""
    video_id = _normalize_video_id(video_id)
    client = get_chroma_client()
    name = collection_name(video_id)

    try:
        col = client.get_collection(name)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Collection {name} not found")

    count = col.count()
    # Fetch all chunks (metadata + text, no embeddings to keep response small)
    data = col.get(include=["documents", "metadatas"])

    chunks = []
    for i in range(len(data["ids"])):
        chunks.append({
            "id": data["ids"][i],
            "text": data["documents"][i][:200] + ("..." if len(data["documents"][i]) > 200 else ""),
            "text_length": len(data["documents"][i]),
            "metadata": data["metadatas"][i],
        })

    # Sort by chunk_index
    chunks.sort(key=lambda c: c["metadata"].get("chunk_index", 0))

    return {
        "collection": name,
        "total_chunks": count,
        "chunks": chunks,
    }


@router.get("/collections/{video_id}/search")
async def search_collection(
    video_id: str,
    q: str = Query(..., description="Search query"),
    n: int = Query(5, ge=1, le=20, description="Number of results"),
):
    """Search a video's collection with a text query (uses embedding similarity)."""
    video_id = _normalize_video_id(video_id)
    from app.services.vector_store import query_chunks

    try:
        results = query_chunks(video_id, q, n_results=n)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "query": q,
        "results": results,
    }


@router.delete("/collections/{video_id}")
async def delete_collection(video_id: str):
    """Delete a video's collection from ChromaDB."""
    video_id = _normalize_video_id(video_id)
    client = get_chroma_client()
    name = collection_name(video_id)

    try:
        client.delete_collection(name)
        log.info("Deleted collection %s", name)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Collection {name} not found")

    return {"deleted": name}
