import unittest
import tempfile
import subprocess
from pathlib import Path
from src.blogger.core.photo_card_generator import (
    generate_photo_card_svg,
    render_svg_to_png,
    generate_photo_deck,
    THEMES,
    CARD_RENDERERS
)


class TestPhotoCardGenerator(unittest.TestCase):
    def test_all_templates_svg_generation(self):
        """Test that all 5 card templates generate valid non-empty SVG strings."""
        for card_type in CARD_RENDERERS.keys():
            for theme in THEMES.keys():
                data = {
                    "title": f"Test {card_type} title",
                    "hook": "4-8字爆破短语",
                    "subtitle": "副标题说明文字",
                    "category": "TEST CATEGORY",
                    "author": "TEST_AUTHOR",
                    "page_idx": "01 / 05"
                }
                svg = generate_photo_card_svg(card_type, data, theme=theme)
                self.assertIsInstance(svg, str)
                self.assertTrue(svg.startswith("<svg"))
                self.assertTrue(svg.endswith("</svg>"))
                self.assertIn('viewBox="0 0 1200 1600"', svg)

    def test_render_png_dimensions(self):
        """Test that render_svg_to_png produces exact 1200x1600 pixel PNG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            out_png = tmp_path / "test_render.png"
            data = {
                "hook": "11% 的谎言？",
                "subtitle": "测试副标题",
                "category": "AI",
                "page_idx": "01 / 01"
            }
            svg = generate_photo_card_svg("cover", data, theme="navy_gold")
            png_path = render_svg_to_png(svg, out_png, resample_width=1200)

            self.assertTrue(png_path.exists())

            # Check dimensions via sips
            res = subprocess.run(
                ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(png_path)],
                capture_output=True,
                text=True,
                check=True
            )
            self.assertIn("pixelWidth: 1200", res.stdout)
            self.assertIn("pixelHeight: 1600", res.stdout)

    def test_generate_photo_deck(self):
        """Test batch deck generation from spec."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            spec = {
                "theme": "swiss_red",
                "cards": [
                    {"type": "cover", "name": "01_cover", "data": {"hook": "爆破Hook"}},
                    {"type": "vs_comparison", "name": "02_vs", "data": {"title": "对比卡片"}},
                    {"type": "bullet_points", "name": "03_points", "data": {"title": "要点卡片"}},
                    {"type": "pipeline_steps", "name": "04_steps", "data": {"title": "步骤卡片"}},
                    {"type": "summary_cta", "name": "05_summary", "data": {"title": "总结卡片"}}
                ]
            }
            generated = generate_photo_deck(spec, tmp_path)
            self.assertEqual(len(generated), 5)
            for p in generated:
                self.assertTrue(p.exists())
                self.assertEqual(p.suffix, ".png")

    def test_clean_branding_defaults(self):
        """Test that default SVG generation produces 0 'AGENT' header brand and 0 'BLOGGER AGENT' footer watermark."""
        for card_type in CARD_RENDERERS.keys():
            # Test with no author
            svg_no_author = generate_photo_card_svg(card_type, {"title": "Test Title", "hook": "Test Hook"})
            self.assertNotIn("BLOGGER AGENT", svg_no_author)
            self.assertNotIn(">AGENT<", svg_no_author)
            self.assertNotIn(">@AGENT<", svg_no_author)

            # Test with author="Agent" (case insensitive default)
            svg_agent_author = generate_photo_card_svg(card_type, {"title": "Test Title", "hook": "Test Hook", "author": "Agent"})
            self.assertNotIn("BLOGGER AGENT", svg_agent_author)
            self.assertNotIn(">AGENT<", svg_agent_author)
            self.assertNotIn(">@AGENT<", svg_agent_author)

            # Test with custom author
            svg_custom = generate_photo_card_svg(card_type, {"title": "Test Title", "hook": "Test Hook", "author": "MyBrand"})
            self.assertIn("MYBRAND", svg_custom)


if __name__ == "__main__":
    unittest.main()
