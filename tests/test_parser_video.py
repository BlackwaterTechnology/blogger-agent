from pathlib import Path
from blogger.core.markdown_parser import parse_markdown_payload
import tempfile
import os

def test_video_path_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        md_file = tmp_path / "test.md"
        video_file = tmp_path / "video.mp4"
        video_file.write_text("dummy video content")
        
        md_content = """---
title: Test Title
video: video.mp4
---
# Content
"""
        md_file.write_text(md_content)
        
        result = parse_markdown_payload(md_file)
        
        assert result["title"] == "Test Title"
        assert result["video_path"] == video_file.absolute()
        print("Test passed: video_path extracted correctly.")

if __name__ == "__main__":
    test_video_path_extraction()
