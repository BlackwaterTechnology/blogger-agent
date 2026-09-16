import os
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from src.blogger.core.dual_sub_video import (
    clean_video_desc,
    clean_video_title,
    create_dual_sub_payload,
    create_gradient_bg,
    generate_video_cover,
    generate_video_payload_md,
    parse_time,
    parse_vtt,
    wrap_text,
)
from src.blogger.core.markdown_parser import parse_markdown_payload
from src.blogger.config import get_wechat_collections


class TestDualSubVideoCore(unittest.TestCase):
    def test_parse_time(self):
        self.assertAlmostEqual(parse_time("00:00:01.500"), 1.5)
        self.assertAlmostEqual(parse_time("00:01:30.000"), 90.0)
        self.assertAlmostEqual(parse_time("01:02:03,456"), 3723.456)
        self.assertAlmostEqual(parse_time("02:15.500"), 135.5)

    def test_parse_vtt(self):
        vtt_content = """WEBVTT

00:00:00.000 --> 00:00:03.200
Hello world, welcome to language learning.

00:00:03.500 --> 00:00:07.100
This is the second practice sentence.
"""
        with tempfile.NamedTemporaryFile("w", suffix=".vtt", delete=False) as f:
            f.write(vtt_content)
            tmp_name = f.name

        try:
            cues = parse_vtt(tmp_name)
            self.assertEqual(len(cues), 2)
            self.assertAlmostEqual(cues[0]["start"], 0.0)
            self.assertAlmostEqual(cues[0]["end"], 3.2)
            self.assertEqual(cues[0]["text"], "Hello world, welcome to language learning.")
            self.assertAlmostEqual(cues[1]["start"], 3.5)
            self.assertAlmostEqual(cues[1]["end"], 7.1)
            self.assertEqual(cues[1]["text"], "This is the second practice sentence.")
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

    def test_create_gradient_bg(self):
        img = create_gradient_bg(640, 360, top_hex="#0B132B", bottom_hex="#1C2541")
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (640, 360))
        self.assertEqual(img.mode, "RGB")
        top_pixel = img.getpixel((320, 0))
        self.assertEqual(top_pixel, (11, 19, 43))

    def test_wrap_text(self):
        img = Image.new("RGB", (1000, 100))
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        long_text = "This is a long sentence meant to test wrapping across multiple lines properly."
        lines = wrap_text(long_text, font, max_width=100, draw=draw)
        self.assertGreater(len(lines), 1)
        reconstructed = " ".join(lines)
        self.assertEqual(reconstructed, long_text)

    def test_clean_video_title(self):
        dirty = "🎯【Daily Drill】DevOps Daily Standup English Practice! 🇯🇵🔥💡"
        clean = clean_video_title(dirty)
        self.assertNotIn("🎯", clean)
        self.assertNotIn("🇯🇵", clean)
        self.assertNotIn("🔥", clean)
        self.assertNotIn("💡", clean)
        self.assertIn("DevOps Daily Standup English Practice", clean)

    def test_clean_video_desc_length_bounds(self):
        # 1. Short desc gets padded to >= 60 chars in English
        short_desc = "Daily standup drill."
        padded = clean_video_desc(short_desc)
        self.assertTrue(60 <= len(padded) <= 120, f"Padded desc length {len(padded)} not in [60, 120]")
        self.assertIn("Featuring dual-tier subtitles", padded)

        # 2. Empty desc with default_title gets generated in English
        gen_desc = clean_video_desc("", default_title="DevOps Standup")
        self.assertTrue(60 <= len(gen_desc) <= 120, f"Generated desc length {len(gen_desc)} not in [60, 120]")
        self.assertIn("Master English listening with DevOps Standup", gen_desc)

        # 3. Long desc gets truncated to <= 120 chars
        long_desc = "This is an exceptionally long and verbose video description written in English to thoroughly test that our video description sanitizer properly truncates text to satisfy platform limits without errors."
        truncated = clean_video_desc(long_desc)
        self.assertTrue(60 <= len(truncated) <= 120, f"Truncated desc length {len(truncated)} not in [60, 120]")
        self.assertTrue(truncated.endswith("."))

    def test_generate_video_cover(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cover_file = Path(tmpdir) / "cover.png"
            res = generate_video_cover(
                output_path=cover_file,
                title="DevOps Daily Standup English Listening Practice",
                tag="LISTENING PRACTICE",
            )
            self.assertTrue(res.exists())
            with Image.open(res) as img:
                self.assertEqual(img.size, (1920, 1080))
                self.assertEqual(img.mode, "RGB")

    def test_generate_video_payload_md_and_parser_compatibility(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create sample sentences
            sentences_file = tmp_path / "sentences.txt"
            sentences_file.write_text(
                "Good morning team, let's start the standup.\n"
                "I deployed the canary release to production.\n",
                encoding="utf-8"
            )

            # Dummy video and cover files
            (tmp_path / "video.mp4").touch()
            (tmp_path / "cover.png").touch()

            payload_md = generate_video_payload_md(
                payload_dir=tmp_path,
                title="DevOps Daily Standup English Listening Practice",
                desc="Practice daily DevOps standup English with dual-tier subtitles and live context stream for immersive listening.",
                collection="软件教程",
                video_filename="video.mp4",
                cover_filename="cover.png",
                sentences_path=sentences_file,
            )

            self.assertTrue(payload_md.exists())
            md_content = payload_md.read_text(encoding="utf-8")
            self.assertIn("## Overview & Learning Objectives", md_content)
            self.assertIn("## Sentence-by-Sentence Transcript", md_content)

            # Parse via standard markdown parser used by publish-video
            data = parse_markdown_payload(payload_md)
            self.assertEqual(data["title"], "DevOps Daily Standup English Listening Practice")
            self.assertEqual(data["author"], "Blogger Agent")
            self.assertEqual(data["collection"], "软件教程")
            self.assertTrue(60 <= len(data["desc"]) <= 120)
            self.assertIsNotNone(data["video_path"])
            self.assertTrue(data["video_path"].exists())
            self.assertIsNotNone(data["cover_path"])
            self.assertTrue(data["cover_path"].exists())

            # Verify collection is allowed in blogger.toml
            allowed_collections = get_wechat_collections(content_type="video")
            if allowed_collections:
                self.assertIn(data["collection"], allowed_collections)


if __name__ == "__main__":
    unittest.main()
