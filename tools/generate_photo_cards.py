#!/usr/bin/env python3
"""
CLI Tool for generating 3:4 Vertical High-Resolution Cards for WeChat Photo Messages.

Usage Examples:
  # 1. Generate from a JSON or YAML deck config:
  python tools/generate_photo_cards.py --config deck_spec.json --output-dir ./articles/2026-08-28-photo-agent/

  # 2. Generate a single Cover card:
  python tools/generate_photo_cards.py --type cover --hook "11% 的谎言？" --subtitle "揭开对冲基金静态套利幻觉" --theme navy_gold -o cover.png

  # 3. Generate a VS Comparison card:
  python tools/generate_photo_cards.py --type vs_comparison --title "认知重构：旧模式 vs 新范式" --theme swiss_red -o 02_vs.png

  # 4. Generate a 3-pillar points card:
  python tools/generate_photo_cards.py --type bullet_points --title "系统落地三大硬核支柱" --theme slate_lime -o 03_points.png
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.blogger.core.photo_card_generator import (
    generate_photo_card_svg,
    render_svg_to_png,
    generate_photo_deck,
    THEMES,
    CARD_RENDERERS
)
from loguru import logger


def load_config_file(config_path: Path) -> dict:
    """Load JSON or YAML deck configuration."""
    content = config_path.read_text(encoding="utf-8")
    if config_path.suffix in [".yaml", ".yml"]:
        try:
            import yaml
            return yaml.safe_load(content)
        except ImportError:
            # Fallback if yaml is not installed: try parsing as json
            try:
                return json.loads(content)
            except Exception:
                raise RuntimeError("PyYAML not installed. Please use .json or install pyyaml.")
    return json.loads(content)


def main():
    parser = argparse.ArgumentParser(description="Generate 3:4 Vertical High-Definition WeChat Photo Cards.")
    parser.add_argument("--config", "-c", type=str, help="Path to deck spec JSON or YAML file for batch generation")
    parser.add_argument("--output-dir", "-d", type=str, default=".", help="Output directory for batch generation")
    parser.add_argument("--type", "-t", type=str, choices=list(CARD_RENDERERS.keys()), default="cover", help="Card layout type")
    parser.add_argument("--theme", type=str, choices=list(THEMES.keys()), default="navy_gold", help="Color theme name")
    parser.add_argument("--title", type=str, help="Main title")
    parser.add_argument("--hook", type=str, help="Explosive hook title for cover")
    parser.add_argument("--hook-accent", type=str, default="", help="Second line accent hook text")
    parser.add_argument("--subtitle", type=str, default="", help="Card subtitle")
    parser.add_argument("--category", type=str, default="AI ARCHITECTURE", help="Category badge text")
    parser.add_argument("--author", type=str, default=None, help="Author/brand text (optional)")
    parser.add_argument("--page-idx", type=str, default="01 / 05", help="Page index (e.g. 01 / 05)")
    parser.add_argument("--output", "-o", type=str, default="photo_card.png", help="Output PNG file path for single card")
    parser.add_argument("--resample-width", type=int, default=1200, help="Output PNG pixel width (default 1200, 3:4 ratio gives 1200x1600)")

    args = parser.parse_args()

    # Mode 1: Batch Generation from Config
    if args.config:
        cfg_file = Path(args.config)
        if not cfg_file.exists():
            logger.error(f"Config file not found: {args.config}")
            sys.exit(1)

        deck_spec = load_config_file(cfg_file)
        out_dir = Path(args.output_dir)
        generated = generate_photo_deck(deck_spec, out_dir)
        logger.success(f"Successfully generated {len(generated)} cards in {out_dir}")
        for p in generated:
            print(f" - {p}")
        return

    # Mode 2: Single Card Generation
    card_data = {
        "title": args.title or "核心观点拆解",
        "hook": args.hook or args.title or "4-8字爆破核心短语",
        "hook_accent": args.hook_accent,
        "subtitle": args.subtitle or "移动端精炼深度拆解与行动洞察",
        "category": args.category,
        "author": args.author,
        "page_idx": args.page_idx,
    }

    svg_content = generate_photo_card_svg(args.type, card_data, theme=args.theme)
    out_path = Path(args.output)
    png_path = render_svg_to_png(svg_content, out_path, resample_width=args.resample_width)
    logger.success(f"Generated single {args.type} card: {png_path}")


if __name__ == "__main__":
    main()
