---
name: archive-index
description: Use when the user asks to archive, organize, structure, or build indices for articles in `articles/published`, or explicitly uses the `/archive-index` command. It reorganizes articles into a structured 2-tier domain taxonomy and generates multi-level README index documents.
---

# Archive & Index Skill (`archive-index`)

## Overview

本 Skill 专门用于管理和维护 `articles/published` 目录下的个人技术与商业知识库。通过将平铺的文章归档至标准分类体系（Domain & Category），并自动在**根目录、一级领域目录、二级分类目录**三个层级生成与维护 `README.md` 索引文档，实现知识库的高效检索、主题脉络沉淀以及定期复盘优化。

---

## 核心工作流与指令

### 1. 知识库自动化工具

Skill 附带 Python 自动化处理脚本 `skills/archive-index/scripts/archive_indexer.py`。该脚本负责文章分类判定、文件目录归档移动、Frontmatter 元数据提取以及 29 个 `README.md` 索引文件的自动编译。

#### 执行检测（Check Mode）
仅扫描当前文章目录，输出分类匹配情况与缺失元数据的文章，不修改任何文件：
```bash
python3 skills/archive-index/scripts/archive_indexer.py --check
```

#### 执行归档与多级索引生成（Archive & Build Mode）
将 `articles/published/` 下的文章目录自动整理至对应的 `<domain>/<category>/` 子目录下，并重新生成/更新所有 29 个 `README.md` 索引文档：
```bash
python3 skills/archive-index/scripts/archive_indexer.py --archive --build-index
```

#### 增量更新索引（Build Index Only Mode）
当在已归档的子目录中新增或修改文章后，仅重新编译索引文档：
```bash
python3 skills/archive-index/scripts/archive_indexer.py --build-index
```

---

## 知识库分类体系 (Taxonomy)

包含 6 大一级领域（Domain）与 22 个二级主题分类（Category）：

1. **`01-ai-and-agents` (AI 与智能体架构)**
   - `agent-harness-frameworks`: Agent 范式、Harness 脚手架、Claude Code, LangGraph, CrewAI 等
   - `llm-cognition-reasoning`: 大模型推理能力、主动慢思考、知识与逻辑分野、开源大模型对比
   - `multimodal-audio-video`: AI 视频去水印、语音翻译配音、NotebookLM、HyperFrames、AI 绘图
   - `memory-context-engineering`: 程序性记忆、双时态机制、上下文工程、记忆分层

2. **`02-crypto-and-web3` (Crypto 与 Web3 经济学)**
   - `funding-rate-arbitrage`: 资金费率套利、跨期套利、基差与单币对对冲
   - `defi-yield-strategies`: LIDO 质押、LST/Restaking、收益耕作、资本效率
   - `quant-trading-infrastructure`: CCXT、Orderbook 深度 VWAP、冰山委托、网格交易漏洞
   - `web3-infra-security`: AVS 共享安全、ZK Prover、验证者运维、链上安全救援

3. **`03-systems-and-security` (系统工程、DevOps 与网络安全)**
   - `browser-mac-automation`: CDP 浏览器自动化、AppleScript/JXA、AXUIElement、cliclick
   - `devops-cloud-tooling`: Antigravity CLI、Gemini CLI、Git/GitLab 扩展、Gateway API
   - `zero-trust-identity-secops`: SDP 软件定义边界、DefectDojo、OPA 策略、WebAuthn/FIDO2
   - `rendering-graphics-infra`: PlantUML/Mermaid 离线高 DPI 渲染、PyTorch MPS、HTTP/3 WebSocket

4. **`04-cognition-and-philosophy` (认知模型、组织管理与社会哲学)**
   - `metacognition-mental-models`: 元认知架构、非对称收益模型、廉价信号悖论、自适应防御
   - `organizational-governance`: 去中心化组织、听证会治理、表演式领导、无老板组织
   - `game-theory-sociology`: 博弈论、法治 vs 法制、逃避自由、儒家与道家思考
   - `tech-strategy-competition`: 波特 AI 竞争战略、通用运维护城河、技术艺术论

5. **`05-finance-and-business` (商业分析、资产配置与财商微观)**
   - `global-asset-allocation`: 日本 GNI 全球投资、美股市值分析、挪威主权基金
   - `micro-business-arbitrage`: 空间时空套利、餐饮小吃店破局、程序员数字小卖部
   - `wealth-cost-economics`: 租房 vs 增购、套利数学模型、社会高利贷与钱的诅咒

6. **`06-parenting-and-life` (育儿认知、家庭治理与生活探索)**
   - `empirical-parenting`: 阿德勒育儿智能体、反好坏警察、责任倒置、家庭认知沟通
   - `life-travel-reflections`: 出入境规程、防诈避坑灰产、日本旅游英语、理发陷阱治理

---

## 多级索引文档规范

1. **根目录索引 (`articles/published/README.md`)**：
   - 知识库概览与统计数据（文章总数、领域覆盖、最新更新时间）。
   - 6 大 Pillar 可视化导航表格。
   - 复盘矩阵（标杆文章推荐、待补充文章清单、跨领域主题串联）。
   - 知识库架构 Mermaid 关系图。

2. **一级领域索引 (`articles/published/<domain>/README.md`)**：
   - 领域定位与涵盖问题域。
   - 二级分类快捷表格。
   - 领域内全量文章时间流列表（包含标题、发布时间、标签、Exec Summary 摘要、复盘状态）。

3. **二级分类索引 (`articles/published/<domain>/<category>/README.md`)**：
   - 分类主题深拆。
   - 文章精细索引卡片与核心洞见。

---

## Frontmatter 元数据标准

为了支持高质量的索引自动生成，每篇文章的 `article.md` 应包含以下 YAML Frontmatter：

```yaml
---
title: "文章完整标题"
date: "YYYY-MM-DD"
author: "Agent"
desc: "一句话文章摘要（100字以风）"
cover: "cover.png"
categories:
  - "一级领域名称"
  - "二级分类名称"
tags:
  - "标签1"
  - "标签2"
review_status: "verified" # 可选值: benchmark (精选标杆), verified (已复盘校验), needs_update (待优化更新)
rating: 5 # 可选值: 1-5 质量评分
---
```

---

## 文章复盘与优化工作流 (Review & Refactor)

1. **查阅索引定位目标**：查阅 `articles/published/README.md` 中的「待优化/复盘清单」。
2. **修改正文与元数据**：针对要优化的文章，完善代码示例、修正图片或添加 `review_status: verified`。
3. **重新编译索引**：运行 `python3 skills/archive-index/scripts/archive_indexer.py --build-index` 自动刷新全库索引。
