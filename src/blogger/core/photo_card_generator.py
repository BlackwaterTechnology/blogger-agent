"""
WeChat Photo Message (3:4 Vertical Card) Generator for Blogger Agent.

Generates high-resolution (1200x1600 px, 3:4 aspect ratio) vertical cognitive cards
optimized for mobile feeds (WeChat 看一看 / 小绿书瀑布流 / 订阅号推荐流).
Provides 5 structured layout templates with clean Swiss/modern typography and zero AI blur.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

# --- Color Themes ---
THEMES: Dict[str, Dict[str, str]] = {
    "navy_gold": {
        "bg": "#0F172A",            # Obsidian Navy
        "card_bg": "#1E293B",       # Slate Navy
        "card_sub_bg": "#0B1329",   # Deep Sub Card
        "primary": "#F59E0B",       # Amber Gold
        "accent": "#38BDF8",        # Cyan Blue
        "title": "#F8FAFC",         # Crisp White
        "text": "#E2E8F0",          # Light Slate
        "muted": "#94A3B8",         # Slate Gray
        "border": "#334155",        # Border Slate
        "badge_bg": "#F59E0B",
        "badge_fg": "#0F172A",
        "tag_bg": "rgba(245, 158, 11, 0.15)",
        "tag_fg": "#F59E0B",
        "bad_color": "#EF4444",     # Red
        "good_color": "#10B981"     # Emerald Green
    },
    "swiss_red": {
        "bg": "#F8F9FA",            # Off White
        "card_bg": "#FFFFFF",       # Pure White
        "card_sub_bg": "#F1F5F9",   # Cool Gray
        "primary": "#E63946",       # Swiss Red
        "accent": "#1D3557",        # Deep Indigo
        "title": "#111827",         # Deep Slate
        "text": "#374151",          # Charcoal Text
        "muted": "#6B7280",         # Muted Gray
        "border": "#E2E8F0",        # Crisp Border
        "badge_bg": "#E63946",
        "badge_fg": "#FFFFFF",
        "tag_bg": "rgba(230, 57, 70, 0.1)",
        "tag_fg": "#E63946",
        "bad_color": "#E63946",
        "good_color": "#059669"
    },
    "emerald": {
        "bg": "#022C22",            # Deep Forest
        "card_bg": "#064E3B",       # Emerald Green
        "card_sub_bg": "#02221A",   # Dark Teal
        "primary": "#10B981",       # Mint Green
        "accent": "#34D399",        # Soft Mint
        "title": "#F0FDF4",         # Ivory Green
        "text": "#D1FAE5",          # Light Mint
        "muted": "#6EE7B7",         # Sage Gray
        "border": "#047857",        # Green Border
        "badge_bg": "#10B981",
        "badge_fg": "#022C22",
        "tag_bg": "rgba(16, 185, 129, 0.15)",
        "tag_fg": "#34D399",
        "bad_color": "#F87171",
        "good_color": "#10B981"
    },
    "slate_lime": {
        "bg": "#18181B",            # Dark Zinc
        "card_bg": "#27272A",       # Matte Charcoal
        "card_sub_bg": "#121214",   # Pitch Sub
        "primary": "#84CC16",       # Electric Lime
        "accent": "#06B6D4",        # Cyan
        "title": "#FAFAFA",         # Bright White
        "text": "#E4E4E7",          # Off White
        "muted": "#A1A1AA",         # Zinc Gray
        "border": "#3F3F46",        # Charcoal Border
        "badge_bg": "#84CC16",
        "badge_fg": "#18181B",
        "tag_bg": "rgba(132, 204, 22, 0.15)",
        "tag_fg": "#A3E635",
        "bad_color": "#F43F5E",
        "good_color": "#84CC16"
    }
}


def _escape_xml(text: Any) -> str:
    """Escape XML special characters."""
    if text is None:
        return ""
    s = str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _render_header_svg(
    category: str,
    page_idx: str,
    author: Optional[str],
    palette: Dict[str, str],
    margin_x: int = 70,
    curr_y: int = 80
) -> str:
    """Render top header bar with category badge, page index, and optional author brand."""
    cat_text = _escape_xml(category.upper())
    idx_text = _escape_xml(page_idx)

    badge_w = max(140, len(cat_text) * 24 + 48)

    author_svg = ""
    if author and str(author).strip().upper() not in ["", "AGENT", "@AGENT"]:
        author_text = _escape_xml(str(author).strip().upper())
        author_svg = f"""
        <!-- Author / Brand -->
        <text x="{margin_x + badge_w + 24}" y="{curr_y + 32}" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="600" fill="{palette['muted']}">{author_text}</text>
        """

    return f"""
    <!-- Top Header Bar -->
    <g id="header">
        <!-- Category Badge -->
        <rect x="{margin_x}" y="{curr_y}" width="{badge_w}" height="48" rx="10" fill="{palette['badge_bg']}" />
        <text x="{margin_x + badge_w / 2}" y="{curr_y + 32}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="bold" fill="{palette['badge_fg']}">{cat_text}</text>
        {author_svg}
        <!-- Page Indicator -->
        <rect x="{1200 - margin_x - 130}" y="{curr_y}" width="130" height="48" rx="10" fill="{palette['card_sub_bg']}" stroke="{palette['border']}" stroke-width="1.5" />
        <text x="{1200 - margin_x - 65}" y="{curr_y + 32}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="bold" fill="{palette['primary']}">{idx_text}</text>
        
        <!-- Divider -->
        <line x1="{margin_x}" y1="{curr_y + 70}" x2="{1200 - margin_x}" y2="{curr_y + 70}" stroke="{palette['border']}" stroke-width="1.5" />
    </g>
    """


def _render_footer_svg(
    palette: Dict[str, str],
    footer_text: str = "SWIPE TO READ ➔",
    footer_left: Optional[str] = None,
    margin_x: int = 70,
    y: int = 1510
) -> str:
    """Render footer indicator bar without tool watermarks."""
    left_svg = ""
    if footer_left:
        left_svg = f"""<text x="{margin_x}" y="{y + 18}" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="500" fill="{palette['muted']}">{_escape_xml(footer_left)}</text>"""

    return f"""
    <!-- Footer -->
    <g id="footer">
        <line x1="{margin_x}" y1="{y - 20}" x2="{1200 - margin_x}" y2="{y - 20}" stroke="{palette['border']}" stroke-width="1.5" />
        {left_svg}
        <text x="{1200 - margin_x}" y="{y + 18}" text-anchor="end" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="26" font-weight="bold" fill="{palette['primary']}">{_escape_xml(footer_text)}</text>
    </g>
    """


# =========================================================================
# Layout Template 1: Cover (Hook & Micro-Infographic)
# =========================================================================
def render_cover_card(data: Dict[str, Any], palette: Dict[str, str]) -> str:
    """
    Template 1: Magazine Hook Cover
    Required keys: title, hook, subtitle
    Optional keys: category, page_idx, author, stats (list of dict: badge, val, note, type)
    """
    title = data.get("title", "核心爆破观点")
    hook = data.get("hook", title)
    subtitle = data.get("subtitle", "移动端精炼深度拆解与行动洞察")
    category = data.get("category", "AI ARCHITECTURE")
    page_idx = data.get("page_idx", "01 / 05")
    author = data.get("author", None)
    footer_left = data.get("footer_left", None)
    stats = data.get("stats", [])

    margin_x = 70
    content_w = 1200 - 2 * margin_x

    header_svg = _render_header_svg(category, page_idx, author, palette, margin_x=margin_x, curr_y=75)
    footer_svg = _render_footer_svg(palette, footer_text="滑动查看核心拆解 ➔", footer_left=footer_left, margin_x=margin_x, y=1515)

    hook_escaped = _escape_xml(hook)
    subtitle_escaped = _escape_xml(subtitle)

    stats_svg = ""
    if not stats:
        stats = [
            {"badge": "传统认知 ❌", "val": "静态对冲稳赚不赔", "note": "忽略资金费率翻转与穿仓摩擦", "type": "bad"},
            {"badge": "实战现实 ⚠️", "val": "实际年化回撤超 60%", "note": "系统性单边行情引发多空踩踏", "type": "warning"},
            {"badge": "终极解法 ✅", "val": "动态 Delta 中性引擎", "note": "实时动态调仓与多交易所风险对冲", "type": "good"}
        ]

    card_y = 660
    card_h = 220
    for i, s in enumerate(stats[:3]):
        box_y = card_y + i * (card_h + 24)
        is_good = s.get("type") == "good"
        is_bad = s.get("type") == "bad"
        box_stroke = palette["good_color"] if is_good else (palette["bad_color"] if is_bad else palette["primary"])
        badge_fill = box_stroke
        badge_str = s.get('badge', '')
        badge_w = max(150, len(badge_str) * 24 + 36)

        stats_svg += f"""
        <g transform="translate({margin_x}, {box_y})">
            <rect width="{content_w}" height="{card_h}" rx="18" fill="{palette['card_bg']}" stroke="{box_stroke}" stroke-width="2" />
            
            <!-- Badge -->
            <rect x="36" y="28" width="{badge_w}" height="42" rx="8" fill="{badge_fill}" />
            <text x="50" y="56" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="bold" fill="#FFFFFF">{_escape_xml(badge_str)}</text>
            
            <!-- Value/Title -->
            <text x="36" y="120" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="36" font-weight="bold" fill="{palette['title']}">{_escape_xml(s.get('val', ''))}</text>
            
            <!-- Note -->
            <text x="36" y="172" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="500" fill="{palette['muted']}">{_escape_xml(s.get('note', ''))}</text>
            
            <!-- Right Accent Icon -->
            <circle cx="{content_w - 50}" cy="{card_h / 2}" r="22" fill="{palette['card_sub_bg']}" stroke="{box_stroke}" stroke-width="2" />
            <text x="{content_w - 50}" y="{card_h / 2 + 8}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="22" font-weight="bold" fill="{box_stroke}">➔</text>
        </g>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1600" width="1200" height="1600">
    <defs>
        <linearGradient id="bg_grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="{palette['bg']}" />
            <stop offset="100%" stop-color="{palette['card_sub_bg']}" />
        </linearGradient>
    </defs>

    <!-- Canvas Background -->
    <rect width="1200" height="1600" fill="url(#bg_grad)" />

    <!-- Subtle Background Grid Accent -->
    <g opacity="0.12">
        <line x1="{margin_x}" y1="0" x2="{margin_x}" y2="1600" stroke="{palette['border']}" stroke-width="1" stroke-dasharray="8,8" />
        <line x1="{1200 - margin_x}" y1="0" x2="{1200 - margin_x}" y2="1600" stroke="{palette['border']}" stroke-width="1" stroke-dasharray="8,8" />
    </g>

    {header_svg}

    <!-- Main Hero Hook Section -->
    <g id="hero_hook" transform="translate({margin_x}, 220)">
        <!-- Hook Super Title (Accent Pillar) -->
        <rect x="0" y="0" width="12" height="160" rx="6" fill="{palette['primary']}" />
        
        <!-- Big Bold Explosive Title -->
        <text x="32" y="70" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="68" font-weight="900" fill="{palette['title']}" letter-spacing="-1">{hook_escaped}</text>
        <text x="32" y="145" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="68" font-weight="900" fill="{palette['primary']}" letter-spacing="-1">{_escape_xml(data.get('hook_accent', ''))}</text>
        
        <!-- Subtitle -->
        <text x="32" y="225" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="32" font-weight="500" fill="{palette['text']}">{subtitle_escaped}</text>
    </g>

    <!-- Micro Infographics / Core Cards -->
    <g id="stats_container">
        {stats_svg}
    </g>

    {footer_svg}
</svg>"""
    return svg


# =========================================================================
# Layout Template 2: VS Comparison (2-Column Side-by-Side Matrix)
# =========================================================================
def render_vs_comparison_card(data: Dict[str, Any], palette: Dict[str, str]) -> str:
    """
    Template 2: VS Dual Column Matrix
    Required keys: title, left_col (dict: title, badge, items), right_col (dict: title, badge, items)
    Optional keys: category, page_idx, author, bottom_takeaway
    """
    title = data.get("title", "认知重构：旧模式 vs 新范式")
    subtitle = data.get("subtitle", "为什么传统方法在复杂场景中必然失效？")
    category = data.get("category", "PARADIGM SHIFT")
    page_idx = data.get("page_idx", "02 / 05")
    author = data.get("author", None)
    footer_left = data.get("footer_left", None)
    left_col = data.get("left_col", {})
    right_col = data.get("right_col", {})
    takeaway = data.get("bottom_takeaway", "底层逻辑改变：不再靠人工堆叠，而是由系统自适应闭环驱动。")

    margin_x = 70
    col_w = 510
    left_x = margin_x
    right_x = margin_x + col_w + 40
    card_y = 350
    card_h = 920

    header_svg = _render_header_svg(category, page_idx, author, palette, margin_x=margin_x, curr_y=75)
    footer_svg = _render_footer_svg(palette, footer_text="滑动查看架构拆解 ➔", footer_left=footer_left, margin_x=margin_x, y=1515)

    # Render Left Column Items (Bad/Old)
    left_items_svg = ""
    left_items = left_col.get("items", [
        "单点依赖人工经验与直觉",
        "状态黑盒，异常无法快速归因",
        "静态规则硬编码，边际维护成本极高",
        "遇到极端扰动直接崩溃，无自愈能力"
    ])
    for i, item in enumerate(left_items):
        item_y = 170 + i * 165
        left_items_svg += f"""
        <g transform="translate(24, {item_y})">
            <rect width="{col_w - 48}" height="135" rx="14" fill="{palette['card_sub_bg']}" stroke="{palette['border']}" stroke-width="1.5" />
            <circle cx="34" cy="40" r="18" fill="{palette['bad_color']}22" stroke="{palette['bad_color']}" stroke-width="2" />
            <text x="34" y="48" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="18" font-weight="bold" fill="{palette['bad_color']}">✕</text>
            
            <text x="68" y="48" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="bold" fill="{palette['title']}">{_escape_xml(item.get('title', item) if isinstance(item, dict) else item)}</text>
            <text x="28" y="98" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="500" fill="{palette['muted']}">{_escape_xml(item.get('desc', '') if isinstance(item, dict) else '')}</text>
        </g>
        """

    # Render Right Column Items (Good/New)
    right_items_svg = ""
    right_items = right_col.get("items", [
        "第一性原理驱动系统化建模",
        "全链路 Trace 可观测与状态审计",
        "动态闭环编排，自适应环境变化",
        "具备反脆弱韧性，故障自动降级"
    ])
    for i, item in enumerate(right_items):
        item_y = 170 + i * 165
        right_items_svg += f"""
        <g transform="translate(24, {item_y})">
            <rect width="{col_w - 48}" height="135" rx="14" fill="{palette['card_sub_bg']}" stroke="{palette['good_color']}55" stroke-width="1.5" />
            <circle cx="34" cy="40" r="18" fill="{palette['good_color']}22" stroke="{palette['good_color']}" stroke-width="2" />
            <text x="34" y="48" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="18" font-weight="bold" fill="{palette['good_color']}">✓</text>
            
            <text x="68" y="48" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="bold" fill="{palette['title']}">{_escape_xml(item.get('title', item) if isinstance(item, dict) else item)}</text>
            <text x="28" y="98" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="500" fill="{palette['muted']}">{_escape_xml(item.get('desc', '') if isinstance(item, dict) else '')}</text>
        </g>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1600" width="1200" height="1600">
    <rect width="1200" height="1600" fill="{palette['bg']}" />
    {header_svg}

    <!-- Section Title -->
    <g transform="translate({margin_x}, 200)">
        <text x="0" y="46" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="44" font-weight="900" fill="{palette['title']}">{_escape_xml(title)}</text>
        <text x="0" y="96" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="500" fill="{palette['muted']}">{_escape_xml(subtitle)}</text>
    </g>

    <!-- Left Column (Old) -->
    <g transform="translate({left_x}, {card_y})">
        <rect width="{col_w}" height="{card_h}" rx="20" fill="{palette['card_bg']}" stroke="{palette['border']}" stroke-width="2" />
        
        <!-- Header -->
        <rect x="0" y="0" width="{col_w}" height="80" rx="20" fill="{palette['bad_color']}15" />
        <rect x="24" y="20" width="130" height="40" rx="8" fill="{palette['bad_color']}" />
        <text x="89" y="48" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="bold" fill="#FFFFFF">{_escape_xml(left_col.get('badge', '旧模式 ✕'))}</text>
        <text x="170" y="50" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="30" font-weight="bold" fill="{palette['title']}">{_escape_xml(left_col.get('title', '脆弱型架构'))}</text>
        
        {left_items_svg}
    </g>

    <!-- Right Column (New) -->
    <g transform="translate({right_x}, {card_y})">
        <rect width="{col_w}" height="{card_h}" rx="20" fill="{palette['card_bg']}" stroke="{palette['good_color']}" stroke-width="2" />
        
        <!-- Header -->
        <rect x="0" y="0" width="{col_w}" height="80" rx="20" fill="{palette['good_color']}15" />
        <rect x="24" y="20" width="130" height="40" rx="8" fill="{palette['good_color']}" />
        <text x="89" y="48" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="bold" fill="#FFFFFF">{_escape_xml(right_col.get('badge', '新范式 ✓'))}</text>
        <text x="170" y="50" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="30" font-weight="bold" fill="{palette['title']}">{_escape_xml(right_col.get('title', '反脆弱系统'))}</text>
        
        {right_items_svg}
    </g>

    <!-- Bottom Takeaway Bar -->
    <g transform="translate({margin_x}, 1320)">
        <rect width="{1200 - 2 * margin_x}" height="130" rx="16" fill="{palette['card_bg']}" stroke="{palette['primary']}" stroke-width="2" />
        <rect x="30" y="45" width="8" height="40" rx="4" fill="{palette['primary']}" />
        <text x="56" y="56" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="bold" fill="{palette['primary']}">CORE TAKEAWAY / 核心结论</text>
        <text x="56" y="100" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="bold" fill="{palette['title']}">{_escape_xml(takeaway)}</text>
    </g>

    {footer_svg}
</svg>"""
    return svg


# =========================================================================
# Layout Template 3: Bullet Points / Modular Point Cards
# =========================================================================
def render_bullet_points_card(data: Dict[str, Any], palette: Dict[str, str]) -> str:
    """
    Template 3: Modular Point Cards
    Required keys: title, points (list of dict: badge, title, desc, tags)
    Optional keys: category, page_idx, author, subtitle
    """
    title = data.get("title", "系统落地的三大硬核支柱")
    subtitle = data.get("subtitle", "从顶层设计到底层执行的完整落地框架")
    category = data.get("category", "KEY PILLARS")
    page_idx = data.get("page_idx", "03 / 05")
    author = data.get("author", None)
    footer_left = data.get("footer_left", None)
    points = data.get("points", [])

    margin_x = 70
    content_w = 1200 - 2 * margin_x

    header_svg = _render_header_svg(category, page_idx, author, palette, margin_x=margin_x, curr_y=75)
    footer_svg = _render_footer_svg(palette, footer_text="滑动查看实操链路 ➔", footer_left=footer_left, margin_x=margin_x, y=1515)

    if not points:
        points = [
            {
                "idx": "01",
                "badge": "CONTEXT FRAMING",
                "title": "高维问题定义与上下文冻结",
                "desc": "在进入执行前完成问题边界界定，把不确定性收敛在可控沙盒内。",
                "tags": ["第一性原理", "范围约束", "输入审计"]
            },
            {
                "idx": "02",
                "badge": "DYNAMIC ORCHESTRATION",
                "title": "动态智能体编排与状态流转",
                "desc": "打破单一 Prompt 线性黑盒，将复杂任务拆解为可独立验证的状态机。",
                "tags": ["状态机", "幂等执行", "异常回滚"]
            },
            {
                "idx": "03",
                "badge": "VERIFICATION GATE",
                "title": "基于 Checklist 的机器终审背书",
                "desc": "建立 100% 形式化品控防线，杜绝人工主观偏见与幻觉泄漏。",
                "tags": ["自动化测试", "品控卡", "零信任"]
            }
        ]

    cards_svg = ""
    start_y = 330
    card_h = 340
    card_gap = 35

    for i, p in enumerate(points[:3]):
        box_y = start_y + i * (card_h + card_gap)
        tags_svg = ""
        tags = p.get("tags", [])
        tag_x = 40
        for t in tags[:4]:
            t_w = len(t) * 26 + 32
            tags_svg += f"""
            <rect x="{tag_x}" y="252" width="{t_w}" height="46" rx="8" fill="{palette['tag_bg']}" stroke="{palette['border']}" stroke-width="1" />
            <text x="{tag_x + t_w / 2}" y="283" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="600" fill="{palette['tag_fg']}">{_escape_xml(t)}</text>
            """
            tag_x += t_w + 16

        # Point Description (supports 1 or 2 lines)
        desc_text = p.get('desc', '')
        if "\n" in desc_text:
            lines = desc_text.split("\n", 1)
            desc_svg = f"""
            <text x="40" y="182" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="500" fill="{palette['text']}">{_escape_xml(lines[0])}</text>
            <text x="40" y="222" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="500" fill="{palette['text']}">{_escape_xml(lines[1])}</text>
            """
        else:
            desc_svg = f"""
            <text x="40" y="195" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="500" fill="{palette['text']}">{_escape_xml(desc_text)}</text>
            """

        cards_svg += f"""
        <g transform="translate({margin_x}, {box_y})">
            <rect width="{content_w}" height="{card_h}" rx="22" fill="{palette['card_bg']}" stroke="{palette['border']}" stroke-width="2" />
            
            <!-- Index Pill Badge -->
            <rect x="40" y="34" width="70" height="42" rx="8" fill="{palette['primary']}" />
            <text x="75" y="64" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="900" fill="{palette['badge_fg']}">{_escape_xml(p.get('idx', f'0{i+1}'))}</text>
            
            <!-- Category Tag -->
            <text x="130" y="64" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="bold" fill="{palette['muted']}" letter-spacing="1">{_escape_xml(p.get('badge', 'PILLAR'))}</text>
            
            <!-- Point Title -->
            <text x="40" y="136" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="36" font-weight="bold" fill="{palette['title']}">{_escape_xml(p.get('title', ''))}</text>
            
            <!-- Point Description -->
            {desc_svg}
            
            <!-- Tags Row -->
            {tags_svg}
        </g>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1600" width="1200" height="1600">
    <rect width="1200" height="1600" fill="{palette['bg']}" />
    {header_svg}

    <!-- Header Title -->
    <g transform="translate({margin_x}, 195)">
        <text x="0" y="46" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="44" font-weight="900" fill="{palette['title']}">{_escape_xml(title)}</text>
        <text x="0" y="96" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="500" fill="{palette['muted']}">{_escape_xml(subtitle)}</text>
    </g>

    <!-- Point Cards Container -->
    <g id="cards_container">
        {cards_svg}
    </g>

    {footer_svg}
</svg>"""
    return svg


# =========================================================================
# Layout Template 4: Pipeline Steps (Sequential Execution Stages)
# =========================================================================
def render_pipeline_steps_card(data: Dict[str, Any], palette: Dict[str, str]) -> str:
    """
    Template 4: Step-by-Step Pipeline Flow
    Required keys: title, steps (list of dict: step, title, desc, deliverable)
    Optional keys: category, page_idx, author, rule_note
    """
    title = data.get("title", "四步闭环执行链路")
    subtitle = data.get("subtitle", "从输入到交付的确定性工程流水线")
    category = data.get("category", "WORKFLOW PIPELINE")
    page_idx = data.get("page_idx", "04 / 05")
    author = data.get("author", None)
    footer_left = data.get("footer_left", None)
    steps = data.get("steps", [])
    rule_note = data.get("rule_note", "工程硬原则：上游阶段产物未完成 Checklist 验收，绝对禁止流转至下一阶段。")

    margin_x = 70
    content_w = 1200 - 2 * margin_x

    header_svg = _render_header_svg(category, page_idx, author, palette, margin_x=margin_x, curr_y=75)
    footer_svg = _render_footer_svg(palette, footer_text="滑动查看行动总结 ➔", footer_left=footer_left, margin_x=margin_x, y=1515)

    if not steps:
        steps = [
            {"step": "STEP 01", "title": "问题建模与假设确立", "desc": "明确反直觉核心主张与社交货币实体", "deliverable": "交付物：1 份高维问题定义单"},
            {"step": "STEP 02", "title": "视觉建模与高密卡片", "desc": "将核心逻辑转化为 3:4 移动端高密图表", "deliverable": "交付物：3~9 张 1200x1600 高清图"},
            {"step": "STEP 03", "title": "短文精炼与无缝连接", "desc": "撰写 300~800 字伴随文案，清除所有 AI 腔", "deliverable": "交付物：规范 Markdown 草案"},
            {"step": "STEP 04", "title": "Subagent 终审查验", "desc": "100 分制打分卡拦截排版与逻辑缺陷", "deliverable": "交付物：就绪可发布 Payload"}
        ]

    steps_svg = ""
    start_y = 320
    step_h = 220
    step_gap = 35

    for i, st in enumerate(steps[:4]):
        box_y = start_y + i * (step_h + step_gap)
        arrow_svg = ""
        if i < len(steps[:4]) - 1:
            arrow_svg = f"""
            <!-- Down Arrow -->
            <g transform="translate({margin_x + content_w / 2}, {box_y + step_h + 8})">
                <circle cx="0" cy="10" r="16" fill="{palette['card_sub_bg']}" stroke="{palette['primary']}" stroke-width="2" />
                <text x="0" y="17" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="20" font-weight="bold" fill="{palette['primary']}">↓</text>
            </g>
            """

        steps_svg += f"""
        <g transform="translate({margin_x}, {box_y})">
            <rect width="{content_w}" height="{step_h}" rx="18" fill="{palette['card_bg']}" stroke="{palette['border']}" stroke-width="2" />
            
            <!-- Step Badge -->
            <rect x="36" y="28" width="130" height="42" rx="8" fill="{palette['primary']}" />
            <text x="101" y="57" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="900" fill="{palette['badge_fg']}">{_escape_xml(st.get('step', f'STEP 0{i+1}'))}</text>
            
            <!-- Title -->
            <text x="186" y="58" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="bold" fill="{palette['title']}">{_escape_xml(st.get('title', ''))}</text>
            
            <!-- Description -->
            <text x="36" y="118" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="500" fill="{palette['text']}">{_escape_xml(st.get('desc', ''))}</text>
            
            <!-- Deliverable Pill -->
            <rect x="36" y="148" width="{content_w - 72}" height="46" rx="8" fill="{palette['card_sub_bg']}" stroke="{palette['border']}" stroke-width="1" />
            <text x="56" y="180" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="26" font-weight="600" fill="{palette['accent']}">{_escape_xml(st.get('deliverable', ''))}</text>
        </g>
        {arrow_svg}
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1600" width="1200" height="1600">
    <rect width="1200" height="1600" fill="{palette['bg']}" />
    {header_svg}

    <!-- Header Title -->
    <g transform="translate({margin_x}, 195)">
        <text x="0" y="46" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="44" font-weight="900" fill="{palette['title']}">{_escape_xml(title)}</text>
        <text x="0" y="96" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="500" fill="{palette['muted']}">{_escape_xml(subtitle)}</text>
    </g>

    <!-- Steps Container -->
    <g id="steps_container">
        {steps_svg}
    </g>

    <!-- Bottom Rule Card -->
    <g transform="translate({margin_x}, 1370)">
        <rect width="{content_w}" height="95" rx="14" fill="{palette['card_bg']}" stroke="{palette['primary']}" stroke-width="1.5" />
        <text x="36" y="58" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="26" font-weight="bold" fill="{palette['primary']}">⚡ 铁律</text>
        <text x="150" y="58" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="26" font-weight="500" fill="{palette['text']}">{_escape_xml(rule_note)}</text>
    </g>

    {footer_svg}
</svg>"""
    return svg


# =========================================================================
# Layout Template 5: Summary & CTA (Checklist & Discussion Trigger)
# =========================================================================
def render_summary_cta_card(data: Dict[str, Any], palette: Dict[str, str]) -> str:
    """
    Template 5: Summary Checklist & Interactive Discussion CTA
    Required keys: title, takeaways (list of strings), question
    Optional keys: category, page_idx, author, subtitle
    """
    title = data.get("title", "核心复盘与行动清单")
    subtitle = data.get("subtitle", "认知落地与实践反思")
    category = data.get("category", "KEY TAKEAWAYS")
    page_idx = data.get("page_idx", "05 / 05")
    author = data.get("author", None)
    footer_left = data.get("footer_left", None)
    takeaways = data.get("takeaways", [
        "微信图片消息享有极高公域推荐权重，是突破私域瓶颈的核心抓手",
        "封面必须坚持双栏复合与 4~8 字认知冲突 Hook，杜绝平铺长标题",
        "移动端字号严格执行 ≥28px 底线，以 4~8 字短语构建高密度认知卡片",
        "长文做深度沉淀，卡片做公域破圈，形成双轮驱动的内容矩阵"
    ])
    question = data.get("question", "在你的内容创作或技术传播中，是否尝试过将长文切片为图片消息发布？效果如何？")

    margin_x = 70
    content_w = 1200 - 2 * margin_x

    header_svg = _render_header_svg(category, page_idx, author, palette, margin_x=margin_x, curr_y=75)
    footer_svg = _render_footer_svg(palette, footer_text="THANK YOU FOR READING", footer_left=footer_left, margin_x=margin_x, y=1515)

    # Render Takeaway Items
    takeaways_svg = ""
    start_y = 330
    item_h = 135
    item_gap = 20

    for i, t in enumerate(takeaways[:4]):
        box_y = start_y + i * (item_h + item_gap)
        takeaways_svg += f"""
        <g transform="translate({margin_x}, {box_y})">
            <rect width="{content_w}" height="{item_h}" rx="16" fill="{palette['card_bg']}" stroke="{palette['border']}" stroke-width="1.5" />
            <circle cx="44" cy="67" r="22" fill="{palette['good_color']}22" stroke="{palette['good_color']}" stroke-width="2" />
            <text x="44" y="75" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="bold" fill="{palette['good_color']}">✓</text>
            
            <text x="86" y="52" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="bold" fill="{palette['primary']}">CHECKLIST 0{i+1}</text>
            <text x="86" y="98" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="bold" fill="{palette['title']}">{_escape_xml(t)}</text>
        </g>
        """

    # Discussion Box
    disc_y = 970
    disc_h = 320
    if "\n" in question:
        q_lines = question.split("\n", 1)
        q_line1 = q_lines[0]
        q_line2 = q_lines[1]
    else:
        q_line1 = question[:22]
        q_line2 = question[22:]

    disc_svg = f"""
    <g transform="translate({margin_x}, {disc_y})">
        <rect width="{content_w}" height="{disc_h}" rx="22" fill="{palette['card_bg']}" stroke="{palette['primary']}" stroke-width="2.5" />
        
        <!-- Top Discussion Pill -->
        <rect x="40" y="34" width="200" height="46" rx="10" fill="{palette['primary']}" />
        <text x="140" y="66" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="24" font-weight="900" fill="{palette['badge_fg']}">💬 互动探讨</text>
        
        <!-- Big Question -->
        <text x="40" y="145" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="bold" fill="{palette['title']}">{_escape_xml(q_line1)}</text>
        <text x="40" y="200" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="bold" fill="{palette['title']}">{_escape_xml(q_line2)}</text>
        
        <!-- Callout Subtext -->
        <text x="40" y="270" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="26" font-weight="500" fill="{palette['muted']}">欢迎在评论区留言交流，分享你的第一手实战体验！</text>
    </g>
    """

    # Interaction Action Banner
    action_y = 1320
    action_svg = f"""
    <g transform="translate({margin_x}, {action_y})">
        <rect width="{content_w}" height="140" rx="18" fill="{palette['card_sub_bg']}" stroke="{palette['border']}" stroke-width="1.5" />
        
        <!-- 3 Pillars: Like / Collect / Share -->
        <g transform="translate({content_w * 0.16}, 70)">
            <text x="0" y="0" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="32">❤️</text>
            <text x="0" y="42" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="26" font-weight="bold" fill="{palette['title']}">点赞支持</text>
        </g>
        <line x1="{content_w * 0.33}" y1="30" x2="{content_w * 0.33}" y2="110" stroke="{palette['border']}" stroke-width="1" />
        
        <g transform="translate({content_w * 0.50}, 70)">
            <text x="0" y="0" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="32">⭐</text>
            <text x="0" y="42" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="26" font-weight="bold" fill="{palette['title']}">收藏备用</text>
        </g>
        <line x1="{content_w * 0.67}" y1="30" x2="{content_w * 0.67}" y2="110" stroke="{palette['border']}" stroke-width="1" />
        
        <g transform="translate({content_w * 0.84}, 70)">
            <text x="0" y="0" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="32">↗️</text>
            <text x="0" y="42" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="26" font-weight="bold" fill="{palette['title']}">转发朋友</text>
        </g>
    </g>
    """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1600" width="1200" height="1600">
    <rect width="1200" height="1600" fill="{palette['bg']}" />
    {header_svg}

    <!-- Header Title -->
    <g transform="translate({margin_x}, 195)">
        <text x="0" y="46" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="44" font-weight="900" fill="{palette['title']}">{_escape_xml(title)}</text>
        <text x="0" y="96" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="500" fill="{palette['muted']}">{_escape_xml(subtitle)}</text>
    </g>

    <!-- Takeaways Container -->
    {takeaways_svg}

    <!-- Discussion Box -->
    {disc_svg}

    <!-- Action Bar -->
    {action_svg}

    {footer_svg}
</svg>"""
    return svg


# =========================================================================
# Main Dispatcher & Rendering Utilities
# =========================================================================
CARD_RENDERERS = {
    "cover": render_cover_card,
    "vs_comparison": render_vs_comparison_card,
    "bullet_points": render_bullet_points_card,
    "pipeline_steps": render_pipeline_steps_card,
    "summary_cta": render_summary_cta_card,
}


def generate_photo_card_svg(
    card_type: str,
    data: Dict[str, Any],
    theme: str = "navy_gold"
) -> str:
    """Generate SVG string for a given card type and data."""
    renderer = CARD_RENDERERS.get(card_type)
    if not renderer:
        raise ValueError(f"Unknown card type: {card_type}. Available: {list(CARD_RENDERERS.keys())}")

    palette = THEMES.get(theme, THEMES["navy_gold"])
    return renderer(data, palette)


def render_svg_to_png(svg_content: str, output_png_path: Path, resample_width: int = 1200) -> Path:
    """Write SVG content to temp file and render to high-definition PNG via macOS sips."""
    output_png_path = Path(output_png_path)
    output_png_path.parent.mkdir(parents=True, exist_ok=True)

    svg_path = output_png_path.with_suffix(".svg")
    svg_path.write_text(svg_content, encoding="utf-8")

    # Run sips on macOS to convert SVG to PNG
    cmd = [
        "sips",
        "-s", "format", "png",
        "--resampleWidth", str(resample_width),
        str(svg_path),
        "--out", str(output_png_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.success(f"Generated 3:4 photo card: {output_png_path} ({resample_width}px width)")
        return output_png_path
    except subprocess.CalledProcessError as e:
        logger.error(f"sips failed to render SVG to PNG: {e.stderr}")
        raise RuntimeError(f"Failed to render PNG via sips: {e.stderr}")


def generate_photo_deck(deck_spec: Dict[str, Any], output_dir: Path, resample_width: int = 1200) -> List[Path]:
    """
    Batch generate a complete photo card deck from a spec dictionary.
    Returns list of generated PNG file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    theme = deck_spec.get("theme", "navy_gold")
    cards = deck_spec.get("cards", [])
    total_cards = len(cards)

    generated_paths = []

    for i, card_info in enumerate(cards):
        card_type = card_info.get("type", "bullet_points")
        card_data = card_info.get("data", card_info)

        # Set default page_idx if missing
        if "page_idx" not in card_data:
            card_data["page_idx"] = f"{i+1:02d} / {total_cards:02d}"

        # Default filename
        slug = card_info.get("name", f"photo_{i+1:02d}_{card_type}")
        out_png = output_dir / f"{slug}.png"

        svg_content = generate_photo_card_svg(card_type, card_data, theme=theme)
        png_path = render_svg_to_png(svg_content, out_png, resample_width=resample_width)
        generated_paths.append(png_path)

    return generated_paths
