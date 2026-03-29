from app.models import YTSageState


async def plan_concepts(state: YTSageState) -> dict:
    """Identify and rank top 3 concepts from the transcript."""
    # TODO: call GPT-4o to analyze transcript chunks and rank concepts
    # For now, return placeholder
    return {
        "top_concepts": [],
        "status": "processing",
    }
