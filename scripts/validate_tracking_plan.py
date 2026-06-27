#!/usr/bin/env python3
"""Tracking Plan 离线体检脚本 / Tracking Plan linter.

对一份填好的 Tracking Plan CSV 做基础校验，作为 CI 的最小起点：
- 事件名命名规范（snake_case、object-action、过去式受控动词、固定字符串）
- 属性命名规范（snake_case、布尔 is_/has_、时间戳 _date/_timestamp）
- 属性类型合法且跨事件一致（同名属性不能时而 number 时而 string）
- 必填列齐全
- 每个事件属性数量上限、事件总数范围
- 大小写漂移导致的近似重名（order_completed vs Order_Completed）

用法:
    python validate_tracking_plan.py path/to/tracking-plan.csv

CSV 需含表头（至少）: event_name, property_name, property_type, property_required
其余列（event_cn, trigger_timing, owner, status, version ...）可选，缺失会给 warning。
退出码 0 = 通过（可能有 warning），1 = 有 error，2 = 用法/读取错误。
"""

import csv
import re
import sys
from collections import defaultdict

SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
# 受控动词词表（事件名最后一段应在此集合内，默认过去式）。可按项目扩充。
CONTROLLED_VERBS = {
    "viewed", "clicked", "submitted", "created", "added", "removed", "updated",
    "deleted", "started", "completed", "cancelled", "canceled", "failed",
    "generated", "sent", "invited", "shared", "searched", "opened", "closed",
    "played", "paused", "subscribed", "loaded", "shown", "selected", "adopted",
}
VALID_TYPES = {"string", "number", "integer", "float", "boolean", "datetime", "timestamp", "date", "array", "object"}
RECOMMENDED_COLS = ["event_name", "event_cn", "trigger_timing", "platform",
                    "property_name", "property_type", "property_required",
                    "metric_served", "owner", "status"]
MAX_PROPS_PER_EVENT = 20
EVENT_COUNT_MIN, EVENT_COUNT_MAX = 10, 200
# 看起来像动态拼接进事件名的 ID/数字片段
LOOKS_DYNAMIC = re.compile(r"_(\d{2,}|[a-f0-9]{6,})$|_p\d+|_u\d+")


def main(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        print(f"[读取失败] {e}")
        return 2

    if not rows:
        print("[空文件] CSV 没有数据行")
        return 2

    errors, warnings = [], []
    cols = set(rows[0].keys())
    for c in RECOMMENDED_COLS:
        if c not in cols:
            warnings.append(f"建议补充列 `{c}`")

    prop_types = defaultdict(set)          # property_name -> {types}
    event_props = defaultdict(list)        # event_name -> [property_name]
    name_by_lower = defaultdict(set)       # lower(event) -> {actual casings}

    for i, r in enumerate(rows, start=2):  # 行号含表头
        ev = (r.get("event_name") or "").strip()
        pn = (r.get("property_name") or "").strip()
        pt = (r.get("property_type") or "").strip().lower()
        req = (r.get("property_required") or "").strip().lower()

        if not ev:
            errors.append(f"第{i}行: event_name 为空")
            continue

        name_by_lower[ev.lower()].add(ev)
        event_props[ev].append(pn)

        # 事件名规范
        if not SNAKE.match(ev):
            errors.append(f"第{i}行: 事件名 `{ev}` 不符合 snake_case")
        else:
            parts = ev.split("_")
            if len(parts) < 2:
                warnings.append(f"第{i}行: 事件名 `{ev}` 不是 object-action 结构（缺动作段）")
            elif parts[-1] not in CONTROLLED_VERBS:
                warnings.append(f"第{i}行: 事件 `{ev}` 的动作段 `{parts[-1]}` 不在受控动词词表内")
        if LOOKS_DYNAMIC.search(ev):
            errors.append(f"第{i}行: 事件名 `{ev}` 疑似拼入了动态 ID/数字——变量应放进属性值，事件名须为固定字符串")

        # 属性规范
        if pn:
            if not SNAKE.match(pn):
                errors.append(f"第{i}行: 属性名 `{pn}` 不符合 snake_case")
            if pt and pt not in VALID_TYPES:
                errors.append(f"第{i}行: 属性 `{pn}` 类型 `{pt}` 非法（合法: {sorted(VALID_TYPES)}）")
            if pt:
                prop_types[pn].add(pt)
            if pt == "boolean" and not (pn.startswith("is_") or pn.startswith("has_")):
                warnings.append(f"第{i}行: 布尔属性 `{pn}` 建议以 is_/has_ 开头")
            if pt in {"datetime", "timestamp", "date"} and not (pn.endswith("_timestamp") or pn.endswith("_date") or pn.endswith("_at")):
                warnings.append(f"第{i}行: 时间属性 `{pn}` 建议以 _timestamp/_date/_at 结尾")
            if req and req not in {"true", "false", "是", "否", "1", "0"}:
                warnings.append(f"第{i}行: property_required `{req}` 建议用 true/false")

    # 跨行一致性检查
    for pn, types in prop_types.items():
        if len(types) > 1:
            errors.append(f"属性 `{pn}` 类型不一致: {sorted(types)} —— 同名属性类型必须稳定")

    for low, variants in name_by_lower.items():
        if len(variants) > 1:
            errors.append(f"事件名大小写漂移（会被平台当成不同事件）: {sorted(variants)}")

    for ev, props in event_props.items():
        real = [p for p in props if p]
        if len(real) > MAX_PROPS_PER_EVENT:
            warnings.append(f"事件 `{ev}` 有 {len(real)} 个属性，超过建议上限 {MAX_PROPS_PER_EVENT}")

    n_events = len(event_props)
    if n_events < EVENT_COUNT_MIN:
        warnings.append(f"事件总数 {n_events} < {EVENT_COUNT_MIN}，可能不足以支撑漏斗分析")
    elif n_events > EVENT_COUNT_MAX:
        warnings.append(f"事件总数 {n_events} > {EVENT_COUNT_MAX}，维护成本偏高，考虑用属性合并")

    print(f"=== Tracking Plan 体检: {path} ===")
    print(f"事件数: {n_events}  数据行: {len(rows)}\n")
    if errors:
        print(f"❌ ERROR ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"\n⚠️  WARNING ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    if not errors and not warnings:
        print("✅ 全部通过，没有发现问题。")
    elif not errors:
        print("\n✅ 没有 error（仅 warning），可放行。")

    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
