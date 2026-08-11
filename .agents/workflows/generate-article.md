---
description: 自动生成高质量中文技术/商业文章 Payload（符合 YYYY-MM-DD-<slug> 规范、移动端优先配图、blogger.toml 微信合集校验），并调度 Subagent 进行终审打分。
---

// turbo-all

## 1. 强制思考链检查 (CoT Self-Check)
在生成任何实际的 Markdown 文件或图片前，Antigravity 必须先在回复中完整输出并回答 `skills/generate-article/SKILL.md` 要求的【内容质量自检】与【形式自检】：
- **极化主张**：明确的反直觉张力陈述句（CTR > 8%）。
- **社交货币**：提炼至少 1 个概念实体或方法论框架。
- **硬核证据与视觉建模**：规划 2-3 件硬核证据与 2-4 个视觉建模图表。
- **人称视角**：全程使用“我们/大家”视角，严格禁止第二人称“你/你的/您/您的”。
- **微信合集校验**：`collection` 必须且只能从 `blogger.toml` 的 `[platforms.wechat.accounts.default].article_collections` 列表中选择。

## 2. 视觉资产生成 (Generate Visual Assets)
按主题生成高清配图：
1. **封面图 `cover.png`**：**优先使用程序化瑞士平面排版直出**（`python tools/generate_cover.py --title "..." --subtitle "..." --category "..." --theme swiss_red|navy_gold|emerald|slate_lime`），彻底杜绝 AI 噪点与伪字。若确需使用 AI 绘图，必须使用 2D 扁平矢量插画风格，**严禁使用 3D 霓虹/发光脑/科幻 HUD/满屏假字等 AI 俗套图**。
2. **正文插图 (2-4 张)**：使用 PlantUML (`dpi 300`) 或原生 SVG + `sips` (`--resampleWidth 1920`) 生成结构化图表。严格执行移动端字号硬性底线（节点字号 ≥ 20px - 22px），文本极简抽象为 4-8 字短语。

## 3. 构造 Payload 目录与正文 (Create Payload)
在项目工作区创建标准目录：`articles/YYYY-MM-DD-<slug>/`（例如 `articles/2026-08-08-agent-collaboration`）。
在该目录下写入 `article.md`，使用合规的 YAML Front Matter：

```markdown
---
title: "[富有张力的爆款标题]"
author: "Agent"
desc: "[60-120字的摘要，高度凝练核心观点]"
collection: "[微信文章合集，必须来自 blogger.toml 的 article_collections 列表]"
cover: "cover.png"
---

[引人入胜的引题段落，使用“我们”引发共鸣...]

### [结构化小标题]

[正文逻辑与硬核证据...]

![[说明性文字]](illustration_1.png)
```

## 4. 资产搬运与调度 Subagent 审查 (Review, DO NOT Auto-Publish)
1. **资产搬运**：将生成的图片从 artifact 目录拷贝至 `articles/YYYY-MM-DD-<slug>/` 目录下，并重命名为 Markdown 引用的标准名称（如 `cover.png`, `illustration_1.png`）。
2. **调度 Review Subagent**：**起草完成后严禁直接自动发布！** 必须使用 `invoke_subagent` 派遣 review 子进程应用 `review-article` skill 进行品控打分、扫除 AI 腔与排版修复。
3. **完成汇报**：审查完成后，向用户报告审查打分卡得分及修改细节，并告知用户运行 `/publish-article` 进行推送。