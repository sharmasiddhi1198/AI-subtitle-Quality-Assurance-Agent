from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def save_json_report(report: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_json_report(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_csv_report(report: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "number", "start", "end", "subtitle_text", "transcript_text",
        "text_similarity", "characters_per_second", "status", "severity", "issues",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in report["subtitles"]:
            writer.writerow(
                {
                    "number": item["number"],
                    "start": item["start"],
                    "end": item["end"],
                    "subtitle_text": item["text"],
                    "transcript_text": item["transcript_text"],
                    "text_similarity": item["text_similarity"],
                    "characters_per_second": item["characters_per_second"],
                    "status": item["status"],
                    "severity": item["severity"],
                    "issues": "; ".join(item["issues"]),
                }
            )
    return path
