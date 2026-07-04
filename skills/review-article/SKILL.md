---
name: review-article
description: Use when invoked by a main agent to review an article draft, or explicitly triggered by `/review-article`. It reads the generated `article.md`, applies strict formatting checks, checks for AI tone cliches, and edits the markdown file directly.
---

# Review Article Skill

## Overview
This skill acts as a strict reviewer for article drafts. It checks the article's front matter, the integration of visual assets, and aggressively removes "AI tone" cliches from the text. Once reviewed, drafts can be published to platforms including WeChat, Juejin, CSDN, and Blogger.

## Workflow

### 阶段 1：发布前自审 (Pre-flight Checks)
你需要读取并检查目标 `article.md` 文件。逐项确认并**直接修改文件**解决问题。

```text
【发布前 Pre-flight】
1. 开篇检查：第一句话能让人停止滚动吗？读一遍，如果像"近期，开发者社区迎来了一个重磅消息"——必须重写。
2. AI 腔排查：全文搜陈词滥调（见下方「AI 腔急救包」），命中即改写。
3. 配图数量检查：正文**必须至少包含 2 张**能辅助理解的插图（封面除外）！如果没生成插图或只塞了一堆文字，属于严重违规。必须强制打回要求补充，或自己调用工具（mermaid/plantuml等）生成补充。
4. 孤儿图检查：每张生成的配图是否在正文中被引用并解释？没有引用的图要么删掉，要么补充正文上下文。
5. 证据检查：每个 ### 段落里是否至少有一处具体证据（代码 / 数字 / 案例 / 引用）？没有就补，或砍掉这段文字。
6. 摘要长度：`desc` 实际长度（中文字符 + 英文字母都算 1）：必须严格落在 60–120 字符。过长或过短必须精简或扩充。
```

### 阶段 2：AI 腔急救包替换
扫描正文，如果发现以下高危陈词，**写出即重写**：

| ✗ 写出即重写 | ✓ 替换方向 |
|------|------|
| "我们不禁要思考" / "值得我们深思" | 直接抛具体问题或数据 |
| "标志着 X 进入了一个全新的阶段" | 说清具体改变了什么旧结论 |
| "必将迎来更令人惊叹的进化" / "在 X 滋养下成长为更伟大的产品" | 删掉，或换成可证伪的预测 |
| "在这样的多重夹击下" / "巨头纷纷下场" | 列出具体三家公司及他们做了什么 |
| "无疑会对 X 产生积极的促进作用" | 删掉，或具体说"让 Y 在 Z 场景省 N 倍工作量" |
| "Y 已经走向成熟" 后面不接证据 | 删掉，或后接一个版本号 / 案例 |
| 段落收尾："未来可期 / 拭目以待 / 让我们一同见证" | 直接结束。中文写作不需要总结的总结 |
| 抽象比喻（"如同一艘巨轮""势不可挡的浪潮"） | 换成开发者经验的类比（"像 git rebase 时的 conflict marker"） |

### 阶段 3：格式微调
- **段落与列表**：确保 `- ` 列表或数字列表前**必须有空行**。如果没有空行，列表可能会被当作普通段落渲染。
- **标题**：正文的小标题不要带着生硬的编号如 `### 1. 核心痛点与背景`，改写为更自然的短句。

### 结束语
完成修改后，向主叫方报告审查完毕以及你修改了哪些内容（比如去掉了哪些 AI 词汇、修复了 `desc` 长度等）。
