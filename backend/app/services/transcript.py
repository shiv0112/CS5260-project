from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    raise ValueError(f"Could not extract video ID from: {url}")


def get_transcript(youtube_url: str) -> list[dict]:
    """Fetch transcript and return as list of {text, start_time, end_time} chunks."""
    video_id = extract_video_id(youtube_url)
    transcript = YouTubeTranscriptApi.get_transcript(video_id)

    chunks = []
    for entry in transcript:
        chunks.append({
            "text": entry["text"],
            "start_time": entry["start"],
            "end_time": entry["start"] + entry["duration"],
        })
    return chunks


def merge_chunks(chunks: list[dict], max_duration: float = 60.0) -> list[dict]:
    """Merge small transcript chunks into larger segments (~60s each)."""
    if not chunks:
        return []

    merged = []
    current = {
        "text": chunks[0]["text"],
        "start_time": chunks[0]["start_time"],
        "end_time": chunks[0]["end_time"],
    }

    for chunk in chunks[1:]:
        if chunk["end_time"] - current["start_time"] <= max_duration:
            current["text"] += " " + chunk["text"]
            current["end_time"] = chunk["end_time"]
        else:
            merged.append(current)
            current = {
                "text": chunk["text"],
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
            }

    merged.append(current)
    return merged
