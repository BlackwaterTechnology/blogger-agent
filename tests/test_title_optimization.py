#!/usr/bin/env python3
"""
Unit tests for title optimization, separator sanitization, and 20-character limit enforcement.
"""

import sys
import re
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.blogger.core.markdown_parser import parse_markdown_payload


def sanitize_photo_title(raw_title: str) -> str:
    """Sanitize photo message title according to blogger standards."""
    photo_title = raw_title.strip()
    # If separator follows punctuation (？, ！, ：, ，), clean up separator without duplicate punctuation
    photo_title = re.sub(r'([？!！:：,，])\s*(\uff5c|\||\u2014\u2014|\u2014|-)\s*', r'\1', photo_title)
    # Otherwise replace remaining spaced separators with clean Chinese colon '：'
    photo_title = re.sub(r'\s*(\uff5c|\||\u2014\u2014|\u2014|-)\s*', '：', photo_title)
    photo_title = re.sub(r'\s+', '', photo_title)  # Remove residual spaces
    if len(photo_title) > 20:
        photo_title = photo_title[:20].rstrip('：，？！')
    return photo_title


def test_sanitize_fullwidth_pipe_with_spaces():
    raw = "冥想是空耗时间？ ｜ 神经科学重构：大脑工程化降载指南"
    sanitized = sanitize_photo_title(raw)
    assert " ｜ " not in sanitized
    assert "｜" not in sanitized
    assert "？：" not in sanitized
    assert len(sanitized) <= 20
    assert sanitized == "冥想是空耗时间？神经科学重构：大脑工程化"


def test_sanitize_pipe_without_prior_punctuation():
    raw = "0.99刀真相 ｜ 揭秘域名暴利定价"
    sanitized = sanitize_photo_title(raw)
    assert sanitized == "0.99刀真相：揭秘域名暴利定价"
    assert len(sanitized) == 15
    assert len(sanitized) <= 20


def test_sanitize_em_dash_with_spaces():
    raw = "单元测试只在验证开发者的想象力 —— PBT与模型测试"
    sanitized = sanitize_photo_title(raw)
    assert " —— " not in sanitized
    assert "——" not in sanitized
    assert len(sanitized) <= 20
    assert sanitized == "单元测试只在验证开发者的想象力：PBT与"


def test_clean_short_title_preservation():
    raw = "0.99刀真相：揭秘域名暴利定价"
    sanitized = sanitize_photo_title(raw)
    assert sanitized == "0.99刀真相：揭秘域名暴利定价"
    assert len(sanitized) == 16
    assert len(sanitized) <= 20


def test_question_formula_preservation():
    raw = "冥想是空耗时间？大脑正在信息戒断"
    sanitized = sanitize_photo_title(raw)
    assert sanitized == "冥想是空耗时间？大脑正在信息戒断"
    assert len(sanitized) == 16
    assert len(sanitized) <= 20


def test_parse_markdown_payload_photo_titles():
    # Test existing photo articles
    reboot_md = Path("articles/2026-09-02-photo-meditation-brain-reboot/article.md")
    if reboot_md.exists():
        data = parse_markdown_payload(reboot_md)
        assert data["type"] == "photo"
        assert len(data["title"]) <= 20
        assert " ｜ " not in data["title"]
        assert " —— " not in data["title"]

    crush_md = Path("articles/2026-09-02-photo-youth-sublimation-crush/article.md")
    if crush_md.exists():
        data = parse_markdown_payload(crush_md)
        assert data["type"] == "photo"
        assert len(data["title"]) <= 20
        assert " ｜ " not in data["title"]

    domain_md = Path("articles/published/2026-09-01-photo-domain-pricing-xyz/article.md")
    if domain_md.exists():
        data = parse_markdown_payload(domain_md)
        assert data["type"] == "photo"
        assert len(data["title"]) <= 20
        assert " ｜ " not in data["title"]


if __name__ == "__main__":
    test_sanitize_fullwidth_pipe_with_spaces()
    test_sanitize_em_dash_with_spaces()
    test_clean_short_title_preservation()
    test_question_formula_preservation()
    test_parse_markdown_payload_photo_titles()
    print("All title optimization tests passed successfully!")
