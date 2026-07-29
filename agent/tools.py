from langchain.tools import tool


@tool
def transcribe_video(video_path: str):
    """Transcribe uploaded video."""
    raise NotImplementedError


@tool
def parse_subtitles(subtitle_path: str):
    """Parse subtitle file."""
    raise NotImplementedError


@tool
def check_dialogue_accuracy():
    """Compare transcript and subtitles."""
    raise NotImplementedError


@tool
def check_timing():
    """Check subtitle timing."""
    raise NotImplementedError


@tool
def check_readability():
    """Evaluate subtitle readability."""
    raise NotImplementedError


@tool
def classify_severity():
    """Determine issue severity."""
    raise NotImplementedError


@tool
def generate_corrections():
    """Generate subtitle corrections."""
    raise NotImplementedError


TOOLS = [
    transcribe_video,
    parse_subtitles,
    check_dialogue_accuracy,
    check_timing,
    check_readability,
    classify_severity,
    generate_corrections,
]