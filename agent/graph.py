from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    comparison_node,
    final_review_node,
    finalize_failure_node,
    finalize_node,
    planner_node,
    review_router_node,
    subtitle_parser_node,
    transcription_node,
)
from agent.state import AgentState


def route_from_planner(state: AgentState) -> str:
    """Send execution to the next step selected by the planner."""

    next_step = state.get("next_step", "finalize_failure")

    valid_steps = {
        "transcription",
        "subtitle_parser",
        "comparison",
        "review_router",
        "final_review",
        "finalize",
        "finalize_failure",
    }

    if next_step not in valid_steps:
        return "finalize_failure"

    return next_step


workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("transcription", transcription_node)
workflow.add_node("subtitle_parser", subtitle_parser_node)
workflow.add_node("comparison", comparison_node)
workflow.add_node("review_router", review_router_node)
workflow.add_node("final_review", final_review_node)
workflow.add_node("finalize", finalize_node)
workflow.add_node("finalize_failure", finalize_failure_node)

workflow.add_edge(START, "planner")

workflow.add_conditional_edges(
    "planner",
    route_from_planner,
    {
        "transcription": "transcription",
        "subtitle_parser": "subtitle_parser",
        "comparison": "comparison",
        "review_router": "review_router",
        "final_review": "final_review",
        "finalize": "finalize",
        "finalize_failure": "finalize_failure",
    },
)

workflow.add_edge("transcription", "planner")
workflow.add_edge("subtitle_parser", "planner")
workflow.add_edge("comparison", "planner")
workflow.add_edge("review_router", "planner")
workflow.add_edge("final_review", "planner")

workflow.add_edge("finalize", END)
workflow.add_edge("finalize_failure", END)

subtitle_agent = workflow.compile()