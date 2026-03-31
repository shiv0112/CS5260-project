import json

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.models import YTSageState
from app.services.vector_store import query_chunks

log = get_logger("agent.citation_mapper")


EXTRACT_CLAIMS_PROMPT = """Extract the distinct factual claims from the following narration script.
Return ONLY valid JSON — a list of short claim strings.

Example: ["Transformers use self-attention", "BERT is bidirectional"]"""


async def map_citations(state: YTSageState) -> dict:
    """Map each claim in the scripts to source timestamps using RAG."""
    video_id = state["video_id"]
    log.info("Citation mapper started for video %s (%d scripts)", video_id, len(state["scripts"]))

    if not state["scripts"]:
        log.warning("No scripts to map citations for")
        return {"citations": [], "status": "complete"}

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    citations = []
    for script in state["scripts"]:
        log.info("Extracting claims from script: '%s'", script["concept_title"])

        claim_response = await llm.ainvoke([
            {"role": "system", "content": EXTRACT_CLAIMS_PROMPT},
            {"role": "user", "content": script["script_text"]},
        ])

        try:
            claims = json.loads(claim_response.content)
            log.info("Extracted %d claims from '%s'", len(claims), script["concept_title"])
        except json.JSONDecodeError:
            log.error("Failed to parse claims JSON: %s", claim_response.content[:200])
            claims = []

        mapped_claims = []
        for claim_text in claims:
            matches = query_chunks(video_id, claim_text, n_results=1)
            if matches:
                best = matches[0]
                timestamp = int(best["start_time"])
                base_url = state["youtube_url"].split("&t=")[0]
                mapped_claims.append({
                    "text": claim_text,
                    "timestamp": timestamp,
                    "url": f"{base_url}&t={timestamp}",
                })
                log.info("  Claim mapped → %ds: %.60s...", timestamp, claim_text)

        citations.append({
            "concept_title": script["concept_title"],
            "claims": mapped_claims,
        })

    log.info("Citation mapping complete: %d scripts processed", len(citations))
    return {"citations": citations, "status": "complete"}
