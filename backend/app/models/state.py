from typing import TypedDict


class YTSageState(TypedDict):
    youtube_url: str
    video_id: str
    transcript_chunks: list[dict]   # {text, start_time, end_time, chunk_index}
    top_concepts: list[dict]        # {title, description, relevant_keywords, rank}
    scripts: list[dict]             # {concept_title, script_text, segments_used}
    citations: list[dict]           # {concept_title, claims: [{text, timestamp, url}]}
    video_urls: list[dict]          # {concept_title, video_url}
    status: str                     # processing | complete | error
    error_message: str
