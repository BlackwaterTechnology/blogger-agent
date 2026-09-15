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
        dirty = "🎯【爆款】DevOps 工程师日常站会英文听力！🇯🇵🔥💡"
        clean = clean_video_title(dirty)
        self.assertNotIn("🎯", clean)
        self.assertNotIn("🇯🇵", clean)
        self.assertNotIn("🔥", clean)
        self.assertNotIn("💡", clean)
        self.assertIn("DevOps 工程师日常站会英文听力", clean)

    def test_clean_video_desc_length_bounds(self):
        # 1. Short desc gets padded to >= 60 chars
        short_desc = "短描述文本测试。"
        padded = clean_video_desc(short_desc)
        self.assertTrue(60 <= len(padded) <= 120, f"Padded desc length {len(padded)} not in [60, 120]")

        # 2. Long desc gets truncated to <= 120 chars
        long_desc = "这是一段非常冗长的视频描述文本，用于测试当用户输入的描述文字超过了一百二十个字符的上限时，我们的自动清洗函数能否准确将其裁剪到合规的区间内，同时保留语义完整性与句尾标点符号，确保在微信公众号视频和各大视频平台上传时不会触发参数校验失败的错误。"
        truncated = clean_video_desc(long_desc)
        self.assertTrue(60 <= len(truncated) <= 120, f"Truncated desc length {len(truncated)} not in [60, 120]")

    def test_generate_video_cover(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cover_file = Path(tmpdir) / "cover.png"
            res = generate_video_cover(
                output_path=cover_file,
                title="DevOps Engineer Daily Standup",
                tag="ASSESSMENT",
                subtitle="双字幕精听与自测",
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
                title="DevOps 工程师日常站会听力精练",
                desc="精选运维工程师日常站会英文高频对话，采用双层字幕焦点视窗与上下文流，适合沉浸式听力跟读与词汇自测。",
                collection="软件教程",
                video_filename="video.mp4",
                cover_filename="cover.png",
                sentences_path=sentences_file,
            )

            self.assertTrue(payload_md.exists())

            # Parse via standard markdown parser used by publish-video
            data = parse_markdown_payload(payload_md)
            self.assertEqual(data["title"], "DevOps 工程师日常站会听力精练")
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
