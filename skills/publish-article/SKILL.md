---
name: publish-article
description: Use when the user asks to publish or push an article or photo message (小绿书/图片消息) to platforms, or explicitly uses the `/publish-article` slash command. Trigger phrases include "/publish-article", "发布文章", "推送到公众号", "发布图片消息", "发布小绿书", "推送到小绿书".
---

# Publish Article Skill

## Overview
This skill takes a completed, reviewed Markdown payload directory and invokes the `blogger` CLI tool to automatically push the draft to configured platforms (WeChat Official Accounts, Juejin, CSDN, Blogger).

It supports both **Rich Text Articles (普通图文)** and **WeChat Photo Messages (3:4 竖版图片消息 / 微信画册 / 小绿书)** via automatic metadata dispatch (`type: "photo"` in `article.md`).

## Prerequisites（启动前必查，跳过会报错）

在执行发布命令之前，**必须**帮用户确认以下几项。如果前置不满足，`blogger` CLI 可能会中途崩溃。

1. **双 Chrome 实例分工（CRITICAL）**：
   - **微信公众号 (`wechat`)**：使用系统**日常 Chrome** 实例（通过 JXA/AppleScript 控制，避开微信反爬检测）。前置要求：日常 Chrome 必须勾选 **View / 查看 → Developer / 开发者 → Allow JavaScript from Apple Events / 允许 Apple 事件中的 JavaScript**，且已打开并登录 `mp.weixin.qq.com`。
   - **掘金 (`juejin`) 与 CSDN (`csdn`)**：使用**独立的 CDP Chrome 实例**（通过 `tools/launch-chrome-cdp.sh` 启动，端口 `9222`，用户目录 `~/.blogger-chrome-cdp`）。掘金与 CSDN 的会话常驻在此实例中，严禁在日常 Chrome 中寻找或误判两者状态。若未启动，运行 `bash tools/launch-chrome-cdp.sh`。
2. **确认目标 Payload 路径**：确保你要发布的文章目录存在且包含 `article.md` 及相关图片。

> ⚠️ 这几条只需在当前会话的**第一次**发布前确认。如果用户之前已经发过，可以假定满足。


## Workflow

### 阶段 1：执行发布命令

确认前置条件后，运行发布工具：

```bash
blogger --payload ./articles/<文章目录> --platform wechat
```

### 阶段 2：监控输出与状态汇报

**监控常见错误**：
- 看输出有无 `WARNING`。
- **看到 `通过 AppleScript 执行 JavaScript 的功能已关闭`**：说明 Prerequisites #1 没满足。让用户去 Chrome 菜单栏开开关，重跑即可。
- **看到 `WeChat Official Account tab not found`**：用户没登录公众号后台。让用户在 Chrome 里登录一次。

**收尾必须给用户一份清单**：

#### 场景 A：普通图文文章 (Rich Text)
```
✓ / ✗ 标题
✓ / ✗ 正文（看 "Filled via paste event"）
✓ / ✗ N 张图片（看 "Successfully initiated image paste/upload" 出现次数）
✓ / ✗ 原创声明（看 "Originality badge found"）
✗ 封面 → 让用户在编辑器右侧点「从正文选择」
✗ 合集 → 手动选
✗ 保存为草稿 → 手动点
```

#### 场景 B：图片消息 / 小绿书 (Photo Message, type: "photo")
```
✓ / ✗ 标题
✓ / ✗ N 张 3:4 竖版卡片（看 "Upload card [X/N]" 成功次数）
✓ 封面（默认选用第 1 张卡片 01_cover.png）
✓ 伴随文案（已注入至描述输入框）
✗ 话题与合集 → 在编辑器下方手动勾选确认
✗ 保存为草稿 → 手动点右下角「保存为草稿」
```
