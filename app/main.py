from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.pdf_report import generate_ai_release_pdf

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from flask import Flask, flash, redirect, render_template, request, send_file, url_for, Response
from werkzeug.utils import secure_filename

from checker.comparison import compare_subtitles_with_transcript
from checker.report_generator import load_json_report, save_csv_report, save_json_report
from checker.subtitle_parser import parse_subtitle_file
from checker.transcription import TranscriptionUnavailable, transcribe_video
from agent.graph import subtitle_agent
from langchain_core.messages import HumanMessage, ToolMessage

UPLOAD_FOLDER = BASE_DIR / "uploads"
REPORT_FOLDER = BASE_DIR / "reports"
VIDEO_EXTENSIONS = {"mp4", "mov", "mkv", "avi", "webm"}
SUBTITLE_EXTENSIONS = {"srt", "vtt"}

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "development-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "500")) * 1024 * 1024
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
REPORT_FOLDER.mkdir(parents=True, exist_ok=True)


def get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def save_upload(uploaded_file) -> tuple[str, Path]:
    safe_name = secure_filename(uploaded_file.filename)
    if not safe_name:
        raise ValueError("The uploaded filename is invalid.")
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    destination = UPLOAD_FOLDER / unique_name
    uploaded_file.save(destination)
    return unique_name, destination


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    video = request.files.get("video")
    subtitle = request.files.get("subtitle")
    if not video or not video.filename:
        flash("Please select a video file.", "error")
        return redirect(url_for("index"))
    if not subtitle or not subtitle.filename:
        flash("Please select an SRT or VTT subtitle file.", "error")
        return redirect(url_for("index"))
    if get_extension(video.filename) not in VIDEO_EXTENSIONS:
        flash("Unsupported video format. Use MP4, MOV, MKV, AVI, or WEBM.", "error")
        return redirect(url_for("index"))
    if get_extension(subtitle.filename) not in SUBTITLE_EXTENSIONS:
        flash("Unsupported subtitle format. Use SRT or VTT.", "error")
        return redirect(url_for("index"))

    video_name = subtitle_name = ""
    video_path: Path | None = None
    subtitle_path: Path | None = None
    try:
        video_name, video_path = save_upload(video)
        subtitle_name, subtitle_path = save_upload(subtitle)
        agent_result = subtitle_agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="Run the complete subtitle quality assurance workflow."
                    )
                ],
                "video_path": str(video_path),
                "subtitle_path": str(subtitle_path),
            }
        )

        report = agent_result.get("comparison_report")
        
        if not report:
            raise ValueError(
                "The LangGraph agent did not return a comparison report."
            )

        report["agent_review"] = agent_result.get(
            "final_response",
            "",
        )
        report["final_decision"] = agent_result.get(
            "final_decision",
        agent_result.get("routing_reason", "REVIEW"),
        )
        report["execution_trace"] = agent_result.get(
            "execution_trace",
            [],
        )
        report_id = uuid.uuid4().hex
        report.update(
            {
                "report_id": report_id,
                "original_video_name": video.filename,
                "original_subtitle_name": subtitle.filename,
                "stored_video_name": video_name,
                "stored_subtitle_name": subtitle_name,
            }
        )
        save_json_report(report, REPORT_FOLDER / f"{report_id}.json")
        save_csv_report(report, REPORT_FOLDER / f"{report_id}.csv")
        return render_template("results.html", report=report)
    except TranscriptionUnavailable as error:
        flash(str(error), "error")
    except Exception as error:
        app.logger.exception("Subtitle analysis failed")
        flash(f"Analysis failed: {error}", "error")
    finally:
        # Uploaded media is temporary. Reports remain downloadable.
        if video_path:
            video_path.unlink(missing_ok=True)
        if subtitle_path:
            subtitle_path.unlink(missing_ok=True)
    return redirect(url_for("index"))


@app.route("/download/<report_id>.csv")
def download_csv(report_id: str):
    if not report_id.isalnum():
        return "Invalid report ID", 400
    path = REPORT_FOLDER / f"{report_id}.csv"
    if not path.is_file():
        return "Report not found", 404
    return send_file(path, as_attachment=True, download_name="subtitle_qa_report.csv")

@app.route("/download/pdf/<report_id>")
def download_pdf(report_id: str):
    if not report_id.isalnum():
        return "Invalid report ID", 400

    report_path = REPORT_FOLDER / f"{report_id}.json"

    if not report_path.is_file():
        return "Report not found", 404

    report = load_json_report(report_path)

    pdf_path = REPORT_FOLDER / f"{report_id}.pdf"
    generate_ai_release_pdf(report, pdf_path)

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name="ai_subtitle_release_report.pdf",
        mimetype="application/pdf",
    )
@app.route("/report/<report_id>")
def view_report(report_id: str):
    if not report_id.isalnum():
        return "Invalid report ID", 400
    path = REPORT_FOLDER / f"{report_id}.json"
    if not path.is_file():
        return "Report not found", 404
    return render_template("results.html", report=load_json_report(path))


@app.route("/health")
def health():
    return {"status": "healthy"}, 200


@app.errorhandler(413)
def too_large(_error):
    flash("The upload is too large. Reduce the video size and try again.", "error")
    return redirect(url_for("index"))

@app.route("/download-corrected-srt/<report_id>")
def download_corrected_srt(report_id):
    report_path = REPORT_FOLDER / f"{report_id}.json"
    if not report_path.is_file():
        return "Report not found", 404
    report = load_json_report(report_path)
    srt_lines = []
    for index, item in enumerate(report["subtitles"], start=1):
        corrected_text = (
            item.get("suggested_subtitle")
            or item.get("text")
            or ""
        )
        srt_lines.extend([
            str(index),
            f'{item["start"]} --> {item["end"]}',
            corrected_text.strip(),
            ""
        ])

    srt_content = "\n".join(srt_lines)

    return Response(
        srt_content,
        mimetype="application/x-subrip",
        headers={
            "Content-Disposition":
                'attachment; filename="corrected_subtitles.srt"'
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
