"""
Swiss Typographic & Editorial Cover Generator for Blogger Agent.

Generates high-resolution (1080p/2K) article cover images using clean
Swiss graphic design principles: bold typography, structured grids,
high contrast color schemes, and 0% AI diffusion artifacts.
"""

import math
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from loguru import logger

# --- Color Themes ---
THEMES: Dict[str, Dict[str, str]] = {
    "swiss_red": {
        "bg": "#F8F9FA",
        "card_bg": "#FFFFFF",
        "primary": "#E63946",       # Swiss Red
        "title": "#111827",         # Deep Slate
        "subtitle": "#4B5563",      # Muted Slate
        "border": "#E5E7EB",
        "badge_bg": "#E63946",
        "badge_fg": "#FFFFFF",
        "accent": "#E63946",
        "meta": "#9CA3AF"
    },
    "navy_gold": {
        "bg": "#0F172A",            # Deep Obsidian Navy
        "card_bg": "#1E293B",
        "primary": "#F59E0B",       # Amber Gold
        "title": "#F8FAFC",         # Crisp White
        "subtitle": "#CBD5E1",      # Light Slate
        "border": "#334155",
        "badge_bg": "#F59E0B",
        "badge_fg": "#0F172A",
        "accent": "#F59E0B",
        "meta": "#64748B"
    },
    "emerald": {
        "bg": "#022C22",            # Deep Forest Emerald
        "card_bg": "#064E3B",
        "primary": "#10B981",       # Mint Emerald
        "title": "#F0FDF4",         # Cream Ivory
        "subtitle": "#A7F3D0",      # Soft Sage
        "border": "#047857",
        "badge_bg": "#10B981",
        "badge_fg": "#022C22",
        "accent": "#34D399",
        "meta": "#059669"
    },
    "slate_lime": {
        "bg": "#18181B",            # Matte Dark Zinc
        "card_bg": "#27272A",
        "primary": "#84CC16",       # Electric Lime
        "title": "#FAFAFA",         # Bright White
        "subtitle": "#A1A1AA",      # Zinc Gray
        "border": "#3F3F46",
        "badge_bg": "#84CC16",
        "badge_fg": "#18181B",
        "accent": "#06B6D4",       # Cyan Accent
        "meta": "#71717A"
    }
}


def _get_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    """Load a truetype font with fallback options on macOS."""
    candidate_paths = []
    if font_path and os.path.exists(font_path):
        candidate_paths.append(font_path)

    # macOS font fallbacks
    candidate_paths.extend([
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial Unicode.ttf"
    ])

    for path in candidate_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception as e:
                logger.debug(f"Failed loading font {path}: {e}")
                continue

    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wrap Chinese/English text cleanly to fit within max_width without orphans."""
    lines = []
    current_line = ""

    for char in text:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char

    if current_line:
        lines.append(current_line)

    # Avoid orphan single-character last lines if possible
    if len(lines) > 1 and len(lines[-1]) == 1:
        prev = lines[-2]
        if len(prev) > 3:
            lines[-2] = prev[:-1]
            lines[-1] = prev[-1] + lines[-1]

    return lines


def generate_swiss_cover(
    title: str,
    subtitle: str = "",
    category: str = "EDITORIAL",
    theme: str = "swiss_red",
    ratio: str = "16:9",
    author: Optional[str] = None,
    date_str: Optional[str] = None,
    output_path: str = "cover.png"
) -> Path:
    """
    Generate a high-resolution Swiss typographic editorial article cover.

    Args:
        title: Main article title (Chinese/English).
        subtitle: Optional subtitle or short summary phrase.
        category: Category badge text (e.g. "AI", "AGENT", "SECURITY", "FINANCE").
        theme: Color theme ("swiss_red", "navy_gold", "emerald", "slate_lime").
        ratio: "16:9" (1920x1080) or "1:1" (1500x1500).
        author: Optional author or publication identifier.
        date_str: Optional date string (defaults to current date).
        output_path: Target output path.

    Returns:
        Path: Path object pointing to the output PNG file.
    """
    # 1. Canvas Dimensions
    if ratio == "1:1":
        width, height = 1500, 1500
    else:  # default 16:9
        width, height = 1920, 1080

    # 2. Select Theme Colors
    palette = THEMES.get(theme, THEMES["swiss_red"])

    # Create Image Canvas
    img = Image.new("RGBA", (width, height), palette["bg"])
    draw = ImageDraw.Draw(img)

    # Margins and Grid Calculations
    margin_x = int(width * 0.065)    # ~125px for 1920
    margin_y = int(height * 0.08)    # ~86px for 1080
    content_w = width - 2 * margin_x

    # 3. Outer Frame / Card Background
    card_box = [margin_x, margin_y, width - margin_x, height - margin_y]
    draw.rectangle(card_box, fill=palette["card_bg"], outline=palette["border"], width=2)

    # Inner Padding within Card Box
    inner_pad_x = int(content_w * 0.05)
    inner_pad_y = int((height - 2 * margin_y) * 0.07)

    curr_x = margin_x + inner_pad_x
    curr_y = margin_y + inner_pad_y
    max_text_w = content_w - 2 * inner_pad_x

    # 4. Header Bar: Category Badge & Brand Identifier
    badge_font = _get_font(None, 24)
    cat_text = f"  {category.upper()}  "
    cat_bbox = draw.textbbox((0, 0), cat_text, font=badge_font)
    cat_w = cat_bbox[2] - cat_bbox[0]
    cat_h = cat_bbox[3] - cat_bbox[1] + 16

    # Draw Category Badge
    badge_rect = [curr_x, curr_y, curr_x + cat_w, curr_y + cat_h]
    draw.rectangle(badge_rect, fill=palette["badge_bg"])
    draw.text((curr_x, curr_y + 8), cat_text, font=badge_font, fill=palette["badge_fg"])

    # Draw Top Right Brand Marker if specified
    if author:
        brand_font = _get_font(None, 22)
        brand_text = author.upper()
        brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
        brand_w = brand_bbox[2] - brand_bbox[0]
        draw.text((margin_x + content_w - inner_pad_x - brand_w, curr_y + 8), brand_text, font=brand_font, fill=palette["meta"])

    # Header Divider Line
    divider_y = curr_y + cat_h + int(inner_pad_y * 0.6)
    draw.line([(curr_x, divider_y), (margin_x + content_w - inner_pad_x, divider_y)], fill=palette["border"], width=1)

    # 5. Main Title Section
    title_start_y = divider_y + int(inner_pad_y * 0.8)

    # Dynamic Font Size Calculation based on Title Length
    title_len = len(title)
    if title_len <= 12:
        title_font_size = int(height * 0.078)   # ~84px in 1080p
    elif title_len <= 20:
        title_font_size = int(height * 0.068)   # ~73px
    elif title_len <= 32:
        title_font_size = int(height * 0.058)   # ~62px
    else:
        title_font_size = int(height * 0.050)   # ~54px

    title_font = _get_font(None, title_font_size)
    lines = _wrap_text(title, title_font, max_text_w, draw)

    line_height = int(title_font_size * 1.35)
    title_y = title_start_y

    for line in lines:
        draw.text((curr_x, title_y), line, font=title_font, fill=palette["title"])
        title_y += line_height

    # 6. Geometric Graphic Accent (Swiss Cross & Accent Pillar)
    accent_y = title_y + int(inner_pad_y * 0.4)
    pillar_w = int(max_text_w * 0.15)
    draw.rectangle([curr_x, accent_y, curr_x + pillar_w, accent_y + 6], fill=palette["primary"])

    # 7. Subtitle Section
    if subtitle:
        sub_y = accent_y + 24
        sub_font_size = int(title_font_size * 0.42)
        sub_font_size = max(24, min(36, sub_font_size))
        sub_font = _get_font(None, sub_font_size)

        sub_lines = _wrap_text(subtitle, sub_font, max_text_w, draw)
        sub_line_height = int(sub_font_size * 1.4)

        for line in sub_lines[:2]:   # Limit to 2 lines max
            draw.text((curr_x, sub_y), line, font=sub_font, fill=palette["subtitle"])
            sub_y += sub_line_height

    # 8. Footer Section (Date & Metadata Bar)
    footer_y = height - margin_y - inner_pad_y - 30
    draw.line([(curr_x, footer_y - 20), (margin_x + content_w - inner_pad_x, footer_y - 20)], fill=palette["border"], width=1)

    if not date_str:
        date_str = datetime.now().strftime("%Y.%m.%d")

    meta_font = _get_font(None, 20)
    meta_text = f"DATE: {date_str}" if not author else f"DATE: {date_str}   //   {author.upper()}"
    draw.text((curr_x, footer_y), meta_text, font=meta_font, fill=palette["meta"])

    # Right-aligned Decorative Grid Marker
    grid_x = margin_x + content_w - inner_pad_x - 60
    for i in range(3):
        for j in range(3):
            cx = grid_x + i * 16
            cy = footer_y + j * 8
            draw.rectangle([cx, cy, cx + 4, cy + 4], fill=palette["primary"])

    # Save to disk
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_file, "PNG")
    logger.success(f"Swiss editorial cover generated: {out_file} ({width}x{height}, theme={theme})")

    return out_file
