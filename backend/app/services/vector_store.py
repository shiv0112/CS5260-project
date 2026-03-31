import chromadb
from chromadb.errors import InvalidCollectionException
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logger import get_logger

log = get_logger("vector_store")

_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Lazy singleton for persistent ChromaDB client."""
    global _client
    if _client is None:
        log.info("Initializing ChromaDB client at %s", settings.chroma_persist_dir)
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )


def collection_name(video_id: str) -> str:
    """One collection per video. Format: yt_{video_id}."""
    return f"yt_{video_id}"


def ingest_chunks(
    video_id: str,
    youtube_url: str,
    chunks: list[dict],
    video_metadata: dict | None = None,
) -> str:
    """Embed and store chunks in ChromaDB. Idempotent — re-ingests if called again.

    video_metadata is stored on the collection level and key fields on each chunk.
    """
    client = get_chroma_client()
    name = collection_name(video_id)

    # Delete existing collection for this video (re-ingest)
    try:
        client.delete_collection(name)
        log.info("Deleted existing collection %s for re-ingestion", name)
    except (ValueError, InvalidCollectionException):
        pass

    # Store video metadata at collection level
    # ChromaDB collection metadata only supports str/int/float values
    col_metadata = {"hnsw:space": "cosine"}
    if video_metadata:
        col_metadata["title"] = video_metadata.get("title", "")
        col_metadata["channel"] = video_metadata.get("channel", "")
        col_metadata["uploader"] = video_metadata.get("uploader", "")
        col_metadata["upload_date"] = video_metadata.get("upload_date", "")
        col_metadata["duration"] = video_metadata.get("duration", 0)
        col_metadata["language"] = video_metadata.get("language", "")
        col_metadata["view_count"] = video_metadata.get("view_count", 0)
        col_metadata["like_count"] = video_metadata.get("like_count", 0)
        col_metadata["thumbnail"] = video_metadata.get("thumbnail", "")
        col_metadata["description"] = video_metadata.get("description", "")[:500]
        col_metadata["summary"] = video_metadata.get("summary", "")
        # ChromaDB metadata only supports str/int/float — serialize lists
        tags = video_metadata.get("tags", [])
        col_metadata["tags"] = ",".join(tags) if isinstance(tags, list) else str(tags)
        categories = video_metadata.get("categories", [])
        col_metadata["categories"] = ",".join(categories) if isinstance(categories, list) else str(categories)

    col = client.get_or_create_collection(
        name=name,
        metadata=col_metadata,
    )

    embedder = get_embeddings()
    texts = [c["text"] for c in chunks]

    log.info("Embedding %d chunks via %s...", len(texts), settings.embedding_model)
    embeddings = embedder.embed_documents(texts)
    log.info("Embedding complete, storing in collection %s", name)

    # Per-chunk metadata includes chunk timing + video context
    ids = [f"{video_id}_chunk_{c['chunk_index']}" for c in chunks]
    metadatas = []
    for c in chunks:
        chunk_meta = {
            "start_time": c["start_time"],
            "end_time": c["end_time"],
            "chunk_index": c["chunk_index"],
            "youtube_url": youtube_url,
            "video_id": video_id,
        }
        if video_metadata:
            chunk_meta["title"] = video_metadata.get("title", "")
            chunk_meta["channel"] = video_metadata.get("channel", "")
        metadatas.append(chunk_meta)

    col.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    log.info("Ingestion complete: %d chunks stored in %s", len(chunks), name)
    return name


def get_video_metadata(video_id: str) -> dict | None:
    """Retrieve video metadata stored on the collection."""
    client = get_chroma_client()
    try:
        col = client.get_collection(collection_name(video_id))
    except (ValueError, InvalidCollectionException):
        return None

    meta = col.metadata or {}
    # Filter out ChromaDB internal keys
    return {k: v for k, v in meta.items() if not k.startswith("hnsw:")}


def query_chunks(
    video_id: str,
    query: str,
    n_results: int = 5,
) -> list[dict]:
    """Retrieve top-k relevant chunks for a query."""
    client = get_chroma_client()
    col = client.get_collection(collection_name(video_id))

    embedder = get_embeddings()
    query_embedding = embedder.embed_query(query)

    results = col.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "start_time": results["metadatas"][0][i]["start_time"],
            "end_time": results["metadatas"][0][i]["end_time"],
            "chunk_index": results["metadatas"][0][i]["chunk_index"],
            "distance": results["distances"][0][i],
        })

    log.info("Query retrieved %d chunks (query: %.60s...)", len(chunks), query)
    return chunks


def is_video_ingested(video_id: str) -> bool:
    """Check if a video has already been ingested into ChromaDB."""
    client = get_chroma_client()
    try:
        col = client.get_collection(collection_name(video_id))
        count = col.count()
        log.info("Video %s ingestion check: %d chunks found", video_id, count)
        return count > 0
    except (ValueError, InvalidCollectionException):
        log.info("Video %s not ingested yet", video_id)
        return False
