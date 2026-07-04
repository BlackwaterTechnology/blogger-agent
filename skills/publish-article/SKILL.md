---
name: publish-article
description: Use when the user asks to publish or push an article to platforms, or explicitly uses the `/publish-article` slash command. Trigger phrases include "/publish-article", "发布文章", "推送到公众号".
---

# Publish Article Skill

## Overview
This skill takes a completed, reviewed Markdown payload directory and invokes the `blogger` CLI tool to automatically push the draft to configured platforms (WeChat Official Accounts, Juejin, CSDN, Blogger).

## Prerequisites（启动前必查，跳过会报错）

在执行发布命令之前，**必须**帮用户确认以下几项。如果前置不满足，`blogger` CLI 可能会中途崩溃。

1. **Chrome 必须开启「允许 Apple 事件中的 JavaScript」**（默认关闭）——CLI 走 osascript 调 JS 操作微信编辑器，开关没开会抛 `通过 AppleScript 执行 JavaScript 的功能已关闭`。让用户去 **Chrome 菜单栏 → View / 查看 → Developer / 开发者 → Allow JavaScript from Apple Events / 允许 Apple 事件中的 JavaScript**，勾上即可。
2. **Chrome 当前已登录微信公众号后台**（任意 tab 打开 `mp.weixin.qq.com` 即可）。CLI 会自动复用已有 session，未登录就只能让用户先去登录一次。
3. **确认目标 Payload 路径**：确保你要发布的文章目录存在且包含 `article.md` 及相关图片。

> ⚠️ 这几条只需在当前会话的**第一次**发布前确认。如果用户之前已经发过，可以假定满足。

## Workflow

### 阶段 1：执行发布命令

确认前置条件后，运行发布工具：

```bash
blogger --payload ./articles/<文章标题目录> --platform wechat,blogger
```

### 阶段 2：监控输出与状态汇报

**监控常见错误**：
- 看输出有无 `WARNING`。
- **看到 `通过 AppleScript 执行 JavaScript 的功能已关闭`**：说明 Prerequisites #1 没满足。让用户去 Chrome 菜单栏开开关，重跑即可。
- **看到 `WeChat Official Account tab not found`**：用户没登录公众号后台。让用户在 Chrome 里登录一次。
- **`Cover Setup` / `Reward Setup` / `Collection Setup` 出现 `Failed to complete within N steps`**：是常态，**正文 + 图片注入通常已经成功**。微信编辑器的弹窗 / 下拉对自动化不够友好，超时不影响主体内容。

**收尾必须给用户一份清单**（即使日志里没有明确的 success summary）：

```
✓ / ✗ 标题
✓ / ✗ 正文（看 "Filled via paste event"）
✓ / ✗ N 张图片（看 "Successfully initiated image paste/upload" 出现次数）
✓ / ✗ 原创声明（看 "Originality badge found"）
✗ 封面 → 让用户在编辑器右侧点「从正文选择」
✗ 合集 → 手动选
✗ 保存为草稿 → 手动点
```

把还需手动补的步骤明确告诉用户，比只说一句"已发送"更负责。
