# 事件模型深入：Event / Property / User

承接 SKILL.md 的「底层数据模型」与工作流程第 4、6 步。这里讲清楚事件模型的几个容易踩坑的细节。

## 目录
- [1. 三要素与一条完整事件长什么样](#1-三要素)
- [2. 事件属性 vs 用户属性](#2-事件属性-vs-用户属性)
- [3. `$set` vs `$set_once`：别覆盖掉获客来源](#3-set-vs-set_once)
- [4. 用户标识与 identity stitching](#4-用户标识)
- [5. 多个事件 vs 一个事件 + 属性](#5-多个事件-vs-一个事件--属性)
- [6. 客户端采集 vs 服务端采集](#6-客户端采集-vs-服务端采集)
- [7. 公共属性 / Super Properties](#7-公共属性)

---

## 1. 三要素

一条完整事件应包含：**谁（User）+ 何时（timestamp）+ 做了什么（Event）+ 在什么上下文（Property）**。

示例（一条 `order_completed`）：
```json
{
  "event": "order_completed",
  "distinct_id": "u_88231",
  "time": "2026-06-26T10:12:03+08:00",
  "properties": {
    "order_id": "o_55012",
    "amount": 199.00,
    "currency": "CNY",
    "payment_type": "alipay",
    "item_count": 2,
    "is_first_order": true,
    "source_channel": "wechat_ad",
    "platform": "ios",
    "app_version": "5.3.1"
  }
}
```

## 2. 事件属性 vs 用户属性

- **事件属性（Event Property）**：描述「这一次动作」的上下文，随事件走。如 `payment_type`、`item_count`、`page`。
- **用户属性（User Property）**：描述「这个人」的持续特征，挂在用户身上、对其后续所有事件生效，直到被改写。如 `member_level`、`register_channel`、`city`、`lifetime_orders`。

判断：如果同一个人在不同事件里这个值应该一致，它多半是用户属性；如果每次动作可能不同，它是事件属性。

## 3. `$set` vs `$set_once`

更新用户属性时有两种语义，混用会污染数据：
- **`$set`（覆盖）**：每次写入覆盖旧值。用于会变的属性：当前会员等级、最近城市、累计订单数。
- **`$set_once`（仅首次）**：只在第一次写入时生效，之后忽略。用于**不可变的获客信息**：注册渠道、首次来源、注册日期、首单时间。

经典 bug：用 `$set` 写「来源渠道」，结果用户每次新会话都把最初的获客渠道覆盖掉，归因彻底失真。获客类一律用 `$set_once`。

## 4. 用户标识

跨设备 / 登录前后把同一个人拼起来，靠的是 identity stitching：
- **匿名期**：用设备/匿名 ID（anonymous_id）记录登录前行为。
- **登录后**：调用 `identify()` 把匿名 ID 与真实用户 ID 关联。

两个静默杀手：
- 首屏没调用初始化 → 丢失登录前行为。
- 登录时没调用 `identify()` → 登录用户和它的匿名身份分裂成两个人，分群、漏斗全错。

规则：**首次加载时调用一次，登录成功后再调用一次**。这类错误不会报错，但会产出错误的人群，务必在 QA 阶段专门验证。

## 5. 多个事件 vs 一个事件 + 属性

默认**优先「一个事件 + 属性区分」**：
- ✅ 一个 `order_completed`，用 `payment_type ∈ {alipay, wechat, card}` 区分。
- ❌ 三个事件 `order_completed_alipay` / `order_completed_wechat` / `order_completed_card`。

原因：统一事件做整体漏斗、整体转化率时口径一致，需要细分时按属性切片即可；拆成多个事件会让漏斗分析必须把它们手动合并，且事件数量爆炸。

什么时候才该拆成不同事件：动作本身在**业务语义和后续分析路径上确实不同**（如 `product_viewed` 和 `product_added` 是两个不同动作，不能合并）。区分原则：同一个动作的不同「风味」→ 用属性；不同的动作 → 用不同事件。

## 6. 客户端采集 vs 服务端采集

| 维度 | 客户端埋点 | 服务端埋点 |
|---|---|---|
| 覆盖动作 | UI 交互、曝光、点击 | 业务结果、支付、订单状态 |
| 可靠性 | 会被广告/隐私拦截吞掉一部分（业内估计 25–40%）、受弱网影响 | 高，落库即真实 |
| 业务属性 | 前端能拿到的有限 | 可拼接完整业务数据 |
| 实现成本 | 前端改动 | 后端改动 |

**推荐混合**：
- 全埋点 / 客户端打底拿基础点击流与曝光；
- 核心 KPI（注册、支付、收入、风控相关）走服务端代码埋点保证准确；
- 对收入等最关键事件可**客户端 + 服务端双采**做交叉校验——但要用**不同事件名**（如 `order_completed_client` / `order_completed_server`）或加 `source` 属性，避免重复计数。

## 7. 公共属性（Super Properties）

把每条事件都需要的上下文统一在一个 analytics 封装层里自动注入，避免每个埋点点各写一遍、写漏写错：
- 环境：`env`（prod/staging）、`app_version`、`platform`、`os_version`、`device_model`。
- 会话：`session_id`、`network_type`。
- 身份：`distinct_id`、`is_login`。

好处：口径统一、漏注风险低、出问题时好排查。这一层也是 QA 与治理的抓手（见 `governance-qa.md`）。
