from typing import Annotated, Any

from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    Shared state for the Subtitle QA LangGraph workflow.
    """

    # Conversation and tool-calling history
    messages: Annotated[list[AnyMessage], add_messages]

    # Uploaded file paths
    video_path: str
    subtitle_path: str

    # Tool outputs
    transcription: dict[str, Any]
    subtitle_report: dict[str, Any]
    comparison_report: dict[str, Any]
    execution_trace: list[str]

    # Final agent response
    final_response: str
    final_decision: str

    #LLM routing decision
    review_required: bool
    routing_reason: str

    # Error handling
    errors: list[str]