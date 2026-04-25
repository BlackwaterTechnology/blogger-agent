---
name: wechat-publisher
description: 自动化微信公众号发布 skill。当用户需要写文章、分享经验、或发布内容到微信公众号时触发。此 skill 会优化文章结构、生成标题和插图（使用 PlantUML 或 Canva），生成特定格式的 Markdown 并利用 Python 脚本自动将草稿发布到微信公众平台。
---

# WeChat Publisher

## Overview

将任意输入内容（文章草稿、对话、观点、代码笔记等）转化为结构完整的微信公众号文章，自动生成插图和封面，并调用本地脚本自动推送到微信公众号草稿箱。

与纯界面的浏览器自动化不同，此 skill 使用的是封装好的 `publish.py` 脚本，Agent 只需准备好标准的 Payload 目录即可，无需手动逐步控制浏览器 UI。

## Required Tools/Servers

执行此 skill 需要以下能力：

- **bash**: 用于运行 Python 发布脚本和子进程图片生成。
- **文件系统**: 用于创建 Payload 目录、保存生成的图片和 Markdown。

### 图片生成（子进程模式）

为节省 token 开销，Canva 和 PlantUML 工具通过 **Claude 子进程** 按需调用，与主 agent 分离：

```
主 Agent
    │
    ├─ 需要生成图片时 → Bash 调用 → Claude 子进程 (canva + plantuml)
    │                                   │
    │                                   └─ 返回图片 URL / 文件路径 (存入 payload 目录)
    │
    └─ 生成 Payload 目录 → Bash 调用 → python3 publish.py
```

子进程配置文件（使用 `--strict-mcp-config` 严格限制）：
- `mcp-configs/canva-only.json` - Canva 封面和插图
- `mcp-configs/planuml-only.json` - PlantUML 技术图表

**重要**：子进程需要使用 `--dangerously-skip-permissions` 跳过权限检查，因为 `-p` 无头模式无法交互式批准工具调用。

## Workflow

```
用户输入 (写文章请求)
    ↓
Step 1: 内容分析与优化
    ↓
Step 2: 封面与插图生成 (按需)
    ↓
Step 3: 构造 Payload 目录
    ↓
Step 4: 执行发布脚本
```

### Step 1: 内容分析与优化

分析用户输入，生成完整的微信公众号文章：

1. **确定文章类型**：技术教程、经验分享、观点讨论、代码解析等。
2. **生成标题**：吸引人且准确描述内容。
3. **优化结构**：微信文章讲究排版，适度分段落。
4. **生成摘要**：**必须在 60-120 字以内**，这是微信官方对摘要长度的硬性要求。
5. **确定合集 (Collection)**：根据内容确定一个分类合集名称（例如 "AI", "Python" 等）。

### Step 2: 插图生成（子进程模式）

每篇文章如果需要插图或封面，**通过 Claude 子进程完成**，生成后保存到 Payload 目录。

**调用示例（以生成封面为例）**：

```bash
# 将图片直接下载到 payload 目录中
claude --strict-mcp-config --mcp-config ./mcp-configs/canva-only.json \
  --dangerously-skip-permissions \
  -p "$(cat <<'EOF'
# 封面图生成任务

为微信公众号文章生成封面图：
**标题**: 《如何自动化微信文章发布》

## 执行步骤
1. 使用 generate-design 生成封面（design_type: youtube_thumbnail 或 presentation）
2. 自动选择第一个候选设计并创建
3. 导出 PNG
4. 使用 curl 下载图片到本地：./payload_dir/cover.png

## 输出格式
只返回 JSON：{"success": true, "local_path": "./payload_dir/cover.png"}
EOF
)" --output-format json --max-turns 15
```

### Step 3: 构造 Payload 目录

1. 在当前项目下（或系统临时目录）创建一个 `payload_dir`（如 `test_data_auto`）。
2. 确保所有生成的封面和插图都已经放置在该目录中。
3. **关键步骤**：在 `payload_dir` 中创建并写入一个固定文件名为 `ARC-AGI-文章.md` 的文件。

**Markdown 格式规范（必须严格遵守）**：

此格式由 `publish.py` 内部的状态机进行严格解析，任何不符合格式的排版都将导致解析失败。

```markdown
# 标题
这里是文章的标题
# 作者
Agent
# 简介
这里是文章简介，长度必须严格控制在 60 到 120 个字符之间。
# 集合
AI
# 封面
cover.png
# 插图
illustration.png
# 正文
这里开始是文章的正文内容。
可以包含 Markdown 的各种语法，如加粗、代码块等。
内容会自动解析为 HTML 格式并保留。
```

注意事项：
- 标题标识如 `# 标题`, `# 作者`, `# 简介` 等必须精确匹配，且独占一行。
- `封面` 和 `插图` 下方填写的是相对于 payload 目录的文件名，如果没有图片，留空换行即可。
- 从 `# 正文` 以下的所有内容，均会被视为微信公众号文章正文。

### Step 4: 执行发布脚本

内容准备就绪后，使用 bash 运行发布脚本：

```bash
cd /Users/linwang/src/github/xiluo/skills/blogger
python3 publish.py --payload ./payload_dir
```

该脚本将自动接管 Google Chrome（使用 macOS 的 AppleScript 和 ChromeDomController），自动寻找或打开微信公众号后台（`mp.weixin.qq.com`），并将你生成的 Markdown 渲染、注入文本、设置原创、设置合集并上传封面插图。

**监控与异常处理**：
1. 观察脚本运行输出，注意是否有 `WARNING` 级别报错（如“Summary length is XX chars”）。
2. 如果提示 “WeChat Official Account tab not found”，说明当前浏览器中没有打开微信公众号页面。你需要提醒用户在 Chrome 中手动登录一次微信公众号后台。

## Example Usage

**用户输入**：
```
帮我写一篇关于 Agent 自动化的文章，发到微信草稿。
```

**执行流程**：
1. 扩写大纲并生成 60-120 字的简介。
2. 使用 Canva 子进程生成一个包含 "Agent Automation" 字样的封面图，保存为 `payload_dir/cover.png`。
3. 创建 `payload_dir/ARC-AGI-文章.md`，填充所需标签。
4. 执行 `python3 publish.py --payload ./payload_dir`。
5. 等待脚本完成，向用户报告草稿已保存，并提醒其在手机或浏览器预览确认。
