import json
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.config import llm
from agent.prompts import SYSTEM_PROMPT
from agent.state import AgentState
from checker.comparison import compare_subtitles_with_transcript
from checker.subtitle_parser import parse_subtitle_file
from checker.transcription import transcribe_video


def transcription_node(state: AgentState) -> dict[str, Any]:
    """
    Transcribe the uploaded video and store the result in AgentState.
    """

    video_path = state.get("video_path")

    if not video_path:
        raise ValueError("The video path is missing from the agent state.")

    transcription = transcribe_video(video_path)

    return {
    "transcription": transcription,
    "execution_trace": [
        "🎬 Video transcribed successfully"
    ],
    "messages": [
        AIMessage(content="Video transcription completed.")
    ],
}


def subtitle_parser_node(state: AgentState) -> dict[str, Any]:
    """
    Parse the uploaded subtitle file and store the result in AgentState.
    """

    subtitle_path = state.get("subtitle_path")

    if not subtitle_path:
        raise ValueError("The subtitle path is missing from the agent state.")

    subtitle_report = parse_subtitle_file(subtitle_path)

    return {
    "subtitle_report": subtitle_report,
    "execution_trace": [
        "📝 Subtitle file parsed"
    ],
    "messages": [
        AIMessage(content="Subtitle parsing completed.")
    ],
}


def comparison_node(state: AgentState) -> dict[str, Any]:
    """
    Compare parsed subtitles with the generated transcript.
    """

    subtitle_report = state.get("subtitle_report")
    transcription = state.get("transcription")

    if not subtitle_report:
        raise ValueError("The parsed subtitle report is missing.")

    if not transcription:
        raise ValueError("The video transcription is missing.")

    comparison_report = compare_subtitles_with_transcript(
        subtitle_report,
        transcription,
    )

    return {
    "comparison_report": comparison_report,
    "execution_trace": [
    "🎬 Video transcribed successfully",
    "📝 Subtitle file parsed",
    "🔍 Subtitle comparison completed",
    ],
    "messages": [
        AIMessage(content="Dialogue accuracy analysis completed.")
    ],
}
def review_router_node(state: AgentState) -> dict[str, Any]:
    """
    Let the LLM decide whether a detailed final review is required.
    """

    comparison_report = state.get("comparison_report", {})

    summary_data = {
        key: value
        for key, value in comparison_report.items()
        if key != "subtitles"
    }

    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are a routing controller for a subtitle QA agent. "
                    "Decide whether the completed report requires a detailed "
                    "AI release review. Return exactly two lines:\n"
                    "REVIEW_REQUIRED: YES or NO\n"
                    "REASON: one concise sentence.\n\n"
                    "A detailed review is required when the release status is "
                    "FAIL or REVIEW, when accuracy is below 95%, or when there "
                    "are high-severity issues. Otherwise, it may be skipped."
                )
            ),
            HumanMessage(
                content=(
                    "Completed QA report:\n\n"
                    + json.dumps(summary_data, default=str)
                )
            ),
        ]
    )

    text = str(response.content).strip()
    review_required = "REVIEW_REQUIRED: YES" in text.upper()

    routing_reason = ""
    for line in text.splitlines():
        if line.upper().startswith("REASON:"):
            routing_reason = line.split(":", 1)[1].strip()
            break

    return {
        "review_required": review_required,
        "routing_reason": routing_reason,
        "messages": [response],
    }

def final_review_node(state: AgentState) -> dict[str, Any]:
    """
    Final LLM review of the completed subtitle QA report.
    """

    comparison_report = state.get("comparison_report", {})

    summary_data = {
        key: value
        for key, value in comparison_report.items()
        if key != "subtitles"
    }

    subtitle_findings = comparison_report.get("subtitles", [])

    if isinstance(subtitle_findings, list):
        summary_data["sample_findings"] = subtitle_findings[:3]

    response = llm.invoke(
        [
            SystemMessage(
                content="""
You are the Final AI Release Manager for a subtitle quality assurance system.

The transcription, subtitle parsing, and comparison have already completed successfully.

Review ONLY the supplied QA report.

Return your answer using EXACTLY this structure:

Release Decision:
PASS / REVIEW / FAIL

Confidence:
0-100%

Root Cause Analysis:
- Explain why the subtitle passed or failed.
- Mention dialogue mismatch if present.
- Mention formatting.
- Mention timing.
- Mention readability.
- Mention language detection.

Risk Assessment:
Low / Medium / High / Critical

Business Impact:
Explain how the subtitle quality affects viewer experience.

Recommended Fix:
Explain exactly what should be corrected.

Executive Summary:
Write a short manager-friendly summary in under 40 words.

Rules:
- Do not invent missing information.
- Do not request files.
- Do not mention file paths.
- Use only the supplied QA report.
"""
            ),
            HumanMessage(
                content=
                    "Review this completed subtitle QA report:\n\n"
                    + json.dumps(summary_data, indent=2, default=str)
            ),
        ]
    )

    ai_report = response.content.strip()

    decision_match = re.search(
       r"Release Decision:\s*(PASS|REVIEW|FAIL)\b",
       ai_report,
       re.IGNORECASE,
    )

    decision = (
       decision_match.group(1).upper()
       if decision_match
       else "REVIEW"
    )

    return {
        "review_required": decision != "PASS",
        "routing_reason": decision,
        "final_response": ai_report,
        "final_decision": decision,
        "messages": [response],
    }