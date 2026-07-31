from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    comparison_node,
    final_review_node,
    review_router_node,
    subtitle_parser_node,
    transcription_node,
)
from agent.state import AgentState

def route_after_transcription(state: AgentState):
    if not state.get("transcription"):
        return END
    return "continue"


def route_after_subtitle_parser(state: AgentState):
    if not state.get("subtitle_report"):
        return END
    return "continue"


def route_after_comparison(state: AgentState):
    if not state.get("comparison_report"):
        return END
    return "continue"

workflow = StateGraph(AgentState)

workflow.add_node("transcription", transcription_node)
workflow.add_node("subtitle_parser", subtitle_parser_node)
workflow.add_node("comparison", comparison_node)
workflow.add_node("review_router", review_router_node)
workflow.add_node("final_review", final_review_node)

workflow.add_edge(START, "transcription")
workflow.add_conditional_edges(
    "transcription",
    route_after_transcription,
    {
        "continue": "subtitle_parser",
        END: END,
    },
)

workflow.add_conditional_edges(
    "subtitle_parser",
    route_after_subtitle_parser,
    {
        "continue": "comparison",
        END: END,
    },
)

workflow.add_conditional_edges(
    "comparison",
    route_after_comparison,
    {
        "continue": "review_router",
        END: END,
    },
)
def route_after_review_router(state: AgentState):
    if state.get("review_required"):
        return "final_review"
    return END
workflow.add_conditional_edges(
    "review_router",
    route_after_review_router,
    {
        "final_review": "final_review",
        END: END,
    },
)
workflow.add_edge("final_review", END)

subtitle_agent = workflow.compile()