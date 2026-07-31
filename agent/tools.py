from langchain.tools import tool

from checker.transcription import transcribe_video as run_transcription

from checker.subtitle_parser import parse_subtitle_file as run_subtitle_parser
from checker.comparison import compare_subtitles_with_transcript

@tool
def transcribe_video(video_path: str) -> dict:
    """
    Transcribe a video using Faster-Whisper.

    Returns the detected language, language confidence,
    video duration, and timestamped transcript segments.
    """
    return run_transcription(video_path)

@tool
def parse_subtitles(subtitle_path: str) -> dict:
    """
    Parse subtitle file and return subtitle quality metrics.
    """
    return run_subtitle_parser(subtitle_path)


@tool
def check_dialogue_accuracy(
    subtitle_report: dict,
    transcription: dict,
) -> dict:
    """
    Compare parsed subtitles with the timestamped transcript.

    Returns subtitle-level similarity results, issues,
    corrections, severity, overall score, and release status.
    """
    return compare_subtitles_with_transcript(
        subtitle_report,
        transcription,
    )

TOOLS = [
    transcribe_video,
    parse_subtitles,
    check_dialogue_accuracy,
]