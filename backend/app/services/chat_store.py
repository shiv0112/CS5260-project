import uuid
from datetime import datetime, timezone

import aiosqlite

from app.core.config import settings
from app.core.logger import get_logger

log = get_logger("chat_store")

_db: aiosqlite.Connection | None = None


async def init_db():
    """Open SQLite connection and create tables. Called once at app startup."""
    global _db
    log.info("Initializing chat database at %s", settings.chat_db_path)
    _db = await aiosqlite.connect(settings.chat_db_path)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")

    await _db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            chat_id           TEXT PRIMARY KEY,
            video_id          TEXT NOT NULL,
            youtube_url       TEXT NOT NULL,
            running_summary   TEXT DEFAULT '',
            summary_watermark INTEGER DEFAULT 0,
            created_at        TEXT NOT NULL
        )
    """)
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_video_id ON sessions(video_id)"
    )

    await _db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id    TEXT NOT NULL REFERENCES sessions(chat_id),
            role       TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content    TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)"
    )

    # Videos table — central registry for all ingested videos
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id        TEXT PRIMARY KEY,
            youtube_url     TEXT NOT NULL,
            title           TEXT DEFAULT '',
            channel         TEXT DEFAULT '',
            duration        INTEGER DEFAULT 0,
            thumbnail       TEXT DEFAULT '',
            slideshow_path  TEXT,
            pipeline_job_id TEXT,
            chunk_count     INTEGER DEFAULT 0,
            ingested_at     TEXT NOT NULL
        )
    """)
    # Migration: add pipeline_job_id if table already exists without it
    try:
        await _db.execute("ALTER TABLE videos ADD COLUMN pipeline_job_id TEXT")
    except Exception:
        pass  # column already exists

    await _db.commit()
    log.info("Chat database initialized")


async def close_db():
    """Close the SQLite connection. Called at app shutdown."""
    global _db
    if _db:
        await _db.close()
        _db = None
        log.info("Chat database closed")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_session(video_id: str, youtube_url: str) -> str:
    """Create a new chat session. Returns the chat_id."""
    chat_id = str(uuid.uuid4())
    await _db.execute(
        "INSERT INTO sessions (chat_id, video_id, youtube_url, running_summary, summary_watermark, created_at) "
        "VALUES (?, ?, ?, '', 0, ?)",
        (chat_id, video_id, youtube_url, _now()),
    )
    await _db.commit()
    log.info("Created session %s for video %s", chat_id[:8], video_id)
    return chat_id


async def get_session(chat_id: str) -> dict | None:
    """Get a session by chat_id."""
    cursor = await _db.execute("SELECT * FROM sessions WHERE chat_id = ?", (chat_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def list_sessions(video_id: str) -> list[dict]:
    """List all sessions for a video, newest first."""
    cursor = await _db.execute(
        "SELECT chat_id, video_id, youtube_url, created_at FROM sessions "
        "WHERE video_id = ? ORDER BY created_at DESC",
        (video_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def add_message(chat_id: str, role: str, content: str) -> int:
    """Add a message to a session. Returns the message id."""
    cursor = await _db.execute(
        "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, _now()),
    )
    await _db.commit()
    return cursor.lastrowid


async def get_messages(chat_id: str) -> list[dict]:
    """Get all messages for a session, ordered chronologically."""
    cursor = await _db.execute(
        "SELECT id, chat_id, role, content, created_at FROM messages "
        "WHERE chat_id = ? ORDER BY id ASC",
        (chat_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def update_running_summary(chat_id: str, summary: str, watermark: int):
    """Update the running summary and watermark for a session."""
    await _db.execute(
        "UPDATE sessions SET running_summary = ?, summary_watermark = ? WHERE chat_id = ?",
        (summary, watermark, chat_id),
    )
    await _db.commit()
    log.info("Updated running summary for session %s (watermark=%d)", chat_id[:8], watermark)


# ── Videos CRUD ──────────────────────────────────────────────────────────────

async def upsert_video(
    video_id: str,
    youtube_url: str,
    title: str = "",
    channel: str = "",
    duration: int = 0,
    thumbnail: str = "",
    chunk_count: int = 0,
) -> None:
    """Insert or update a video record."""
    await _db.execute(
        """INSERT INTO videos (video_id, youtube_url, title, channel, duration, thumbnail, chunk_count, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(video_id) DO UPDATE SET
             youtube_url = excluded.youtube_url,
             title = excluded.title,
             channel = excluded.channel,
             duration = excluded.duration,
             thumbnail = excluded.thumbnail,
             chunk_count = excluded.chunk_count""",
        (video_id, youtube_url, title, channel, duration, thumbnail, chunk_count, _now()),
    )
    await _db.commit()
    log.info("Upserted video %s (%s)", video_id, title[:40])


async def set_pipeline_job(video_id: str, job_id: str) -> None:
    """Store the pipeline job ID for a video so any client can track it."""
    await _db.execute(
        "UPDATE videos SET pipeline_job_id = ? WHERE video_id = ?",
        (job_id, video_id),
    )
    await _db.commit()


async def set_slideshow_path(video_id: str, path: str) -> None:
    """Set the slideshow MP4 path for a video."""
    await _db.execute(
        "UPDATE videos SET slideshow_path = ? WHERE video_id = ?",
        (path, video_id),
    )
    await _db.commit()
    log.info("Slideshow path set for video %s: %s", video_id, path)


async def get_video(video_id: str) -> dict | None:
    """Get a video record by video_id."""
    cursor = await _db.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def list_videos() -> list[dict]:
    """List all ingested videos, newest first."""
    cursor = await _db.execute(
        "SELECT * FROM videos ORDER BY ingested_at DESC"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
