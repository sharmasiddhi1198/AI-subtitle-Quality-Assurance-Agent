from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

TIMESTAMP_PATTERN = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{3})"
    r"\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{3})"
)
TAG_PATTERN = re.compile(r"<[^>]+>")


def timestamp_to_seconds(timestamp: str) -> float:
    normalized = timestamp.replace(",", ".")
    hours, minutes, seconds = normalized.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def clean_subtitle_text(text: str) -> str:
    without_tags = TAG_PATTERN.sub("", text)
    return " ".join(html.unescape(without_tags).split())


def _readability_status(cps: float, duration: float) -> str:
    if duration <= 0:
        return "Invalid"
    if cps <= 17:
        return "Good"
    if cps <= 20:
        return "Warning"
    return "Too Fast"


def parse_subtitle_file(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Subtitle file was not found: {path}")

    content = path.read_text(encoding="utf-8-sig", errors="replace")
    content = content.replace("\r\n", "\n").strip()
    if content.startswith("WEBVTT"):
        content = content.split("\n", 1)[1] if "\n" in content else ""

    blocks = re.split(r"\n\s*\n", content)
    subtitles: list[dict[str, Any]] = []
    previous_end = -1.0

    for block_number, block in enumerate(blocks, start=1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        timestamp_index = next(
            (i for i, line in enumerate(lines) if TIMESTAMP_PATTERN.search(line)),
            None,
        )
        if timestamp_index is None:
            continue

        match = TIMESTAMP_PATTERN.search(lines[timestamp_index])
        assert match is not None
        start = match.group("start")
        end = match.group("end")
        start_seconds = timestamp_to_seconds(start)
        end_seconds = timestamp_to_seconds(end)
        duration = round(end_seconds - start_seconds, 3)
        text = clean_subtitle_text(" ".join(lines[timestamp_index + 1 :]))
        cps = round(len(text) / duration, 2) if duration > 0 else 0.0
        readability = _readability_status(cps, duration)

        issues: list[str] = []
        if not text:
            issues.append("Empty subtitle text")
        if duration <= 0:
            issues.append("Invalid subtitle duration")
        if previous_end >= 0 and start_seconds < previous_end:
            issues.append("Overlaps previous subtitle")
        if duration > 7:
            issues.append("Subtitle remains on screen for more than 7 seconds")
        if duration > 0 and duration < 0.7:
            issues.append("Subtitle duration is shorter than 0.7 seconds")
        if readability == "Warning":
            issues.append("Reading speed may be high")
        elif readability == "Too Fast":
            issues.append("Reading speed is too high")
        if len(text) > 84:
            issues.append("Subtitle text is longer than 84 characters")

        number = (
            lines[0]
            if timestamp_index > 0 and lines[0].isdigit()
            else str(block_number)
        )
        subtitles.append(
            {
                "number": number,
                "start": start,
                "end": end,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "duration": duration,
                "text": text,
                "character_count": len(text),
                "characters_per_second": cps,
                "readability_status": readability,
                "format_issues": issues,
            }
        )
        previous_end = max(previous_end, end_seconds)

    if not subtitles:
        raise ValueError("No valid subtitle cues were found in the uploaded file.")

    issue_lines = sum(bool(item["format_issues"]) for item in subtitles)
    format_score = round((1 - issue_lines / len(subtitles)) * 100, 2)
    return {
        "file_name": path.name,
        "total_subtitles": len(subtitles),
        "format_issue_lines": issue_lines,
        "format_score": format_score,
        "average_cps": round(
            sum(item["characters_per_second"] for item in subtitles) / len(subtitles),
            2,
        ),
        "overlap_count": sum(
            "Overlaps previous subtitle" in item["format_issues"] for item in subtitles
        ),
        "fast_reading_count": sum(
            item["readability_status"] == "Too Fast" for item in subtitles
        ),
        "empty_count": sum(not item["text"] for item in subtitles),
        "subtitles": subtitles,
    }
