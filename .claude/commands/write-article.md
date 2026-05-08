---
description: 用 blogger-agent skill 创作并发布一篇中文技术文章
argument-hint: [主题/草稿/目标平台等，可留空]
---

读取并**严格遵守** `skills/blogger-agent/SKILL.md` 的全部内容，按其规定的 5 阶段流程执行：

1. **阶段 1 双重自检**：在回复中先输出【内容质量自检】+【形式自检】并填答完整，主张写不出陈述句不得进入下一步。
2. **阶段 2 视觉资产**：先做 §2.0 素材盘点（用户已发的图优先），再决定是否生成；封面默认 16:9 或 1:1，最后跑 `tools/fit_wechat_cover.py` letterbox。
3. **阶段 3 起草 Markdown**：按阶段 1 选定的文章类型挑骨架（不要默认套"痛点→方案→总结"）。
4. **阶段 4 Pre-flight**：按 AI 腔急救包逐条扫陈词，孤儿图删掉，desc 严格 60–120。
5. **阶段 5 执行发布**：跑 `blogger --payload ./articles/<目录>`，监控 WARNING 与登录态。

不要跳步。SKILL 里写"必须"的地方就是必须。

---

用户本次需求：

$ARGUMENTS
