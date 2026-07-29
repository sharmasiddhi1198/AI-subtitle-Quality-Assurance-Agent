from typing import Annotated, Any, Literal

from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


ReleaseDecision = Literal["GO", "REVIEW REQUIRED", "NO-GO"]


class AgentState(TypedDict, total=False):
    """
    Shared state carried through the complete LangGraph workflow.

    Each node reads the information it needs and returns only the fields
    it wants to add or update.
    """

    # Conversation and LLM activity
    messages: Annotated[list[AnyMessage], add_messages]

    # User inputs
    video_path: str
    subtitle_path: str
    content_title: str
    language: str
    target_market: str
    content_type: str
    release_notes: str

    # Tool outputs
    transcript_segments: list[dict[str, Any]]
    subtitle_segments: list[dict[str, Any]]
    accuracy_results: dict[str, Any]
    timing_results: dict[str, Any]
    readability_results: dict[str, Any]
    severity_results: dict[str, Any]
    correction_results: list[dict[str, Any]]

    # Agent planning and execution
    selected_tools: list[str]
    completed_tools: list[str]
    execution_trace: list[dict[str, Any]]
    next_action: str
    requires_human_review: bool

    # Final decision
    final_decision: ReleaseDecision
    overall_score: float
    confidence_score: float
    decision_reasoning: str
    recommended_actions: list[str]
    executive_summary: str

    # Error handling
    errors: list[str]