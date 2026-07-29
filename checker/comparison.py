from __future__ import annotations

import re
from difflib import ndiff
from typing import Any

from rapidfuzz.fuzz import ratio, token_set_ratio
from checker.semantic_matcher import semantic_similarity

WORD_PATTERN = re.compile(r"[^\w\s']+", re.UNICODE)
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "will",
    "with",
    "you",
    "your",
}

def normalize_text(text: str) -> str:
    return " ".join(WORD_PATTERN.sub(" ", text.lower()).split())
def build_word_differences(
    original_text: str,
    suggested_text: str,
) -> dict[str, list[str]]:
    original_words = original_text.split()
    suggested_words = suggested_text.split()

    removed_words: list[str] = []
    added_words: list[str] = []

    for difference in ndiff(original_words, suggested_words):
        if difference.startswith("- "):
            word = difference[2:]
            cleaned_word = word.lower().strip(".,!?;:'\"")

            if cleaned_word and cleaned_word not in STOP_WORDS:
                removed_words.append(word)

        elif difference.startswith("+ "):
            word = difference[2:]
            cleaned_word = word.lower().strip(".,!?;:'\"")

            if cleaned_word and cleaned_word not in STOP_WORDS:
                added_words.append(word)
    removed_html = original_text
    for word in removed_words:
        removed_html = removed_html.replace(
            word,
            f"<span class='diff-removed'>{word}</span>",
            1,
        )

    added_html = suggested_text
    for word in added_words:
        added_html = added_html.replace(
            word,
            f"<span class='diff-added'>{word}</span>",
            1,
        )
        return {
            "removed_words": removed_words,
            "added_words": added_words,
            "removed_html": removed_html,
            "added_html": added_html,
        }

def _overlapping_text(
    subtitle: dict[str, Any],
    segments: list[dict[str, Any]],
    tolerance: float = 0.8,
) -> str:
    start = subtitle["start_seconds"] - tolerance
    end = subtitle["end_seconds"] + tolerance
    overlapping = [
        segment["text"]
        for segment in segments
        if segment["end"] >= start and segment["start"] <= end
    ]
    return " ".join(overlapping).strip()

def generate_mismatch_explanation(
    subtitle_text: str,
    transcript_text: str,
    similarity: float,
) -> str:
    if not transcript_text:
        return (
            "No matching speech was detected during this subtitle's timestamp."
        )

    if similarity >= 85:
        return (
            "The subtitle closely matches the spoken dialogue. "
            "Only minor wording or punctuation differences may be present."
        )

    if similarity >= 65:
        return (
            f'The subtitle partially matches the spoken dialogue. '
            f'The subtitle says "{subtitle_text}", while the detected speech says '
            f'"{transcript_text}". Some words or details may be missing or changed.'
        )

    return (
        f'The subtitle does not match the spoken dialogue. '
        f'The subtitle says "{subtitle_text}", while the detected speech says '
        f'"{transcript_text}". The two lines communicate substantially different content.'
    )
def compare_subtitles_with_transcript(
    subtitle_report: dict[str, Any],
    transcription: dict[str, Any],
) -> dict[str, Any]:
    compared: list[dict[str, Any]] = []

    for subtitle in subtitle_report["subtitles"]:
        transcript_text = _overlapping_text(subtitle, transcription["segments"])
        subtitle_norm = normalize_text(subtitle["text"])
        transcript_norm = normalize_text(transcript_text)

    if not transcript_norm:
        lexical_similarity = 0.0
        semantic_score = 0.0
        similarity = 0.0
    else:
        lexical_similarity = round(
            max(
                ratio(subtitle_norm, transcript_norm),
                token_set_ratio(subtitle_norm, transcript_norm),
            ),
            2,
        )

        semantic_score = semantic_similarity(
            subtitle["text"],
            transcript_text,
        )

        hybrid_score = (
            lexical_similarity * 0.45
            + semantic_score * 0.55
        )

        similarity = round(
            max(lexical_similarity, hybrid_score),
            2,
    )
        word_differences = build_word_differences(
            subtitle["text"],
            transcript_text or subtitle["text"],
        )
        explanation = generate_mismatch_explanation(
    subtitle["text"],
    transcript_text,
    similarity,
)
        issues = list(subtitle["format_issues"])
        if not transcript_text:
            issues.append("No matching speech was detected at this timestamp")
        elif similarity < 55:
            issues.append("Subtitle text does not match the spoken dialogue")
        elif similarity < 75:
            issues.append("Subtitle text only partially matches the spoken dialogue")

        if similarity >= 85 and not subtitle["format_issues"]:
            status = "Pass"
            severity = "None"
        elif similarity >= 65:
            status = "Review"
            severity = "Medium"
        else:
            status = "Fail"
            severity = "High"

        compared.append(
    {
        **subtitle,
        "transcript_text": transcript_text or "No speech detected",
        "suggested_subtitle": transcript_text or subtitle["text"],
        "auto_fix_available": bool(transcript_text and similarity < 85),
        "removed_words": word_differences["removed_words"],
        "added_words": word_differences["added_words"],
        "removed_html": word_differences["removed_html"],
        "added_html": word_differences["added_html"],
        "text_similarity": similarity,
        "lexical_similarity": lexical_similarity,
        "semantic_similarity": semantic_score,
        "issues": issues,
        "explanation": explanation,
        "status": status,
        "severity": severity,
    }
)

    text_accuracy = round(
        sum(item["text_similarity"] for item in compared) / len(compared), 2
    )
    pass_count = sum(item["status"] == "Pass" for item in compared)
    review_count = sum(item["status"] == "Review" for item in compared)
    fail_count = sum(item["status"] == "Fail" for item in compared)

    # Text match is the main signal; format/timing quality is supporting evidence.
    overall_score = round(text_accuracy * 0.85 + subtitle_report["format_score"] * 0.15, 2)
    overall_status = (
        "PASS" if overall_score >= 85 and fail_count == 0
        else "REVIEW" if overall_score >= 65
        else "FAIL"
    )
    total_subtitles = len(compared)

    if overall_status == "PASS":
        executive_recommendation = (
            "The subtitle file is suitable for release. "
            "Only minor proofreading may be required."
        )
    elif overall_status == "REVIEW":
        executive_recommendation = (
            "The subtitle file requires manual review before release. "
            "Correct the highlighted subtitle lines."
        )
    else:
        executive_recommendation = (
            "The subtitle file is not ready for release. "
            "Correct the failed subtitle lines and run the analysis again."
        )

        executive_summary = {
            "total_subtitles": total_subtitles,
            "passed": pass_count,
            "review": review_count,
            "failed": fail_count,
            "recommendation": executive_recommendation,
        }
        return {
            **subtitle_report,
            "language": transcription["language"],
            "language_probability": transcription["language_probability"],
            "executive_summary": executive_summary,
            "text_accuracy": text_accuracy,
            "overall_score": overall_score,
            "overall_status": overall_status,
            "pass_count": pass_count,
            "review_count": review_count,
            "fail_count": fail_count,
            "subtitles": compared,
        }
