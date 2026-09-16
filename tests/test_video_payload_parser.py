import unittest
from pathlib import Path
from src.blogger.core.markdown_parser import parse_markdown_payload
from src.blogger.config import get_wechat_collections


class TestVideoPayloadParser(unittest.TestCase):
    def setUp(self):
        self.payload_path = Path("videos/notebooklm_auth_modes/payload.md")

    def test_parse_video_payload(self):
        if not self.payload_path.exists():
            self.skipTest(f"{self.payload_path} does not exist")

        data = parse_markdown_payload(self.payload_path)

        # 1. Basic Frontmatter Checks
        self.assertIn("notebooklm-py", data["title"])
        self.assertEqual(data["author"], "Gemini CLI")
        self.assertEqual(data["collection"], "agent")
        self.assertTrue(60 <= len(data["desc"]) <= 120, f"Desc length {len(data['desc'])} not in [60, 120]")

        # 2. Asset Auto-Detection Checks
        self.assertIsNotNone(data["video_path"], "video_path must not be None")
        self.assertTrue(data["video_path"].exists(), f"Video file not found: {data['video_path']}")
        self.assertTrue(
            data["video_path"].name.endswith("_clean.mp4") or data["video_path"].name.endswith(".mp4"),
            f"Unexpected video file name: {data['video_path'].name}"
        )

        self.assertIsNotNone(data["cover_path"], "cover_path must not be None")
        self.assertTrue(data["cover_path"].exists(), f"Cover file not found: {data['cover_path']}")

        # 3. Collection Config Validation
        allowed_video_collections = get_wechat_collections(content_type="video")
        if allowed_video_collections:
            self.assertIn(data["collection"], allowed_video_collections)

    def test_auto_detect_video_fallback(self):
        """Ensure auto-detection finds video and cover even when omitted from frontmatter."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dir = Path(tmpdir)
            
            # Create dummy media assets
            clean_video = tmp_dir / "my_video_clean.mp4"
            clean_video.touch()
            cover_img = tmp_dir / "cover.png"
            cover_img.touch()

            # Markdown with NO video and NO cover declared
            md_file = tmp_dir / "payload.md"
            md_file.write_text(
                "---\n"
                "title: \"测试视频标题\"\n"
                "author: \"Test Author\"\n"
                "desc: \"这是一段完全符合字数要求的测试视频描述文本内容，用于验证在没有显式声明视频和封面字段时，解析器能否自动嗅探并补全媒体路径。\"\n"
                "collection: \"agent\"\n"
                "---\n\n"
                "视频说明正文...\n",
                encoding="utf-8"
            )

            data = parse_markdown_payload(md_file)
            self.assertIsNotNone(data["video_path"])
            self.assertEqual(data["video_path"].name, "my_video_clean.mp4")
            self.assertIsNotNone(data["cover_path"])
            self.assertEqual(data["cover_path"].name, "cover.png")


if __name__ == "__main__":
    unittest.main()
