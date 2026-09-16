import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from src.blogger.core.dual_sub_video import (
    CEFR_LEVEL_PRESETS,
    clean_video_desc,
    clean_video_title,
    create_dual_sub_payload,
    create_gradient_bg,
    generate_ambient_svg,
    generate_video_cover,
    generate_video_payload_md,
    parse_time,
    parse_vtt,
    prepare_ambient_background,
    resolve_level_preset,
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

    def test_prepare_ambient_background_fallback(self):
        # When no bg_image_path is provided, should fall back to gradient
        img = prepare_ambient_background(640, 360, bg_image_path=None)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (640, 360))
        top_pixel = img.getpixel((320, 0))
        self.assertEqual(top_pixel, (11, 19, 43))

        # When nonexistent file is provided, should gracefully fall back
        img_missing = prepare_ambient_background(640, 360, bg_image_path="/nonexistent/path/to/img.png")
        self.assertEqual(img_missing.size, (640, 360))

    def test_prepare_ambient_background_with_image(self):
        # Create a bright test image with distinct dimensions to test aspect fill and crop
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            test_img_path = f.name

        try:
            bright_img = Image.new("RGB", (800, 400), "#FF5500")
            bright_img.save(test_img_path)

            ambient_img = prepare_ambient_background(
                width=640,
                height=360,
                bg_image_path=test_img_path,
                blur_radius=10,
                overlay_color="#0B132B",
                overlay_alpha=0.75,
            )
            self.assertEqual(ambient_img.size, (640, 360))
            # Blended pixel should be darker than #FF5500 due to #0B132B overlay
            pixel = ambient_img.getpixel((320, 180))
            # Red channel should be darkened by 75% overlay
            self.assertLess(pixel[0], 120)
            self.assertGreater(pixel[0], 20)
        finally:
            if os.path.exists(test_img_path):
                os.remove(test_img_path)

    def test_generate_ambient_svg(self):
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            svg_path = f.name

        try:
            out_p = generate_ambient_svg(svg_path, width=1920, height=1080)
            self.assertTrue(out_p.exists())
            content = out_p.read_text(encoding="utf-8")
            self.assertIn('viewBox="0 0 1920 1080"', content)
            self.assertIn("radialGradient", content)
            self.assertIn("#38BDF8", content)
        finally:
            if os.path.exists(svg_path):
                os.remove(svg_path)

    @mock.patch("src.blogger.core.dual_sub_video.generate_dual_subtitle_video")
    def test_create_dual_sub_payload_with_bg_image(self, mock_gen_video):
        mock_gen_video.return_value = "/dummy/video.mp4"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            sent_file = tmp_path / "input.txt"
            sent_file.write_text("Sentence one.\nSentence two.\n", encoding="utf-8")

            custom_bg = tmp_path / "custom_art.png"
            Image.new("RGB", (100, 100), "#336699").save(custom_bg)

            payload_dir = (tmp_path / "payload_out").resolve()
            res = create_dual_sub_payload(
                payload_dir=payload_dir,
                sentences_path=sent_file,
                title="Testing Ambient Video",
                desc="A test description of sufficient length to meet the requirement properly.",
                bg_image=custom_bg,
            )

            self.assertTrue((payload_dir / "bg.png").exists())
            self.assertEqual(res["bg_image"], str(payload_dir / "bg.png"))
            self.assertTrue(res["cover_path"].exists())
            self.assertTrue(res["payload_md"].exists())
            mock_gen_video.assert_called_once()
            _, kwargs = mock_gen_video.call_args
            self.assertEqual(kwargs.get("bg_image"), payload_dir / "bg.png")

    def test_resolve_level_preset_default_a2(self):
        cfg = resolve_level_preset()
        self.assertEqual(cfg["level"], "a2")
        self.assertEqual(cfg["rate"], "-12%")
        self.assertEqual(cfg["tag"], "A2 · ELEMENTARY")
        self.assertIn("CEFR A2", cfg["subtitle"])

    def test_resolve_level_preset_all_levels(self):
        for lv, expected_rate, expected_tag_part in [
            ("a2", "-12%", "ELEMENTARY"),
            ("b1", "-6%", "INTERMEDIATE"),
            ("b2", "-3%", "PROFESSIONAL"),
            ("c1", "+0%", "ADVANCED"),
        ]:
            cfg = resolve_level_preset(level=lv)
            self.assertEqual(cfg["level"], lv)
            self.assertEqual(cfg["rate"], expected_rate)
            self.assertIn(expected_tag_part, cfg["tag"])

    def test_resolve_level_preset_custom_overrides(self):
        # Custom rate and custom tag
        cfg = resolve_level_preset(level="a2", rate="-8%", tag="DEV OPS")
        self.assertEqual(cfg["rate"], "-8%")
        # Custom tag should be prefixed with level
        self.assertEqual(cfg["tag"], "A2 · DEV OPS")

        # Custom tag already with level prefix
        cfg2 = resolve_level_preset(level="b2", tag="B2 · SPECIAL")
        self.assertEqual(cfg2["tag"], "B2 · SPECIAL")


if __name__ == "__main__":
    unittest.main()
