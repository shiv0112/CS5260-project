import hashlib
import json
import os

from app.config import settings


def _get_cache_path(youtube_url: str, concept_title: str | None = None) -> str:
    key = youtube_url
    if concept_title:
        key += f":{concept_title}"
    url_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
    return os.path.join(settings.cache_dir, f"{url_hash}.json")


def get_cached(youtube_url: str, concept_title: str | None = None) -> dict | None:
    path = _get_cache_path(youtube_url, concept_title)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def set_cached(youtube_url: str, data: dict, concept_title: str | None = None) -> None:
    os.makedirs(settings.cache_dir, exist_ok=True)
    path = _get_cache_path(youtube_url, concept_title)
    with open(path, "w") as f:
        json.dump(data, f)
