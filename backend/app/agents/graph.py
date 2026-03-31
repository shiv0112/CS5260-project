from langgraph.graph import StateGraph, END

from app.models import YTSageState
from app.agents.ingest import ingest_transcript
from app.agents.planner import plan_concepts
from app.agents.script_writer import write_scripts
from app.agents.citation_mapper import map_citations


def build_graph() -> StateGraph:
    """Build the LangGraph pipeline: ingest → planner → script_writer → citation_mapper."""
    graph = StateGraph(YTSageState)

    graph.add_node("ingest", ingest_transcript)
    graph.add_node("planner", plan_concepts)
    graph.add_node("script_writer", write_scripts)
    graph.add_node("citation_mapper", map_citations)
    # video_generator node will be added in Week 2

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "planner")
    graph.add_edge("planner", "script_writer")
    graph.add_edge("script_writer", "citation_mapper")
    graph.add_edge("citation_mapper", END)

    return graph.compile()
