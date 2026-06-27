# 命名规范与属性规则

命名规范必须在写第一个事件之前定好并全程统一，否则数据一定漂移。本文件是工作流程第 5 步的细则。

## 目录
- [1. 事件命名：object-action 四轴](#1-事件命名object-action-四轴)
- [2. 受控动词词表](#2-受控动词词表)
- [3. 最重要的一条铁律：事件名是固定字符串](#3-铁律事件名是固定字符串)
- [4. 属性命名规则](#4-属性命名规则)
- [5. 正反例](#5-正反例)
- [6. 平台硬限制（GA4 等）](#6-平台硬限制)
- [7. 规模约束](#7-规模约束)

---

## 1. 事件命名：object-action 四轴

业界标准是 **object-action（对象在前、动作在后）**，因为它让相关事件在字典里按对象聚类、好检索，且命名决策快、不易重名。四个轴各选一种并全程统一：

1. **大小写（Casing）**：`snake_case` / `camelCase` / `Title Case` 选一种。平台会把 `Song Played` 和 `song played` 当成两个不同事件，混用即碎裂。**推荐 `snake_case`**。
2. **格式（Format）**：`[对象]_[动作]` 或 `[上下文]_[对象]_[动作]`。对象在前，便于聚类。
3. **时态（Tense）**：过去式（`product_viewed`）或一般式（`product_view`）选一种。**推荐过去式**，读起来就是「已发生的动作」。
4. **受控词表（Controlled vocabulary）**：动词只能从一个批准的列表里选（见下），杜绝 `click` / `tap` / `press` 同义乱用。

推荐组合：`snake_case` + `[对象]_[动作]` + 过去式，例如 `product_viewed`、`checkout_started`、`order_completed`。

## 2. 受控动词词表

把动作动词限定在一个小集合内（可按需增删，但要登记）。参考集合：

```
viewed / clicked / submitted / created / added / removed / updated / deleted /
started / completed / cancelled / failed / generated / sent / invited /
shared / searched / opened / closed / played / paused / subscribed
```

新增动词前先确认现有词表里没有等价词，避免 `viewed` 与 `displayed` 并存。

## 3. 铁律：事件名是固定字符串

**事件名和属性名必须是源代码里的固定字符串字面量，绝不能在运行时动态拼接。**

变量数据（用户 ID、商品名、页面标题、分类名）只能进**属性值**，绝不能进事件名/属性名。

- ✅ `product_viewed` + `{ "product_id": "p_123", "category": "shoes" }`
- ❌ `product_viewed_p_123`、❌ `viewed_shoes`

原因：一旦把变量拼进事件名，就制造了一个**无限命名空间**——事件清单会爆炸到成千上万、没有任何 Tracking Plan 能治理、所有按事件名做的分析全部失效。

## 4. 属性命名规则

- **格式**：`object_adjective` / 名词短语，`snake_case`。如 `user_id`、`item_price`、`source_channel`、`member_count`。
- **布尔值**：以 `is_` 或 `has_` 开头。如 `is_subscribed`、`is_first_order`、`has_seen_upsell`。
- **时间 / 时间戳**：以 `_date` 或 `_timestamp` 结尾。如 `signup_date`、`paid_at_timestamp`。
- **金额**：带上单位/币种约定，配 `currency` 属性，金额用数值类型而非字符串。
- **跨事件一致性**：同一个含义在所有事件里用**同一个属性名和同一种类型**。要用 `item_type` 和 `payment_type`，不要到处用泛泛的 `type`。
- **类型稳定**：一个属性一旦定为数值，就永远是数值。同名属性一会儿发数字、一会儿发字符串，会污染整个序列（type mutation），是最常见的脏数据来源之一。
- **漏斗覆盖**：做漏斗要用的关键属性，要在漏斗涉及的**每一个**事件里都带上。例如 `product_id` 要同时出现在 `product_viewed` 和 `product_added` 上，否则漏斗串不起来。
- **控制基数（cardinality）**：不要把全 URL、自由文本输入等高基数原始值直接当属性灌进去（会撑爆分析、拖慢查询）。需要时先归一化/截断/分桶。

## 5. 正反例

| 场景 | ❌ 反例 | ✅ 正例 |
|---|---|---|
| 点击按钮 | `btnClick`、`click_buy_now` | `button_clicked` + `{button_name: "buy_now"}` |
| 浏览商品 | `view_product_p123` | `product_viewed` + `{product_id: "p123"}` |
| 支付方式 | 三个事件 `pay_alipay`/`pay_wechat`/... | `order_completed` + `{payment_type: "alipay"}` |
| 布尔属性 | `subscribed: "yes"` | `is_subscribed: true` |
| 时间属性 | `time: "2026/6/26"` | `signup_date: "2026-06-26"` |
| 大小写混用 | `Order_Completed` 与 `order_completed` 并存 | 全项目统一 `order_completed` |

## 6. 平台硬限制

落地前确认目标平台的限制，避免方案无法实现。以 **GA4** 为例：
- 事件名 ≤ 40 字符，大小写敏感，必须以字母开头，只能含字母/数字/下划线。
- 不能以 `ga_`、`firebase_`、`google_`、`gtag.` 开头（保留前缀）。
- 每个事件 ≤ 25 个参数。
- 事件级自定义维度 ≤ 50；App 数据流每个用户的不同事件名 ≤ 500。

神策 / GrowingIO / Amplitude / Mixpanel 各有自己的保留字段（多以 `$` 开头）与上限，方案定稿前查一遍对应平台文档。

## 7. 规模约束

- 一份 Tracking Plan：**10–200 个事件**。少于 10 难做漏斗，多于 200 没人维护。
- 每个事件：**≤ 约 20 个属性**（GA4 为 25 个参数上限）。
- 超出多半意味着该「用属性区分」却「拆成了多个事件」，或反过来——回到 `event-model.md` 第 5 节重新取舍。
