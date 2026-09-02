import unittest
from pathlib import Path
from src.blogger.core.markdown_parser import render_markdown_to_clean_text, parse_markdown_payload


class TestPhotoCleanText(unittest.TestCase):
    def test_render_markdown_to_clean_text(self):
        md = """# 0.99刀真相：揭秘域名暴利定价

💡 核心洞察：买域名绝不能只看首年促销价。域名本质是“租借资产”，全生命周期的持有成本完全取决于第二年及以后的续费价格与隐藏条款。

## .xyz 6~9 位纯数字为什么这么便宜？
「6 位及以上纯数字的 .xyz 域名只要 6~7 元/年」并非短期促销：
• 规则范围：涵盖 6~9 位纯数字，组合多达 11.11 亿个。
• 续费同价：官方批发底价固定，零售约 $0.80 ~ $0.99/年，持有永不涨价。
• 最佳场景：极度适合个人服务器、DDNS 动态解析、API 测试或 Web3 地址绑定。

【低成本注册实操避坑四步法】
1. 全局比价（TLD-List）：购买前务必查清注册、续费和转入三项价格。
2. 认准零加价平台：优先选择 Cloudflare Registrar（成本直售）、Porkbun 等良心平台。
3. 按需配置后缀：测试脚本选 .xyz 纯数字；正式品牌项目优先考虑 .com。
4. 利用 Transfer 降本：低价首年域名在 60 天后转入 Cloudflare 锁定成本。

💬 互动探讨：
你注册过最便宜或最贵的域名是多少钱？在选购和续费中踩过哪些刺客套路？欢迎在评论区分享你的实战经验！

#域名注册 #云计算 #避坑指南
"""
        clean = render_markdown_to_clean_text(md)

        # 1. Standalone hashtags stripped
        self.assertNotIn("#域名注册", clean)

        # 2. H1 top title stripped from body
        self.assertFalse(clean.startswith("# "))

        # 3. Headings converted to 【...】
        self.assertIn("【.xyz 6~9 位纯数字为什么这么便宜？】", clean)
        self.assertIn("【低成本注册实操避坑四步法】", clean)

        # 4. Check that sections are separated by blank lines (\n\n)
        self.assertIn("隐藏条款。\n\n【.xyz", clean)
        self.assertIn("地址绑定。\n\n【低成本", clean)
        self.assertIn("锁定成本。\n\n💬 互动探讨：", clean)

        # 5. Check that list items are on individual lines
        self.assertIn("• 规则范围：涵盖 6~9 位纯数字，组合多达 11.11 亿个。\n• 续费同价：", clean)
        self.assertIn("1. 全局比价（TLD-List）：购买前务必查清注册、续费和转入三项价格。\n2. 认准零加价平台：", clean)

    def test_wechat_html_body_line_breaks(self):
        md = """💡 核心洞察：练习时觉得枯燥完全正常。

【大脑不是玄学放空，而是一套神经控制力训练】
• 注意力离散重捕获：经历「专注 → 走神 → 察觉 → 拉回」闭环。
• 抑制默认模式网络（DMN）：下调大脑背景噪音。

【工程师视角的 3 种极简生理降载实操】
1. 降维至 2 分钟微习惯：在任务切换时做 3 次慢呼气。
2. 生理性叹息：鼻腔连续吸气两次，嘴部长呼气。

💬 互动探讨：
大家有哪些快速降噪的私人技巧？欢迎在评论区分享！"""

        clean = render_markdown_to_clean_text(md)
        clean_html_text = clean.replace('\n', '<br>')
        html_body = f'<p>{clean_html_text}</p>'

        # Inter-paragraph breaks must be double <br>
        self.assertIn("完全正常。<br><br>【大脑不是玄学放空", html_body)
        self.assertIn("背景噪音。<br><br>【工程师视角", html_body)
        self.assertIn("嘴部长呼气。<br><br>💬 互动探讨：", html_body)

        # List items and titles must have single <br>
        self.assertIn("【大脑不是玄学放空，而是一套神经控制力训练】<br>• 注意力离散重捕获", html_body)
        self.assertIn("【工程师视角的 3 种极简生理降载实操】<br>1. 降维至 2 分钟微习惯", html_body)
        self.assertIn("💬 互动探讨：<br>大家有哪些快速降噪", html_body)

    def test_actual_payload_article(self):
        payload_path = Path("articles/2026-09-02-photo-meditation-brain-reboot/article.md")
        data = parse_markdown_payload(payload_path)
        clean = data["clean_text"]
        
        self.assertNotIn("#认知思维", clean)
        self.assertIn("识别为低效。\n\n【大脑不是玄学放空", clean)
        self.assertIn("主动做出决策。\n\n【工程师视角", clean)
        self.assertIn("焦虑带宽。\n\n💬 互动探讨：", clean)


if __name__ == "__main__":
    unittest.main()
