#!/usr/bin/env python3
"""
CLI Tool for generating clean Swiss Typographic Article Covers.

Usage:
  python tools/generate_cover.py --title "文章标题" --subtitle "副标题" --category "AI" --theme navy_gold --output cover.png
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.blogger.core.cover_generator import generate_swiss_cover, THEMES
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Generate Swiss editorial covers for articles.")
    parser.add_argument("--title", type=str, help="Article main title")
    parser.add_argument("--subtitle", type=str, default="", help="Article subtitle or summary phrase")
    parser.add_argument("--category", type=str, default="EDITORIAL", help="Category badge text (e.g. AI, AGENT, DEVSECOPS, PARENTING)")
    parser.add_argument("--theme", type=str, default="navy_gold", choices=list(THEMES.keys()), help="Color theme name")
    parser.add_argument("--ratio", type=str, default="16:9", choices=["16:9", "1:1"], help="Image aspect ratio")
    parser.add_argument("--author", type=str, default=None, help="Optional author or brand marker text")
    parser.add_argument("--output", "-o", type=str, default="cover.png", help="Output PNG file path")

    args = parser.parse_args()

    if not args.title:
        parser.print_help()
        sys.exit(1)

    out_path = generate_swiss_cover(
        title=args.title,
        subtitle=args.subtitle,
        category=args.category,
        theme=args.theme,
        ratio=args.ratio,
        author=args.author,
        output_path=args.output
    )

    logger.info(f"Successfully generated cover at {out_path}")


if __name__ == "__main__":
    main()
