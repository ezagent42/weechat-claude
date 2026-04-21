---
name: handle-review-command
description: Use when admin types `/review [yesterday|today|week]` or asks for KPIs / CSAT / 接管率 / 升级转结案率 / 报告. Calls run_zchat_cli audit report --json and formats aggregate metrics.
---

# Handle /review Command

## When
- `/review`, `/review yesterday`, `/review today`, `/review week`
- 自然语言: "今日 CSAT 怎样", "看看本周指标", "运营报告"

## Steps
1. **取数**：
   ```
   rc, out, err = run_zchat_cli(args=["audit", "report", "--json"])
   ```
   （window 参数若 CLI 支持可加，目前 audit report 只暴露聚合视图）

2. **解析 + 格式化**：
   ```
   reply(chat_id="#<my admin channel>", text="""
   <周期> 统计：
   - 接管次数: <takeovers>
   - 已结案: <resolved>
   - 升级转结案率: <escalation_to_resolve_rate>
   - CSAT 均分: <csat_avg>（<csat_count> 条评分）
   """)
   ```

## 反模式
- ❌ 把 audit report 的 raw JSON 输出给管理员
- ❌ 自己估算指标（直接读 `aggregates` 字段，别算）
