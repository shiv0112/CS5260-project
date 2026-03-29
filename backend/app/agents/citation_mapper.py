from app.models import YTSageState


async def map_citations(state: YTSageState) -> dict:
    """Map each claim in the scripts to source timestamps in the original video."""
    # TODO: call GPT-4o to align claims with transcript timestamps
    # For now, return placeholder
    return {
        "citations": [],
        "status": "complete",
    }
