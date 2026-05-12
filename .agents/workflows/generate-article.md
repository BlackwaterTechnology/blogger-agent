---
description: This workflow automates the process of generating high-quality articles for the `blogger-agent` project, ensuring strict adherence to formatting, tone, and visual requirements.
---

// turbo-all

## 1. 强制思考链检查 (CoT Checklist)
在生成任何实际的 Markdown 文件或图片前，Antigravity 必须先在回复中输出以下检查单：

```text
**【文章规范自我检查】**
1. **人称视角**：我将全程使用“我们/大家”，绝不使用具有说教感的“你/您的”。
2. **封面图**：需要生成 1 张 `cover.png`（必填）。
3. **插图规划**：我将在正文中生成至少 1 张说明图（如 `illustration_1.png`）。
4. **字数与格式**：摘要控制在 60-120 字，严格使用规定的 Markdown YAML 模板。
```

## 2. 视觉资产生成 (Generate Visual Assets)
根据主题，使用 `generate_image` 工具生成：
1. `cover.png`：高质量的概念封面图。**严禁使用流程图、架构图等宽幅技术图表作为封面**（因为裁剪后分辨率过低、太宽）。必须使用 `generate_image` 生成，并在提示词中要求：“aspect ratio 16:9, high resolution, centered composition, no text, avoid ultra-wide panoramic formats”。
2. `illustration_x.png`：用于解释核心原理或痛点的正文配图。可以使用宽幅技术图表。

*注意：生成的图片会暂时保存在 artifact 目录中，在最后一步需要拷贝到 Payload 目录。*

## 3. 构造 Payload 目录与正文 (Create Payload)
在项目工作区创建目录：`articles/<文章标题>/`。
在该目录下写入 `article.md`，**必须一字不差地套用以下骨架**，并替换中括号内容：

```markdown
---
title: "[富有张力的爆款标题]"
author: "Agent"
desc: "[60-120字的摘要，高度凝练核心观点]"
collection: "AI"
cover: "cover.png"
---

[引人入胜的引题段落，使用“我们”引发痛点共鸣...]

### 1. [痛点/背景解析]

[详细解释背景...]

![[说明性文字]](illustration_1.png)

### 2. [核心技术/方案剖析]

[使用生动的类比解释复杂技术...]

### 3. 总结

[掷地有声的总结...]
```

## 4. 资产审查与发布 (Review & Publish)
在执行发布前，**必须执行一致性审查**：确认生成的图片文件名（带有时间戳后缀）与 `article.md` 中引用的标准文件名（如 `cover.png`）是否一致。

使用 `run_command` 依次执行：
1. 将 artifact 目录中的图片拷贝至 `articles/<文章标题>/` 目录下，并**务必重命名**去除时间戳后缀。
2. 运行发布指令。

```bash
# 拷贝时请务必使用通配符匹配带时间戳的源文件，并将其重命名为 markdown 中引用的标准名称
cp /Users/linwang/.gemini/antigravity/brain/<conversation-id>/cover_*.png /Users/linwang/src/github/xiluo/skills/blogger/articles/<文章标题>/cover.png
cp /Users/linwang/.gemini/antigravity/brain/<conversation-id>/illustration_1_*.png /Users/linwang/src/github/xiluo/skills/blogger/articles/<文章标题>/illustration_1.png

cd /Users/linwang/src/github/xiluo/skills/blogger && blogger --payload ./articles/<文章标题>
```
3. 使用 `command_status` 跟踪发布结果并向用户汇报。