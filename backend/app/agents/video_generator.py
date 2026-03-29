from app.models import YTSageState


async def generate_videos(state: YTSageState) -> dict:
    """Generate AI explainer videos using Runway or Kling API."""
    # TODO: Week 2 - integrate Runway/Kling API
    return {
        "video_urls": [],
        "status": "complete",
    }
