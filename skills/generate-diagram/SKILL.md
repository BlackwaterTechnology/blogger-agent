---
name: generate-diagram
description: Use when the user requests to generate, create, redraw, or render technical diagrams, architecture topology, state machines, sequence pipelines, trade-off matrices, terminal slices, or 6 professional visual card modes from technical concepts, code, or article sections, or explicitly invokes /generate-diagram.
---

# Generate Diagram Skill (专业技术图表与系统建模)

## Overview

本 Skill 专门负责**高精度、高信息密度、确定性的专业技术图表与系统建模可视化**交付。

将软件工程的 **UML 建模思维**（类图、时序图、状态图、部署图、权衡矩阵、性能跟踪）与移动端信息架构（IA）深度融合。坚决杜绝用 ASCII 字符画替代图表，杜绝把文字机械塞进色块方框中。

无论是长文插图、小红书/小绿书 3:4 竖版卡片，还是单图重构，均产出生产级的高清 PNG 及可编辑 SVG 源码。

---

## 🎨 6 大专业表现模式决策树与 UML 映射

制图前，**必须且只能**先分析信息拓扑本质，从 6 大专业表现模式中匹配最优形态：

| 表现模式 | UML / 软件工程映射 | 解决的认知痛点 | 适用技术场景与特征 | 核心视觉组件 |
|---|---|---|---|---|
| **1. 便当盒网格 (Bento Spec)** | 类图 / 对象规约 | 静态参数离散、难以快速提取核心属性 | 实体规格、参数配比、多维能力总览（高内聚、模块化展示静态属性与约束） | 紧凑网格 (Grid)、Pill 胶囊标签、Key-Value 键值对、对比指标 |
| **2. 垂直时序管道 (Causal Pipeline)** | 活动图 / 顺序图 | 动态因果链条推演冗长、故障链不直观 | 故障扩散链路、端到端请求时序、多步实施步骤（1➔2➔3➔4 递进、阶段状态色阶、触发点箭头） | 垂直贯穿导引线、阶段序号、触发点与后果、警示色阶递进 |
| **3. 二元对抗/四象限 (Trade-off Matrix)** | 决策分支 / ATAM 权衡 | 选型纠结、难以洞察反模式代价 | 新旧范式对抗（❌旧模式 vs ✅新模式）、2x2 成本/复杂度四象限 | 左右红绿双栏、决策分水岭、象限坐标轴、对比结论条 |
| **4. 系统拓扑边界 (Topology Map)** | 部署图 / 组件依赖图 | 局部割裂、缺乏空间与容器边界感 | 架构全景、网络组网、容器包含关系（VPC > Subnet > Node > Pod） | 嵌套虚线容器盒、总线通信连线、协议标注（HTTP/gRPC/Kafka） |
| **5. 状态机闭环 (State Machine)** | 状态机图 (Statechart) | 状态流转不清、异常处理与重试遗漏 | 控制循环（Reconcile）、健康检测、退避重试回路、生命周期 | 圆角状态节点、带守卫条件 [Guard] 箭头、异常回路、终止态 |
| **6. 实证量化/终端切片 (Trace & Benchmark)** | 性能画像 / 执行跟踪 | 纯理论推演缺乏实操证据与信服力 | 真实终端报错还原、CLI 命令切片、压测剪刀差折线图、基准对比 | 拟真 macOS 终端三色窗口、Monospace 代码高亮、坐标轴曲线 |

*辅助增强模态：具象概念隐喻 (Conceptual Metaphor)*：对标 DDD 领域概念模型。用于封面爆破 Hook 破冰或抽象概念降维（如天平倾斜表达调度失衡）。环境具备且用户需要时通过 `generate_image` 生成去 AI 味的高审美社论插画。

---

## 📐 3 大标准画布规格与版式规范

根据交付场景，严格选择对应的画布比例：

1. **移动端长文正文插图（默认 1200px 宽）**：
   - 首选 **4:3 (`1200 x 900`)** 或 **3:2 (`1200 x 800`)**；
   - 复杂双轨复合图或纵向管道可使用纵向流（`1200 x 1000 ~ 1220`）；
   - **严禁使用 16:9 超扁平横图作为正文核心机制图**（在手机端缩放后高度过矮、字号极小）。
2. **小红书 / 微信图片消息卡片（严格 3:4 竖版）**：
   - 统一采用 `<svg viewBox="0 0 1200 1600" width="1200" height="1600">`；
   - 遵循 Header（大标题+副标题）+ Body（拓扑/状态机/管道）+ Footer（Takeaway 横条）三段式架构。
3. **文章封面图（16:9 宽屏）**：
   - 统一采用 `1200 x 675` 或 `1920 x 1080`；
   - 核心视觉与文字严格收敛在中央 60% 安全区，防止平台裁切正方形时关键内容丢失。

---

## 📱 移动端字号硬底线与排版铁律 (CRITICAL)

在手机（360px 宽度）阅读时，源图文字会按 `源字号 × 360 / 源画布宽度` 发生等比缩放：
- **字号绝对底线**：在 1200px 源画布中，**全图文字绝对禁止低于 28px**（缩放后约 8.4px 为阅读极限）：
  - 核心大标题：`44px ~ 54px`（粗体加重）
  - 卡片主标题 / 核心阶段：`32px ~ 40px`
  - 正文说明 / 节点描述：`28px ~ 32px`
  - 标签 / 辅助微型文字：不低于 `24px ~ 26px`
- **横向分栏上限（最多 2 栏）**：手机竖屏严禁横排 3 栏或 4 栏！多步骤时序必须采用垂直单向流动（Top-to-Bottom）。
- **极简短语化**：每个节点严格限制在 2~3 行文字以内（每行 8~14 字），严禁在图内塞入整段长篇大论。
- **禁绝 ASCII 字符画**：严禁在正文中使用 `┌─┐`、`│`、`└─┘` 等字符方框代码块。

---

## 🛠️ 标准实施工作流 (Workflow)

### 阶段 1：信息拓扑分析与模式判定
明确待表达的技术关系本质：
- 是静态属性（选 Bento 网格）？
- 是故障传播（选 Causal Pipeline）？
- 是方案选型（选 Trade-off Matrix）？
- 是服务组网（选 Topology Map）？
- 是生命周期回路（选 State Machine）？
- 还是实测命令行输出（选 Terminal Slice）？

### 阶段 2：选择画布画幅与主题色板
- 确定画幅（长文 1200x900 / 画册 1200x1600 / 封面 1200x675）；
- 选择一套主题色（默认 `slate_navy`：深曜蓝 `#0F172A`、琥珀金 `#F59E0B`、天蓝 `#38BDF8`、薄荷绿 `#10B981`、告警红 `#EF4444`）。

### 阶段 3：编写原生 SVG 代码
参考 [SVG 组件模板库](references/svg-templates.md)，编写结构清晰、分层明确的原生 SVG，保存至目标目录（如 `target.svg`）。

### 阶段 4：高画质渲染导出
使用 macOS 原生 `sips` 导出 1920px Retina 级 PNG：
```bash
# 长文插图导出
sips -s format png --resampleWidth 1920 target.svg --out target.png

# 3:4 画册卡片导出
sips -s format png --resampleWidth 1200 target.svg --out target.png
```

### 阶段 5：极验与交付
- 运行 `sips -g pixelWidth -g pixelHeight target.png` 检查尺寸；
- 检查移动端字号折算（确保无 <28px 小字，无边缘截断）；
- 正文中以 `![精准描述图意](target.png)` 正式嵌入。
