import tempfile
import unittest
from pathlib import Path

from checker.comparison import compare_subtitles_with_transcript
from checker.subtitle_parser import parse_subtitle_file

SRT = """1
00:00:00,000 --> 00:00:02,000
Hello world

2
00:00:03,000 --> 00:00:05,000
This is a test
"""


class CheckerTests(unittest.TestCase):
    def test_parse_and_matching_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.srt"
            path.write_text(SRT, encoding="utf-8")
            parsed = parse_subtitle_file(path)
            transcription = {
                "language": "en",
                "language_probability": 99.0,
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "Hello world"},
                    {"start": 3.0, "end": 5.0, "text": "This is a test"},
                ],
            }
            report = compare_subtitles_with_transcript(parsed, transcription)
            self.assertEqual(report["overall_status"], "PASS")
            self.assertGreaterEqual(report["text_accuracy"], 95)

    def test_mismatched_subtitles_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.srt"
            path.write_text(SRT, encoding="utf-8")
            parsed = parse_subtitle_file(path)
            transcription = {
                "language": "en",
                "language_probability": 99.0,
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "Completely different sentence"},
                    {"start": 3.0, "end": 5.0, "text": "Nothing matches here"},
                ],
            }
            report = compare_subtitles_with_transcript(parsed, transcription)
            self.assertEqual(report["overall_status"], "FAIL")
            self.assertEqual(report["fail_count"], 2)


if __name__ == "__main__":
    unittest.main()
