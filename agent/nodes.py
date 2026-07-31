import json
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.config import llm
from agent.state import AgentState
from checker.comparison import compare_subtitles_with_transcript
from checker.subtitle_parser import parse_subtitle_file
from checker.transcription import transcribe_video


def _append_unique(items: list[str] | None, value: str) -> list[str]:
    """Return a new list containing value only once."""
    updated = list(items or [])

    if value not in updated:
        updated.append(value)

    return updated


def _append_trace(state: AgentState, message: str) -> list[str]:
    """Append a recruiter-friendly workflow event."""
    return [*(state.get("execution_trace") or []), message]


def _merge_tool_output(
    state: AgentState,
    tool_name: str,
    output: Any,
) -> dict[str, Any]:
    """Preserve previous tool outputs and add the latest one."""
    outputs = dict(state.get("tool_outputs") or {})
    outputs[tool_name] = output
    return outputs


def planner_node(state: AgentState) -> dict[str, Any]:
    """
    Inspect the current state and select the next valid workflow step.

    The planner does not expose hidden reasoning. It only records the
    operational action selected from the available workflow state.
    """

    completed_steps = state.get("completed_steps") or []
    errors = state.get("errors") or []
    retry_count = state.get("retry_count", 0)

    if errors and retry_count >= 1:
        next_step = "finalize_failure"
        status = "failed"

    elif not state.get("transcription"):
        next_step = "transcription"
        status = "running"

    elif not state.get("subtitle_report"):
        next_step = "subtitle_parser"
        status = "running"

    elif not state.get("comparison_report"):
        next_step = "comparison"
        status = "running"

    elif "review_router" not in completed_steps:
        next_step = "review_router"
        status = "running"

    elif state.get("review_required") and not state.get("final_response"):
        next_step = "final_review"
        status = "running"

    else:
        next_step = "finalize"
        status = "running"

    return {
        "current_step": "planner",
        "next_step": next_step,
        "agent_status": status,
        "messages": [
            AIMessage(content=f"Planner selected next step: {next_step}.")
        ],
    }


def transcription_node(state: AgentState) -> dict[str, Any]:
    """Transcribe the uploaded video and store the result."""

    video_path = state.get("video_path")

    if not video_path:
        error = "The video path is missing from the agent state."

        return {
            "current_step": "transcription",
            "next_step": "planner",
            "agent_status": "retrying",
            "retry_count": state.get("retry_count", 0) + 1,
            "errors": [*(state.get("errors") or []), error],
            "execution_trace": _append_trace(
                state,
                "❌ Video transcription could not start",
            ),
            "messages": [AIMessage(content=error)],
        }

    try:
        transcription = transcribe_video(video_path)

        return {
            "transcription": transcription,
            "current_step": "transcription",
            "next_step": "planner",
            "completed_steps": _append_unique(
                state.get("completed_steps"),
                "transcription",
            ),
            "tool_outputs": _merge_tool_output(
                state,
                "transcription",
                transcription,
            ),
            "execution_trace": _append_trace(
                state,
                "🎬 Video transcribed successfully",
            ),
            "agent_status": "running",
            "messages": [
                AIMessage(content="Video transcription completed.")
            ],
        }

    except Exception as error:
        message = f"Video transcription failed: {error}"

        return {
            "current_step": "transcription",
            "next_step": "planner",
            "agent_status": "retrying",
            "retry_count": state.get("retry_count", 0) + 1,
            "errors": [*(state.get("errors") or []), message],
            "execution_trace": _append_trace(
                state,
                "❌ Video transcription failed",
            ),
            "messages": [AIMessage(content=message)],
        }


def subtitle_parser_node(state: AgentState) -> dict[str, Any]:
    """Parse the uploaded subtitle file and store the result."""

    subtitle_path = state.get("subtitle_path")

    if not subtitle_path:
        error = "The subtitle path is missing from the agent state."

        return {
            "current_step": "subtitle_parser",
            "next_step": "planner",
            "agent_status": "retrying",
            "retry_count": state.get("retry_count", 0) + 1,
            "errors": [*(state.get("errors") or []), error],
            "execution_trace": _append_trace(
                state,
                "❌ Subtitle parsing could not start",
            ),
            "messages": [AIMessage(content=error)],
        }

    try:
        subtitle_report = parse_subtitle_file(subtitle_path)

        return {
            "subtitle_report": subtitle_report,
            "current_step": "subtitle_parser",
            "next_step": "planner",
            "completed_steps": _append_unique(
                state.get("completed_steps"),
                "subtitle_parser",
            ),
            "tool_outputs": _merge_tool_output(
                state,
                "subtitle_parser",
                subtitle_report,
            ),
            "execution_trace": _append_trace(
                state,
                "📝 Subtitle file parsed",
            ),
            "agent_status": "running",
            "messages": [
                AIMessage(content="Subtitle parsing completed.")
            ],
        }

    except Exception as error:
        message = f"Subtitle parsing failed: {error}"

        return {
            "current_step": "subtitle_parser",
            "next_step": "planner",
            "agent_status": "retrying",
            "retry_count": state.get("retry_count", 0) + 1,
            "errors": [*(state.get("errors") or []), message],
            "execution_trace": _append_trace(
                state,
                "❌ Subtitle parsing failed",
            ),
            "messages": [AIMessage(content=message)],
        }


def comparison_node(state: AgentState) -> dict[str, Any]:
    """Compare parsed subtitles with the generated transcript."""

    subtitle_report = state.get("subtitle_report")
    transcription = state.get("transcription")

    if not subtitle_report or not transcription:
        error = (
            "Subtitle comparison requires both a transcription "
            "and a parsed subtitle report."
        )

        return {
            "current_step": "comparison",
            "next_step": "planner",
            "agent_status": "retrying",
            "retry_count": state.get("retry_count", 0) + 1,
            "errors": [*(state.get("errors") or []), error],
            "execution_trace": _append_trace(
                state,
                "❌ Subtitle comparison could not start",
            ),
            "messages": [AIMessage(content=error)],
        }

    try:
        comparison_report = compare_subtitles_with_transcript(
            subtitle_report,
            transcription,
        )

        return {
            "comparison_report": comparison_report,
            "current_step": "comparison",
            "next_step": "planner",
            "completed_steps": _append_unique(
                state.get("completed_steps"),
                "comparison",
            ),
            "tool_outputs": _merge_tool_output(
                state,
                "comparison",
                comparison_report,
            ),
            "execution_trace": _append_trace(
                state,
                "🔍 Subtitle comparison completed",
            ),
            "agent_status": "running",
            "messages": [
                AIMessage(content="Dialogue accuracy analysis completed.")
            ],
        }

    except Exception as error:
        message = f"Subtitle comparison failed: {error}"

        return {
            "current_step": "comparison",
            "next_step": "planner",
            "agent_status": "retrying",
            "retry_count": state.get("retry_count", 0) + 1,
            "errors": [*(state.get("errors") or []), message],
            "execution_trace": _append_trace(
                state,
                "❌ Subtitle comparison failed",
            ),
            "messages": [AIMessage(content=message)],
        }


def review_router_node(state: AgentState) -> dict[str, Any]:
    """Let the LLM decide whether a detailed release review is required."""

    comparison_report = state.get("comparison_report", {})

    summary_data = {
        key: value
        for key, value in comparison_report.items()
        if key != "subtitles"
    }

    try:
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a routing controller for a subtitle QA "
                        "agent. Decide whether the completed report requires "
                        "a detailed AI release review.\n\n"
                        "Return exactly two lines:\n"
                        "REVIEW_REQUIRED: YES or NO\n"
                        "REASON: one concise sentence.\n\n"
                        "A detailed review is required when release status "
                        "is FAIL or REVIEW, accuracy is below 95%, or there "
                        "are high-severity issues. Otherwise it may be skipped."
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

        routing_reason = "QA report evaluated by the review router."

        for line in text.splitlines():
            if line.upper().startswith("REASON:"):
                routing_reason = line.split(":", 1)[1].strip()
                break

        return {
            "review_required": review_required,
            "routing_reason": routing_reason,
            "current_step": "review_router",
            "next_step": "planner",
            "completed_steps": _append_unique(
                state.get("completed_steps"),
                "review_router",
            ),
            "tool_outputs": _merge_tool_output(
                state,
                "review_router",
                {
                    "review_required": review_required,
                    "reason": routing_reason,
                },
            ),
            "execution_trace": _append_trace(
                state,
                (
                    "🧭 Detailed AI review requested"
                    if review_required
                    else "🧭 Detailed AI review safely skipped"
                ),
            ),
            "agent_status": "running",
            "messages": [response],
        }

    except Exception as error:
        # Safe fallback: require review instead of silently passing.
        message = f"Review routing failed; detailed review required: {error}"

        return {
            "review_required": True,
            "routing_reason": message,
            "current_step": "review_router",
            "next_step": "planner",
            "completed_steps": _append_unique(
                state.get("completed_steps"),
                "review_router",
            ),
            "execution_trace": _append_trace(
                state,
                "⚠️ Router fallback activated",
            ),
            "agent_status": "running",
            "messages": [AIMessage(content=message)],
        }


def final_review_node(state: AgentState) -> dict[str, Any]:
    """Generate the final AI release assessment."""

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

The transcription, subtitle parsing, and comparison have already completed.
Review only the supplied QA report.

Return your answer using exactly this structure:

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
Explain how subtitle quality affects viewer experience.

Recommended Fix:
Explain exactly what should be corrected.

Executive Summary:
Write a manager-friendly summary in under 40 words.

Rules:
- Do not invent missing information.
- Do not request files.
- Do not mention file paths.
- Use only the supplied QA report.
"""
            ),
            HumanMessage(
                content=(
                    "Review this completed subtitle QA report:\n\n"
                    + json.dumps(summary_data, indent=2, default=str)
                )
            ),
        ]
    )

    ai_report = str(response.content).strip()

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
        "routing_reason": state.get("routing_reason", decision),
        "final_response": ai_report,
        "final_decision": decision,
        "current_step": "final_review",
        "next_step": "planner",
        "completed_steps": _append_unique(
            state.get("completed_steps"),
            "final_review",
        ),
        "tool_outputs": _merge_tool_output(
            state,
            "final_review",
            {
                "decision": decision,
                "report": ai_report,
            },
        ),
        "execution_trace": _append_trace(
            state,
            f"🤖 AI release assessment completed: {decision}",
        ),
        "agent_status": "running",
        "messages": [response],
    }


def finalize_node(state: AgentState) -> dict[str, Any]:
    """Finish a successful workflow and supply a fallback PASS summary."""

    comparison_report = state.get("comparison_report", {})
    final_response = state.get("final_response")
    final_decision = state.get("final_decision")

    if not final_response:
        final_decision = str(
            comparison_report.get("overall_status", "PASS")
        ).upper()

        final_response = (
            f"Release Decision:\n{final_decision}\n\n"
            "Confidence:\nBased on completed automated QA checks.\n\n"
            "Executive Summary:\n"
            "Automated subtitle QA completed without requiring an "
            "additional detailed AI review."
        )

    return {
        "final_response": final_response,
        "final_decision": final_decision or "REVIEW",
        "current_step": "finalize",
        "next_step": "end",
        "completed_steps": _append_unique(
            state.get("completed_steps"),
            "finalize",
        ),
        "execution_trace": _append_trace(
            state,
            "✅ Autonomous QA workflow completed",
        ),
        "agent_status": "completed",
        "messages": [
            AIMessage(content="Autonomous subtitle QA workflow completed.")
        ],
    }


def finalize_failure_node(state: AgentState) -> dict[str, Any]:
    """Stop safely after an unrecoverable workflow error."""

    errors = state.get("errors") or ["Unknown workflow error."]

    final_response = (
        "Release Decision:\nREVIEW\n\n"
        "Confidence:\nLow\n\n"
        "Root Cause Analysis:\n"
        + "\n".join(f"- {error}" for error in errors)
        + "\n\nRisk Assessment:\nHigh\n\n"
        "Recommended Fix:\nResolve the workflow error and rerun QA.\n\n"
        "Executive Summary:\n"
        "Automated QA could not complete safely. Manual review is required."
    )

    return {
        "review_required": True,
        "routing_reason": "Workflow execution failed.",
        "final_response": final_response,
        "final_decision": "REVIEW",
        "current_step": "finalize_failure",
        "next_step": "end",
        "completed_steps": _append_unique(
            state.get("completed_steps"),
            "finalize_failure",
        ),
        "execution_trace": _append_trace(
            state,
            "🛑 Workflow stopped safely after an error",
        ),
        "agent_status": "failed",
        "messages": [AIMessage(content=final_response)],
    }