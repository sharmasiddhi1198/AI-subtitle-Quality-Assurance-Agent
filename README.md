# AI Subtitle Quality Assurance Agent

A Dockerized Flask application that accepts a video plus an SRT/VTT subtitle file, transcribes speech using `faster-whisper`, compares each subtitle cue with overlapping speech, checks timing/readability, displays filters, and exports a CSV report.

## What the score means

- **Speech-text match:** similarity between subtitle text and Whisper transcription at the same timestamp.
- **Format score:** internal subtitle checks such as overlaps, invalid duration, reading speed, and line length.
- **Overall accuracy:** 85% speech-text match + 15% format score.

Speech recognition is probabilistic. Audio clarity, accents, background music, language, and model size affect accuracy.

## Local setup

Python 3.11 is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app\main.py
```

Open `http://127.0.0.1:5000`.

The first analysis downloads the Whisper model and can take several minutes. The default model is `tiny`. For non-English videos, set `WHISPER_MODEL=tiny`.

## Docker

```bash
docker build -t subtitle-qa-agent .
docker run --rm -p 5000:10000 -e PORT=10000 subtitle-qa-agent
```

Open `http://127.0.0.1:5000`.

## Render

This repository includes `render.yaml` and a Dockerfile. Local speech transcription needs more memory than Render's smallest free instances; the blueprint uses the Starter plan. Change the plan only after testing memory usage.

## Tests

```bash
python -m unittest discover -s tests -v
```
