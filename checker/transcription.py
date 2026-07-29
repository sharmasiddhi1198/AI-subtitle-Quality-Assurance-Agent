from __future__ import annotations

import os
import gc
from pathlib import Path
from typing import Any


class TranscriptionUnavailable(RuntimeError):
    """Raised when the speech-to-text engine cannot be used."""


def _get_model():
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        raise TranscriptionUnavailable(
            f"faster-whisper could not be imported: "
            f"{type(exc)._name_}: {exc}"
        ) from exc

    model_name = os.getenv("WHISPER_MODEL", "tiny")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    try:
        return WhisperModel(model_name, device=device, compute_type=compute_type)
    except Exception as exc:
        raise TranscriptionUnavailable(
            f"Whisper model '{model_name}' could not be loaded: {exc}"
        ) from exc


def transcribe_video(video_path: str | Path) -> dict[str, Any]:
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video file was not found: {path}")

    model = _get_model()
    try:
        segments_iter, info = model.transcribe(
            str(path),
            beam_size=1,
            vad_filter=True,
            word_timestamps=False,
        )
        segments = [
            {
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": " ".join(segment.text.split()),
            }
            for segment in segments_iter
            if segment.text and segment.text.strip()
        ]
    except Exception as exc:
        raise TranscriptionUnavailable(f"Video transcription failed: {exc}") from exc
    finally:
        del model
        gc.collect()
    if not segments:
        raise TranscriptionUnavailable(
            "No speech was detected in the video. Check that the video contains audible dialogue."
        )

    return {
        "language": getattr(info, "language", None) or "unknown",
        "language_probability": round(
            float(getattr(info, "language_probability", 0.0)) * 100, 2
        ),
        "duration": round(max(segment["end"] for segment in segments), 3),
        "segments": segments,
    }
