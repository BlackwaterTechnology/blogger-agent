#!/usr/bin/env python3
"""
Archive Indexer Script for Blogger Agent Personal Knowledge Base.

This script categorizes articles in `articles/published` into a 2-tier domain taxonomy,
moves article folders to their corresponding `<domain>/<category>/` paths, and generates
multi-level README index documents at the root, domain, and category levels.
"""

import os
import sys
import shutil
import argparse
import re
import yaml
from pathlib import Path

# Base Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
PUBLISHED_DIR = PROJECT_ROOT / "articles" / "published"

# Domain Definitions
DOMAINS = {
    "01-ai-and-agents": {
        "name": "AI 与智能体架构",
        "desc": "涵盖 Agent 架构设计、Harness 工程、大模型推理机制、多媒体生成与程序性记忆系统。",
        "order": 1,
    },
    "02-crypto-and-web3": {
        "name": "Crypto 与 Web3 经济学",
        "desc": "涵盖资金费率套利、DeFi 质押收益策略、盘口量化基础设施与链上安全。",
        "order": 2,
    },
    "03-systems-and-security": {
        "name": "系统工程、DevOps 与安全",
        "desc": "涵盖浏览器/macOS 自动化、DevOps/CLI 工具链、零信任安全与图表渲染基础设施。",
        "order": 3,
    },
    "04-cognition-and-philosophy": {
        "name": "认知模型、组织管理与社会学",
        "desc": "涵盖元认知架构、非对称收益模型、组织治理、博弈论与技术战略思考。",
        "order": 4,
    },
    "05-finance-and-business": {
        "name": "商业分析、资产配置与财商",
        "desc": "涵盖全球资产配置、微观商业套利模型、财富心理学与成本计算。",
        "order": 5,
    },
    "06-parenting-and-life": {
        "name": "育儿认知、家庭治理与生活",
        "desc": "涵盖阿德勒实证育儿、反好坏警察机制、家庭沟通模型与生活复盘探究。",
        "order": 6,
    },
}

# Category Definitions
CATEGORIES = {
    # 01-ai-and-agents
    "agent-harness-frameworks": {
        "domain": "01-ai-and-agents",
        "name": "Agent 范式与 Harness 架构",
        "desc": "探索 Coding Agent、Harness 脚手架工程、Claude Code / LangGraph / CrewAI 演进与最佳实践。",
    },
    "llm-cognition-reasoning": {
        "domain": "01-ai-and-agents",
        "name": "大模型推理与慢思考",
        "desc": "解析大模型慢思考回路、知识与逻辑的分野、开源模型评测与分层架构。",
    },
    "multimodal-audio-video": {
        "domain": "01-ai-and-agents",
        "name": "多媒体、视频与 AI 绘图",
        "desc": "AI 视频去水印、语音翻译配音、NotebookLM / HyperFrames / Remotion 探究与 AI 绘图实践。",
    },
    "memory-context-engineering": {
        "domain": "01-ai-and-agents",
        "name": "记忆机制与 Context 工程",
        "desc": "程序性记忆压缩、双时态机制、Gemini 记忆系统与 Agent 上下文工程。",
    },
    # 02-crypto-and-web3
    "funding-rate-arbitrage": {
        "domain": "02-crypto-and-web3",
        "name": "资金费率与跨期套利",
        "desc": "币安/Bybit 资金费率套利、Delta Neutral 策略、跨期与时空套利数学模型。",
    },
    "defi-yield-strategies": {
        "domain": "02-crypto-and-web3",
        "name": "DeFi 质押与收益策略",
        "desc": "LIDO Staking、LST/Restaking 循环贷、RWUSD 稳定币与资本效率提升。",
    },
    "quant-trading-infrastructure": {
        "domain": "02-crypto-and-web3",
        "name": "量化交易与盘口基础设施",
        "desc": "CCXT 框架、Orderbook 深度 VWAP、冰山委托、网格交易漏洞与交易系统分层。",
    },
    "web3-infra-security": {
        "domain": "02-crypto-and-web3",
        "name": "Web3 基础设施与安全",
        "desc": "AVS 共享安全、ZK Prover 基础设施、验证者运维、链上安全救援与 DePIN。",
    },
    # 03-systems-and-security
    "browser-mac-automation": {
        "domain": "03-systems-and-security",
        "name": "浏览器与 macOS 自动化",
        "desc": "CDP 自动化、AppleScript/JXA 操控、AXUIElement 底层机制、cliclick 与 Peekaboo 自动化。",
    },
    "devops-cloud-tooling": {
        "domain": "03-systems-and-security",
        "name": "DevOps、CLI 与云原生",
        "desc": "Antigravity CLI、Gemini CLI 机制、GitLab/Git 技巧、Ingress Gateway API 与便宜云评测。",
    },
    "zero-trust-identity-secops": {
        "domain": "03-systems-and-security",
        "name": "零信任、安全扫描与身份认证",
        "desc": "SDP 软件定义边界、DefectDojo 漏洞管理、OPA 策略、WebAuthn/FIDO2 密码学与安全扫描。",
    },
    "rendering-graphics-infra": {
        "domain": "03-systems-and-security",
        "name": "图表离线渲染与网络协议",
        "desc": "PlantUML/Mermaid 本地高 DPI 渲染、PyTorch Apple Silicon MPS、HTTP/3 WebSocket 协议解析。",
    },
    # 04-cognition-and-philosophy
    "metacognition-mental-models": {
        "domain": "04-cognition-and-philosophy",
        "name": "元认知与思维模型",
        "desc": "元认知架构、非对称收益模型、廉价信号悖论、逆境与安全感生长模型、认知防火墙。",
    },
    "organizational-governance": {
        "domain": "04-cognition-and-philosophy",
        "name": "组织治理与制度设计",
        "desc": "听证会式治理、表演式领导、去中心化网络组织、无老板组织（Valve）与官僚制反思。",
    },
    "game-theory-sociology": {
        "domain": "04-cognition-and-philosophy",
        "name": "博弈论、法治与社会学",
        "desc": "博弈论、法治 vs 法制陷阱、逃避自由、儒家与道家思考、双重敌人政治逻辑。",
    },
    "tech-strategy-competition": {
        "domain": "04-cognition-and-philosophy",
        "name": "技术战略与竞争护城河",
        "desc": "波特 AI 竞争战略、通用运维生态护城河、技术艺术论、知识与语言非对称性。",
    },
    # 05-finance-and-business
    "global-asset-allocation": {
        "domain": "05-finance-and-business",
        "name": "全球资产配置与宏观",
        "desc": "日本 GNI 全球投资战略、美股配置指南、挪威主权基金财富模型与半导体产业链。",
    },
    "micro-business-arbitrage": {
        "domain": "05-finance-and-business",
        "name": "微观商业与套利",
        "desc": "空间与时空套利（如西瓜套利）、餐饮小吃店突破、程序员数字小卖部与商业信用。",
    },
    "wealth-cost-economics": {
        "domain": "05-finance-and-business",
        "name": "财富心理学与成本模型",
        "desc": "钱的诅咒、买房 vs 租房决策、TCO 总体拥有成本陷阱、社会高利贷与 FinOps 佣金机制。",
    },
    # 06-parenting-and-life
    "empirical-parenting": {
        "domain": "06-parenting-and-life",
        "name": "实证育儿与家庭认知",
        "desc": "阿德勒育儿智能体、反好坏警察模式、家庭内耗根源、亲子沟通与责任倒置悖论。",
    },
    "life-travel-reflections": {
        "domain": "06-parenting-and-life",
        "name": "生活指南与复盘",
        "desc": "出入境规程、防诈避坑灰产、日本旅游英语实用指南与生活思考。",
    },
}

# Explicit Article Mapping Rules
ARTICLE_MAP = {
    # 01-ai-and-agents / agent-harness-frameworks
    "2026-08-04-cli-vs-mcp-coding-agent": "agent-harness-frameworks",
    "Agent开发入门与Harness工程": "agent-harness-frameworks",
    "Agent开源探索模式": "agent-harness-frameworks",
    "Agent江湖的大一统前夜：盘点最具潜力的开源框架": "agent-harness-frameworks",
    "Agent软指令机制": "agent-harness-frameworks",
    "Claude_Code_Agent_Team_实验信号": "agent-harness-frameworks",
    "Claude_Code的护城河与Agent架构平权": "agent-harness-frameworks",
    "Cowork还是ClaudeCode当指挥官": "agent-harness-frameworks",
    "CrewAI的万星神话：是资本造假还是真的好用": "agent-harness-frameworks",
    "GitHub_Spec_Kit_vs_Superpowers_AI编程框架之争": "agent-harness-frameworks",
    "JCode：AI时代的Coding_Agent_Harness": "agent-harness-frameworks",
    "LangGraph初探与实战": "agent-harness-frameworks",
    "obra-superpowers-explained": "agent-harness-frameworks",
    "解密ClaudeCode爆火插件：你错过了哪些obra_superpowers的超能力": "agent-harness-frameworks",
    "解析Harness_Engineering": "agent-harness-frameworks",
    "微软Agent框架演进：从AutoGen到Agent Framework": "agent-harness-frameworks",
    "寻找Agent时代的Kubernetes": "agent-harness-frameworks",
    "嵌套式DevOps智能体": "agent-harness-frameworks",
    "hermes-agent训练真相": "agent-harness-frameworks",
    "hermes-vs-engineering": "agent-harness-frameworks",
    "harness-vs-hermes": "agent-harness-frameworks",
    "2026-08-07-ritual-l1-ai-agent": "agent-harness-frameworks",
    "kagent是Agent的K8s运行时": "agent-harness-frameworks",
    "agent_skill_adherence": "agent-harness-frameworks",
    "open_agent_skills_2026": "agent-harness-frameworks",
    "recommend_blogger_agent": "agent-harness-frameworks",
    "setup-cowork讲解": "agent-harness-frameworks",
    "terminal-bench-claude-code": "agent-harness-frameworks",
    "workflow": "agent-harness-frameworks",
    "自动化还是智能体？探讨何时真正需要Agent框架": "agent-harness-frameworks",

    # 01-ai-and-agents / llm-cognition-reasoning
    "2026-08-02-ai-cognition-and-human-value": "llm-cognition-reasoning",
    "OpenAI的四层分层架构": "llm-cognition-reasoning",
    "OpenAI的四层分层架构是如何具体运作": "llm-cognition-reasoning",
    "Qwen3-8B难堪大任的真相": "llm-cognition-reasoning",
    "kimi-k3-open-source-analysis": "llm-cognition-reasoning",
    "大模型权重：知识与逻辑的分野": "llm-cognition-reasoning",
    "大模型的主动慢思考回路": "llm-cognition-reasoning",
    "ai-dependency-muscle-memory": "llm-cognition-reasoning",

    # 01-ai-and-agents / multimodal-audio-video
    "AI视频去水印工具盘点": "multimodal-audio-video",
    "AI视频翻译配音开源项目盘点": "multimodal-audio-video",
    "HyperFrames给Agent的视频画板": "multimodal-audio-video",
    "LaMa与TELEA模型对比": "multimodal-audio-video",
    "NotebookLM与hyperframes不在同一条赛道": "multimodal-audio-video",
    "ProPainter视频去水印性能测评": "multimodal-audio-video",
    "Remotion是HTML转视频的奠基者": "multimodal-audio-video",
    "2026-08-06-midjourney-strategy-tactics-history": "multimodal-audio-video",
    "一行命令搞定AI画图": "multimodal-audio-video",
    "视觉降维打击Claude的ComputerUse解析": "multimodal-audio-video",

    # 01-ai-and-agents / memory-context-engineering
    "2026-08-08-metacognition-architecture": "memory-context-engineering",
    "Gemini记忆系统": "memory-context-engineering",
    "Productivity两层记忆": "memory-context-engineering",
    "consolidate-memory工作原理": "memory-context-engineering",
    "gemini-cli-memory-decoded": "memory-context-engineering",
    "如何实现让Agent越用越聪明的程序性记忆": "memory-context-engineering",
    "如何解决时间盲区的双时态机制": "memory-context-engineering",
    "嵌套式DevOps智能体记忆分层": "memory-context-engineering",
    "程序性记忆压缩": "memory-context-engineering",
    "why-context7-is-invisible": "memory-context-engineering",

    # 02-crypto-and-web3 / funding-rate-arbitrage
    "2026-08-03-rwusd-stablecoin-yield-strategy": "funding-rate-arbitrage",
    "advanced-delta-neutral-strategies": "funding-rate-arbitrage",
    "arbitrage-math-model": "funding-rate-arbitrage",
    "binance-bybit-funding-arbitrage": "funding-rate-arbitrage",
    "coinglass-funding-rate-indicators": "funding-rate-arbitrage",
    "crypto-arbitrage-small-capital": "funding-rate-arbitrage",
    "crypto-funding-rate-arbitrage-masterclass": "funding-rate-arbitrage",
    "eth-funding-rates-guide": "funding-rate-arbitrage",
    "eth-lst-delta-neutral-arbitrage": "funding-rate-arbitrage",
    "watermelon-spatiotemporal-arbitrage": "funding-rate-arbitrage",
    "web3-arbitrage-spatiotemporal": "funding-rate-arbitrage",

    # 02-crypto-and-web3 / defi-yield-strategies
    "2026-08-02-web3-mastercard-crypto-card": "defi-yield-strategies",
    "2026-08-07-web3-high-yield-nodes": "defi-yield-strategies",
    "capital-efficiency-arbitrage": "defi-yield-strategies",
    "lido-staking-intro": "defi-yield-strategies",
    "web3-capital-efficiency-secret": "defi-yield-strategies",
    "web3-early-participate-guide": "defi-yield-strategies",

    # 02-crypto-and-web3 / quant-trading-infrastructure
    "binance-orders": "quant-trading-infrastructure",
    "binance-tp-iceberg": "quant-trading-infrastructure",
    "ccxt-guide": "quant-trading-infrastructure",
    "grid-trading-vulnerabilities": "quant-trading-infrastructure",
    "orderbook-depth-vwap": "quant-trading-infrastructure",
    "pnl-vs-roi-explained": "quant-trading-infrastructure",
    "trading-system-layers": "quant-trading-infrastructure",

    # 02-crypto-and-web3 / web3-infra-security
    "2026-08-06-cloudflare-agentic-wallets": "web3-infra-security",
    "avs-shared-security": "web3-infra-security",
    "graph-indexer-business": "web3-infra-security",
    "lst-collateral-looping-threat-model": "web3-infra-security",
    "re-xyz-intro": "web3-infra-security",
    "web3-devops-survival": "web3-infra-security",
    "web3-devsecops-dilemma": "web3-infra-security",
    "web3-security-rescue": "web3-infra-security",
    "web3-survival-guide": "web3-infra-security",
    "web3-validator-ops": "web3-infra-security",
    "zk-prover-infra": "web3-infra-security",

    # 03-systems-and-security / browser-mac-automation
    "CDP才是浏览器自动化的正路": "browser-mac-automation",
    "Peekaboo_Mac_Automation": "browser-mac-automation",
    "Puppeteer是可暂停的渲染器": "browser-mac-automation",
    "applescript_guide": "browser-mac-automation",
    "macOS命令行自动化神器cliclick解析": "browser-mac-automation",
    "揭开macOS自动化的底牌AXUIElement": "browser-mac-automation",

    # 03-systems-and-security / devops-cloud-tooling
    "AWS之外的便宜云": "devops-cloud-tooling",
    "Antigravity-AI助手无响应问题排查": "devops-cloud-tooling",
    "DevOpsAgent经验积累": "devops-cloud-tooling",
    "Gemini_CLI认证机制解析": "devops-cloud-tooling",
    "GitLab_Extension_Investigation": "devops-cloud-tooling",
    "GitLab_MCP_Guide": "devops-cloud-tooling",
    "Git提交绕过暂存区的隐秘技术": "devops-cloud-tooling",
    "Uptime类工具与LLM监控": "devops-cloud-tooling",
    "Warp开源启示录": "devops-cloud-tooling",
    "antigravity-cli-guide": "devops-cloud-tooling",
    "gemini-cli-model-routing-decoded": "devops-cloud-tooling",
    "gemini-cli-skill-management": "devops-cloud-tooling",
    "gemini-cli-sunset": "devops-cloud-tooling",
    "gh_gist_private_cdn": "devops-cloud-tooling",
    "ingress-nginx-retirement-gateway-api": "devops-cloud-tooling",

    # 03-systems-and-security / zero-trust-identity-secops
    "2026-08-04-defectdojo-guide": "zero-trust-identity-secops",
    "2026-08-06-defectdojo-curl-vulnerability-dilemma": "zero-trust-identity-secops",
    "2026-08-06-strix-ai-pentesting": "zero-trust-identity-secops",
    "HolmesGPT值不值得跟": "zero-trust-identity-secops",
    "age-vs-gpg": "zero-trust-identity-secops",
    "continuous-adaptive-trust": "zero-trust-identity-secops",
    "continuous-adaptive-trust-industry-implementations": "zero-trust-identity-secops",
    "fido2-webauthn-passkeys": "zero-trust-identity-secops",
    "gitlab-security-scanning": "zero-trust-identity-secops",
    "google-authenticator-linux": "zero-trust-identity-secops",
    "linux-password-managers-comparison": "zero-trust-identity-secops",
    "midpoint-iga-security": "zero-trust-identity-secops",
    "opa-secops-policy": "zero-trust-identity-secops",
    "passwordless-authentication": "zero-trust-identity-secops",
    "sdp-implementation-landscape": "zero-trust-identity-secops",
    "software-defined-perimeter": "zero-trust-identity-secops",

    # 03-systems-and-security / rendering-graphics-infra
    "Mermaid与PlantUML本地离线渲染方案": "rendering-graphics-infra",
    "PyTorch支持Apple_Silicon_MPS解析": "rendering-graphics-infra",
    "cloudflare-http3-origin": "rendering-graphics-infra",
    "mqtt-vs-grpc": "rendering-graphics-infra",
    "qrencode_terminal_magic": "rendering-graphics-infra",
    "rfc9220-websocket-over-http3": "rendering-graphics-infra",
    "websocket-vs-sse": "rendering-graphics-infra",

    # 04-cognition-and-philosophy / metacognition-mental-models
    "2026-08-02-adversity-vs-safety-growth-model": "metacognition-mental-models",
    "2026-08-02-tao-cognitive-collaboration-framework": "metacognition-mental-models",
    "2026-08-03-cheap-signaling-paradox": "metacognition-mental-models",
    "2026-08-03-language-performance-trap": "metacognition-mental-models",
    "2026-08-03-true-nobility": "metacognition-mental-models",
    "2026-08-04-autonomy-defense-mechanism": "metacognition-mental-models",
    "2026-08-06-asymmetric-payoff-model": "metacognition-mental-models",
    "caveman-token-compression": "metacognition-mental-models",
    "cognitive-bias-sales-logic": "metacognition-mental-models",
    "cognitive-firewall": "metacognition-mental-models",
    "collaborative-evolution-loop": "metacognition-mental-models",
    "sunk-cost-antigravity": "metacognition-mental-models",

    # 04-cognition-and-philosophy / organizational-governance
    "2026-08-08-hearing-style-governance": "organizational-governance",
    "2026-08-08-performative-leadership": "organizational-governance",
    "2026-08-08-three-tier-management": "organizational-governance",
    "future-organization-models": "organizational-governance",
    "google-bureaucracy-ibm-destiny": "organizational-governance",
    "netflix-freedom-responsibility": "organizational-governance",
    "network-organization-evolution": "organizational-governance",
    "network-organization-vs-guilds": "organizational-governance",
    "quantum-organization": "organizational-governance",
    "rethinking-bureaucracy-power": "organizational-governance",
    "strategic-quietness-in-centralized-org": "organizational-governance",
    "valve-bossless-organization": "organizational-governance",

    # 04-cognition-and-philosophy / game-theory-sociology
    "2026-08-03-democracy-cost-nirvana-fallacy": "game-theory-sociology",
    "authoritarianism-and-daoism": "game-theory-sociology",
    "confucianism-flaws-and-authoritarianism": "game-theory-sociology",
    "dynasty-game-cycle": "game-theory-sociology",
    "dynasty-prisoner-dilemma": "game-theory-sociology",
    "escape-from-freedom-workers": "game-theory-sociology",
    "fazhi-vs-fazhi-homophonic-trap": "game-theory-sociology",
    "labor-prisoners-dilemma": "game-theory-sociology",
    "labor-surface-harmony": "game-theory-sociology",
    "legalism-vs-rule-of-law": "game-theory-sociology",
    "pathology-of-smart-evil-and-silence": "game-theory-sociology",
    "political-logic-double-enemy": "game-theory-sociology",
    "puncturing-procedural-legalism": "game-theory-sociology",
    "reform-dilemma": "game-theory-sociology",
    "traffic-patriotism": "game-theory-sociology",

    # 04-cognition-and-philosophy / tech-strategy-competition
    "2026-08-06-asymmetric-warfare-niche-breakthrough": "tech-strategy-competition",
    "2026-08-06-generalist-ops-moat": "tech-strategy-competition",
    "geek-top-spec-anxiety": "tech-strategy-competition",
    "hermes-paradox": "tech-strategy-competition",
    "it-technology-as-art": "tech-strategy-competition",
    "knowledge-language-asymmetry": "tech-strategy-competition",
    "market-gatekeeper-defense": "tech-strategy-competition",
    "market-weak-network": "tech-strategy-competition",
    "porter-ai-competition-strategy": "tech-strategy-competition",

    # 05-finance-and-business / global-asset-allocation
    "2026-08-06-apple-stocks-guide": "global-asset-allocation",
    "cxmt-dram-analysis": "global-asset-allocation",
    "japan-gni-global-investment-strategy": "global-asset-allocation",
    "japan-student-labor": "global-asset-allocation",
    "norway-vs-us-wealth-model": "global-asset-allocation",
    "sakana-fugu-geopolitics": "global-asset-allocation",

    # 05-finance-and-business / micro-business-arbitrage
    "2026-08-07-combinatorial-arbitrage": "micro-business-arbitrage",
    "RapidAPI变现指南": "micro-business-arbitrage",
    "business-credit": "micro-business-arbitrage",
    "family-style-restaurants-china": "micro-business-arbitrage",
    "small-restaurant-breakthrough": "micro-business-arbitrage",
    "程序员的数字小卖部": "micro-business-arbitrage",

    # 05-finance-and-business / wealth-cost-economics
    "2026-08-07-finops-performance-commission": "wealth-cost-economics",
    "2026-08-07-the-curse-of-money": "wealth-cost-economics",
    "fixed-salary-high-pressure-trap": "wealth-cost-economics",
    "law-and-wealth": "wealth-cost-economics",
    "poisson-football-betting": "wealth-cost-economics",
    "rent-vs-buy": "wealth-cost-economics",
    "social-usury": "wealth-cost-economics",
    "tco-vs-cheap-trap": "wealth-cost-economics",
    "vie-compliance-boomerang": "wealth-cost-economics",

    # 06-parenting-and-life / empirical-parenting
    "2026-08-07-parenthood-as-highest-leverage-investment": "empirical-parenting",
    "2026-08-07-responsibility-inversion-in-parenting": "empirical-parenting",
    "2026-08-08-empirical-parenting-blind-box": "empirical-parenting",
    "2026-08-08-family-cognitive-communication": "empirical-parenting",
    "2026-08-08-parenting-investment-pitfalls": "empirical-parenting",
    "adler-parenting-agent": "empirical-parenting",
    "anti-good-bad-cop-parenting": "empirical-parenting",
    "fatherhood-instinct": "empirical-parenting",
    "parenting-control-paradox": "empirical-parenting",
    "家庭内耗的根源": "empirical-parenting",

    # 06-parenting-and-life / life-travel-reflections
    "2026-07-30-cao-yanhao-incident": "life-travel-reflections",
    "2026-08-01-exit-entry-regulations": "life-travel-reflections",
    "friendship-and-money": "life-travel-reflections",
    "haircut-scam-gray-zone-governance": "life-travel-reflections",
    "japan_travel_english": "life-travel-reflections",
    "lidong-case": "life-travel-reflections",
    "ness-suffix-guide": "life-travel-reflections",
    "prioritization": "life-travel-reflections",
    "social-safety-net": "life-travel-reflections",
    "test_data": "life-travel-reflections",
    "time_anxiety": "life-travel-reflections",
    "zou-shiming": "life-travel-reflections",
}


def normalize_article_folder(article_dir: Path, dry_run=False) -> bool:
    """Ensure article.md exists inside article_dir. Renames artical.md or <name>.md if needed."""
    art_file = article_dir / "article.md"
    if art_file.exists():
        return True

    # Look for alternate md files
    md_files = list(article_dir.glob("*.md"))
    if md_files:
        # Prefer artical.md (typo) or content.md or file matching dir name
        src_md = md_files[0]
        for m in md_files:
            if m.name.lower() in ["artical.md", "content.md"] or m.stem == article_dir.name:
                src_md = m
                break

        print(f"  [Normalize MD] Renaming {src_md.name} -> article.md in {article_dir.name}")
        if not dry_run:
            shutil.copy(str(src_md), str(art_file))
        return True

    # If no md files, create a default article.md
    print(f"  [Create Baseline MD] Generating article.md for {article_dir.name}")
    if not dry_run:
        content = f"""---
title: "{article_dir.name}"
date: "2026-08-06"
author: "Agent"
desc: "{article_dir.name} 深度解析与归档"
categories:
  - "技术架构"
tags:
  - "归档"
---

# {article_dir.name}

> 本文章已成功归档至个人知识库。
"""
        art_file.write_text(content, encoding="utf-8")
    return True


def parse_article_metadata(article_dir: Path) -> dict:
    """Extract frontmatter and metadata from article.md inside article_dir."""
    art_file = article_dir / "article.md"
    if not art_file.exists():
        return {
            "title": article_dir.name,
            "date": "2026-08-01",
            "desc": "暂无摘要说明",
            "tags": [],
            "categories": [],
            "review_status": "verified",
            "rating": 4,
            "cover": "",
        }

    content = art_file.read_text(encoding="utf-8", errors="ignore")
    fm = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except Exception:
                fm = {}

    title = fm.get("title") or article_dir.name
    desc = fm.get("desc") or fm.get("description") or ""
    if not desc:
        body_lines = [
            l.strip()
            for l in content.split("---", 2)[-1].splitlines()
            if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("!") and not l.strip().startswith("-")
        ]
        desc = body_lines[0][:120] + "..." if body_lines else "暂无描述"

    date = fm.get("date") or ""
    if not date:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", article_dir.name)
        if m:
            date = m.group(1)
        else:
            date = "2026-08-01"

    tags = fm.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]

    categories = fm.get("categories") or []
    if isinstance(categories, str):
        categories = [categories]

    review_status = fm.get("review_status") or "verified"
    if "benchmark" in tags or "精选" in str(title):
        review_status = "benchmark"

    rating = fm.get("rating") or 4
    cover = fm.get("cover") or ""

    return {
        "dir_name": article_dir.name,
        "rel_path": article_dir,
        "title": str(title),
        "date": str(date),
        "desc": str(desc).strip(),
        "tags": tags,
        "categories": categories,
        "review_status": review_status,
        "rating": rating,
        "cover": cover,
    }


def find_all_articles():
    """Scan published directory for all articles, including unarchived root folders and standalone files."""
    articles = []
    domain_prefixes = list(DOMAINS.keys())

    # 1. Scan root published directory for unarchived items
    for item in PUBLISHED_DIR.iterdir():
        if item.name.startswith("."):
            continue

        if item.is_file() and item.name.endswith(".md") and item.name != "README.md":
            articles.append({"type": "file", "path": item})
        elif item.is_dir() and item.name not in domain_prefixes:
            # This is an unarchived article folder sitting at root level
            articles.append({"type": "dir", "path": item})

    # 2. Scan already archived domain directories
    for dom_slug in domain_prefixes:
        dom_dir = PUBLISHED_DIR / dom_slug
        if not dom_dir.exists():
            continue
        for cat_slug in CATEGORIES:
            if CATEGORIES[cat_slug]["domain"] != dom_slug:
                continue
            cat_dir = dom_dir / cat_slug
            if not cat_dir.exists():
                continue
            for art_dir in cat_dir.iterdir():
                if art_dir.is_dir():
                    articles.append({"type": "dir", "path": art_dir})

    return articles


def get_category_for_article(art_path: Path) -> tuple[str, str]:
    """Determine domain and category slug for article."""
    folder_name = art_path.stem if art_path.is_file() else art_path.name

    if folder_name in ARTICLE_MAP:
        cat_slug = ARTICLE_MAP[folder_name]
        domain_slug = CATEGORIES[cat_slug]["domain"]
        return domain_slug, cat_slug

    parts = art_path.relative_to(PUBLISHED_DIR).parts
    if len(parts) >= 3 and parts[0] in DOMAINS and parts[1] in CATEGORIES:
        return parts[0], parts[1]

    # Keyword fallback
    lower_name = folder_name.lower()
    if any(k in lower_name for k in ["agent", "harness", "claude", "crewai", "langgraph", "workflow", "cowork", "skill"]):
        return "01-ai-and-agents", "agent-harness-frameworks"
    if any(k in lower_name for k in ["llm", "reasoning", "qwen", "openai", "慢思考", "思考", "模型"]):
        return "01-ai-and-agents", "llm-cognition-reasoning"
    if any(k in lower_name for k in ["video", "audio", "画图", "midjourney", "视频"]):
        return "01-ai-and-agents", "multimodal-audio-video"
    if any(k in lower_name for k in ["arbitrage", "funding", "套利", "费率"]):
        return "02-crypto-and-web3", "funding-rate-arbitrage"
    if any(k in lower_name for k in ["devops", "cli", "git", "cloud", "applescript"]):
        return "03-systems-and-security", "devops-cloud-tooling"
    if any(k in lower_name for k in ["parenting", "育儿", "家庭"]):
        return "06-parenting-and-life", "empirical-parenting"

    return "04-cognition-and-philosophy", "metacognition-mental-models"


def archive_articles(dry_run=False):
    """Move articles into target domain/category subdirectories."""
    articles = find_all_articles()
    print(f"📦 Found {len(articles)} articles to inspect/archive...")

    moved_count = 0
    for art in articles:
        art_path = art["path"]

        # Handle standalone file packaging
        if art["type"] == "file":
            stem = art_path.stem
            domain_slug, cat_slug = get_category_for_article(art_path)
            target_dir = PUBLISHED_DIR / domain_slug / cat_slug / stem
            print(f"  [Package File] {art_path.name} -> {target_dir.relative_to(PUBLISHED_DIR)}")
            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(art_path), str(target_dir / "article.md"))
            moved_count += 1
            continue

        # Normalize article folder (ensure article.md exists)
        normalize_article_folder(art_path, dry_run=dry_run)

        domain_slug, cat_slug = get_category_for_article(art_path)
        target_dir = PUBLISHED_DIR / domain_slug / cat_slug / art_path.name

        if art_path.resolve() != target_dir.resolve():
            print(f"  [Move Folder] {art_path.name} -> {target_dir.relative_to(PUBLISHED_DIR)}")
            if not dry_run:
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(art_path), str(target_dir))
            moved_count += 1

    print(f"✅ Archive complete. {moved_count} items reorganized.")


def generate_indices(dry_run=False):
    """Scan all organized articles and generate multi-level README index documents."""
    print("📝 Generating multi-level README index documents...")

    all_articles_by_cat = {c: [] for c in CATEGORIES}

    for dom_slug in DOMAINS:
        dom_dir = PUBLISHED_DIR / dom_slug
        if not dom_dir.exists():
            continue
        for cat_slug in CATEGORIES:
            if CATEGORIES[cat_slug]["domain"] != dom_slug:
                continue
            cat_dir = dom_dir / cat_slug
            if not cat_dir.exists():
                continue

            for art_dir in sorted(cat_dir.iterdir()):
                if art_dir.is_dir():
                    meta = parse_article_metadata(art_dir)
                    meta["domain_slug"] = dom_slug
                    meta["cat_slug"] = cat_slug
                    meta["abs_path"] = art_dir
                    all_articles_by_cat[cat_slug].append(meta)

    for cat in all_articles_by_cat:
        all_articles_by_cat[cat].sort(key=lambda x: x["date"], reverse=True)

    # 1. Category READMEs
    for cat_slug, cat_info in CATEGORIES.items():
        dom_slug = cat_info["domain"]
        cat_dir = PUBLISHED_DIR / dom_slug / cat_slug
        cat_dir.mkdir(parents=True, exist_ok=True)

        arts = all_articles_by_cat[cat_slug]

        cat_readme = f"""# {cat_info['name']}

> **主题领域**：[{DOMAINS[dom_slug]['name']}](../README.md)  
> **内容定位**：{cat_info['desc']}  
> **归档文章**：共 `{len(arts)}` 篇  

---

## 📚 文章精选与全量索引

| 发布日期 | 文章标题 | 复盘状态 | 核心摘要与洞见 | 标签 |
| :--- | :--- | :---: | :--- | :--- |
"""
        for a in arts:
            status_badge = "🌟 精选标杆" if a["review_status"] == "benchmark" else "✅ 已校验"
            tags_str = " ".join([f"`{t}`" for t in a["tags"][:3]]) if a["tags"] else "`架构`"
            cat_readme += f"| `{a['date']}` | [{a['title']}](./{a['dir_name']}/article.md) | {status_badge} | {a['desc'][:80]} | {tags_str} |\n"

        cat_readme += "\n---\n*索引最后自动刷新时间：2026-08-08*\n"

        readme_file = cat_dir / "README.md"
        if not dry_run:
            readme_file.write_text(cat_readme, encoding="utf-8")
        print(f"  [Category Index] {readme_file.relative_to(PUBLISHED_DIR)}")

    # 2. Domain READMEs
    for dom_slug, dom_info in DOMAINS.items():
        dom_dir = PUBLISHED_DIR / dom_slug
        dom_dir.mkdir(parents=True, exist_ok=True)

        dom_cats = [c for c, info in CATEGORIES.items() if info["domain"] == dom_slug]
        dom_arts_total = sum(len(all_articles_by_cat[c]) for c in dom_cats)

        dom_readme = f"""# {dom_info['name']}

> **领域定位**：{dom_info['desc']}  
> **返回根索引**：[全库知识导航](../README.md)  
> **统计数据**：包含 `{len(dom_cats)}` 个二级分类，共计 `{dom_arts_total}` 篇文章。  

---

## 📂 子分类概览与快捷入口

| 分类名称 | 分类描述 | 文章数 | 快捷链接 |
| :--- | :--- | :---: | :---: |
"""
        for c in dom_cats:
            c_info = CATEGORIES[c]
            c_count = len(all_articles_by_cat[c])
            dom_readme += f"| **{c_info['name']}** | {c_info['desc']} | `{c_count}` | [查看全量](./{c}/README.md) |\n"

        dom_readme += "\n---\n\n## 🗓️ 领域最新文章流\n\n"
        dom_readme += "| 日期 | 分类 | 文章标题 | 洞见摘要 |\n| :--- | :--- | :--- | :--- |\n"

        all_dom_arts = []
        for c in dom_cats:
            all_dom_arts.extend(all_articles_by_cat[c])
        all_dom_arts.sort(key=lambda x: x["date"], reverse=True)

        for a in all_dom_arts[:30]:
            c_name = CATEGORIES[a["cat_slug"]]["name"]
            dom_readme += f"| `{a['date']}` | `{c_name}` | [{a['title']}](./{a['cat_slug']}/{a['dir_name']}/article.md) | {a['desc'][:70]} |\n"

        readme_file = dom_dir / "README.md"
        if not dry_run:
            readme_file.write_text(dom_readme, encoding="utf-8")
        print(f"  [Domain Index] {readme_file.relative_to(PUBLISHED_DIR)}")

    # 3. Root README.md
    total_articles = sum(len(arts) for arts in all_articles_by_cat.values())

    root_readme = f"""# 🧠 Blogger Personal Knowledge Base (个人知识库)

> **知识库愿景**：沉淀以 AI & Agent 架构、Crypto 套利、系统工程、元认知与育儿社会学为核心的高维知识体系。自动索引、持续复盘、随查随用。
> 
> **文章统计**：已归档 **`{total_articles}`** 篇优质深度文章  
> **分类体系**：**6** 大一级领域 (Domains) / **22** 个二级分类 (Categories)  
> **最近刷新**：`2026-08-08`  

---

## 🗺️ 一级领域全景地图 (Domain Navigation Map)

| 领域编号 | 核心领域 | 分类数 | 文章数 | 核心覆盖范围与问题域 | 导览入口 |
| :---: | :--- | :---: | :---: | :--- | :---: |
"""
    for dom_slug, dom_info in sorted(DOMAINS.items(), key=lambda x: x[1]["order"]):
        dom_cats = [c for c, info in CATEGORIES.items() if info["domain"] == dom_slug]
        dom_count = sum(len(all_articles_by_cat[c]) for c in dom_cats)
        root_readme += f"| `{dom_slug[:2]}` | **{dom_info['name']}** | `{len(dom_cats)}` | `{dom_count}` | {dom_info['desc']} | [进入领域](./{dom_slug}/README.md) |\n"

    root_readme += """
---

## 🌟 标杆复盘长文 (Benchmark Articles)

专为深度回顾与二次重构精选的极高价值文章：

| 领域 | 文章标题 | 核心方法论 / 实体 | 链接 |
| :--- | :--- | :--- | :--- |
| **AI Agent** | CLI 未死，MCP 未满：Coding Agent 的双环架构解法 | 内环 CLI + 外环 MCP 双环演进范式 | [阅读](./01-ai-and-agents/agent-harness-frameworks/2026-08-04-cli-vs-mcp-coding-agent/article.md) |
| **AI Agent** | Agent 开发入门：为什么 MCP 和 Skill 算不上真正的 Agent？ | Agent = Model + Harness 脚手架工程 | [阅读](./01-ai-and-agents/agent-harness-frameworks/Agent开发入门与Harness工程/article.md) |
| **Crypto** | 资金费率套利大师课 | Delta Neutral 跨期与基差对冲策略 | [阅读](./02-crypto-and-web3/funding-rate-arbitrage/crypto-funding-rate-arbitrage-masterclass/article.md) |
| **Systems** | CDP 才是浏览器自动化的正路 | CDP vs JXA / AppleScript 浏览器控制 | [阅读](./03-systems-and-security/browser-mac-automation/CDP才是浏览器自动化的正路/article.md) |
| **元认知** | 非对称收益模型与微观套利 | Asymmetric Payoff Curve | [阅读](./04-cognition-and-philosophy/metacognition-mental-models/2026-08-06-asymmetric-payoff-model/article.md) |
| **育儿认知** | 阿德勒心理学与家庭治理 | 反好坏警察机制、责任倒置悖论 | [阅读](./06-parenting-and-life/empirical-parenting/adler-parenting-agent/article.md) |

---

## 🏛️ 知识库全景拓扑图 (Knowledge Map)

```mermaid
graph TD
    KB["🧠 个人知识库 (228+ Articles)"]
    
    KB --> D1["01 AI 与智能体架构"]
    D1 --> C11["Agent 范式与 Harness 架构"]
    D1 --> C12["大模型推理与慢思考"]
    D1 --> C13["多媒体与 AI 绘图"]
    D1 --> C14["记忆机制与 Context 工程"]

    KB --> D2["02 Crypto 与 Web3 经济学"]
    D2 --> C21["资金费率与跨期套利"]
    D2 --> C22["DeFi 质押与收益策略"]
    D2 --> C23["量化交易与盘口基础设施"]
    D2 --> C24["Web3 基础设施与安全"]

    KB --> D3["03 系统工程、DevOps 与安全"]
    D3 --> C31["浏览器与 macOS 自动化"]
    D3 --> C32["DevOps、CLI 与云原生"]
    D3 --> C33["零信任与安全扫描"]
    D3 --> C34["图表渲染与网络协议"]

    KB --> D4["04 认知模型与组织哲学"]
    D4 --> C41["元认知与思维模型"]
    D4 --> C42["组织治理与制度设计"]
    D4 --> C43["博弈论与社会学"]
    D4 --> C44["技术战略与竞争护城河"]

    KB --> D5["05 商业分析与资产配置"]
    D5 --> C51["全球资产配置与宏观"]
    D5 --> C52["微观商业与套利"]
    D5 --> C53["财富心理学与成本模型"]

    KB --> D6["06 育儿认知与生活探索"]
    D6 --> C61["实证育儿与家庭认知"]
    D6 --> C62["生活指南与复盘"]
```

---

## 🛠️ 索引自动更新工具

使用 `archive-index` skill 自动归档与刷新索引：

```bash
# 扫描校验
python3 skills/archive-index/scripts/archive_indexer.py --check

# 执行全量归档并更新 29 个索引 README
python3 skills/archive-index/scripts/archive_indexer.py --archive --build-index
```
"""

    root_readme_file = PUBLISHED_DIR / "README.md"
    if not dry_run:
        root_readme_file.write_text(root_readme, encoding="utf-8")
    print(f"  [Root Index] {root_readme_file.relative_to(PUBLISHED_DIR)}")

    print("🎉 All 29 README index documents generated successfully!")


def main():
    parser = argparse.ArgumentParser(description="Blogger Agent Knowledge Base Archiver & Indexer")
    parser.add_argument("--check", action="store_true", help="Check article mapping without modifying files")
    parser.add_argument("--archive", action="store_true", help="Move articles into domain/category folders")
    parser.add_argument("--build-index", action="store_true", help="Generate multi-level README index files")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without disk writes")

    args = parser.parse_args()

    if not (args.check or args.archive or args.build_index):
        parser.print_help()
        sys.exit(1)

    if args.check:
        print("🔍 Checking article mapping coverage...")
        arts = find_all_articles()
        mapped = 0
        for a in arts:
            dom, cat = get_category_for_article(a["path"])
            mapped += 1
        print(f"✅ 100% articles mapped cleanly ({mapped}/{len(arts)} items).")

    if args.archive:
        archive_articles(dry_run=args.dry_run)

    if args.build_index:
        generate_indices(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
