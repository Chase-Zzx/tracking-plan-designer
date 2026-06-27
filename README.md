# tracking-plan-designer

一个 [Claude Skill](https://docs.claude.com/en/docs/claude-code/skills)，用于**设计和落地一套用户行为数据监测 / 数据埋点体系**。

它不会一上来就甩给你一堆「要埋的事件」，而是带你从**业务目标反推**到可落地的埋点方案：

```
业务目标 (North Star) → 用户旅程 (UJM) → 指标 (OSM/HEART) → 事件 (Event) → 埋点方案 (Tracking Plan) → QA / 数据治理
```

最终交付一份可直接给研发执行的 **Tracking Plan（埋点方案 / 事件字典）**，并附命名规范、QA 清单与治理机制。

## 何时会触发

当你问 Claude 这类问题时会自动启用：

- 「一个网站/App 要怎么监测用户行为？」「怎么搭建数据监测体系？」
- 「帮我设计一套埋点方案 / 事件模型」
- 「指标体系 / 北极星指标 / OSM / 用户旅程怎么做？」
- 「神策 / GrowingIO / Amplitude / Mixpanel / GA4 / 数数 怎么埋点？」
- 涉及 event taxonomy、tracking plan、analytics instrumentation、漏斗 / 留存 / 归因 / 分群 的设计问题。

## 核心理念

- **从「为什么」开始，不从「埋什么」开始**——先埋点后想用途必然泛滥失控。
- **算不出来的指标是空的；采不到指标的事件是冗余的。**
- 基于 **Event–Property–User** 事件模型（与神策/GrowingIO/Amplitude/Mixpanel/GA4 同一抽象）。
- 命名规范先行（object-action、固定字符串、变量进属性）。
- 把埋点**当代码来治理**：有 owner、有 schema、有迁移、有 CI 校验。

## 目录结构

```
tracking-plan-designer/
├── SKILL.md                          # 主流程与心法
├── references/
│   ├── methodology.md                # North Star / OSM / UJM / HEART / AARRR
│   ├── event-model.md                # Event/Property/User、identify、客户端 vs 服务端
│   ├── naming-conventions.md         # 命名规范、属性规则、平台硬限制、正反例
│   └── governance-qa.md              # QA 清单、数据质量监控、生命周期与治理
├── assets/
│   └── tracking-plan-template.csv    # 事件字典 / Tracking Plan 交付模板
└── scripts/
    └── validate_tracking_plan.py     # Tracking Plan 命名/必填/类型一致性体检脚本
```

## 安装

把整个目录放进 Claude 的 skills 目录即可：

```bash
git clone https://github.com/<your-account>/tracking-plan-designer.git \
  ~/.claude/skills/tracking-plan-designer
```

（项目级安装可放在 `<project>/.claude/skills/`。）

## 体检脚本用法

填好 Tracking Plan CSV 后，可离线校验命名规范、必填项与类型一致性：

```bash
python3 scripts/validate_tracking_plan.py your-tracking-plan.csv
```

退出码：`0` 通过（可能有 warning）/ `1` 有 error / `2` 用法或读取错误。可直接接入 CI。

## 致谢

方法论综合自神策、GrowingIO、Amplitude、Mixpanel、PostHog、GA4 等主流分析体系的公开最佳实践。
