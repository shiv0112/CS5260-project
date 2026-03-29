from app.models import YTSageState


async def write_scripts(state: YTSageState) -> dict:
    """Write ~30-second narration scripts for the top 2 concepts."""
    # TODO: call GPT-4o to write scripts grounded in transcript segments
    # For now, return placeholder
    return {
        "scripts": [],
        "status": "processing",
    }
