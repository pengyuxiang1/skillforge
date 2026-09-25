---
status: stable
verified: 2026-09-20
---
# OKF 时效性规范（知识资产的保质期管理）

> 所有会被未来会话消费的知识文件（skill 的经验文档、案例档案、调研结论）都必须带 OKF frontmatter。
> 没有时效标记的知识库 = "看起来可信的过时信息"仓库——AI 检索到两年前失效的 API 地址时，不会自己报警。

## 一、三个字段，一条生命周期

```yaml
---
status: stable        # draft → stable → deprecated
verified: 2026-09-20  # 最后一次人工核对日期
stale_after: 2027-03-20  # 过期日（条件必填，见第三节）
---
```

```
draft ──(人工核对内容属实)──→ stable
  │                              │
  │                     stale_after 到期 → 体检脚本标记过期
  │                              │
  │                     ──(重新核对属实)──→ stable + 更新 verified
  │                              │
  └──(内容被新知识取代)──→ deprecated
        ⚠️ 不物理删除：置 deprecated + 正文顶部链接替代笔记，保留可追溯
```

| 字段 | 必填 | 语义 | 更新规则 |
|------|------|------|---------|
| `status` | 推荐 | `draft`（未核对）/ `stable`（已核对）/ `deprecated`（已废弃） | 核对属实 draft→stable；被取代→deprecated |
| `verified` | 推荐 | 最后人工核对日 | **每次核对后必须更新**——verified 距今越久，可信度越低 |
| `stale_after` | **条件必填** | 内容预计失效日 | 什么内容必标见第三节；不标 = 声明长期有效 |

## 二、verified 与 stale_after 的区别

- `verified` 回答"**上次确认它对**是什么时候"（历史事实）
- `stale_after` 回答"**预计它什么时候开始不对**"（未来预判）
- 两个都新鲜 = 高可信；verified 新但 stale_after 已过 = 该复核了；都旧 = 红灯

## 三、什么内容必须标 stale_after（判断清单）

**必标**（有半衰期的内容）：

| 内容类型 | 估算公式 | 例子 |
|---------|---------|------|
| 外部服务/CDN/第三方依赖 | 3-6 个月 | esm.sh 加载 excalidraw 的方案 |
| Agent 工具名 / hook 语法 | 6 个月（随版本漂移） | "CLI 权威工具名 v2.148.0 实测" |
| API 端点 / URL | 6 个月 | 官方文档地址 |
| 文件路径 / 目录结构 | 6 个月 | 源码文件位置 |
| 版本号相关结论 | 该版本大版本周期 | "0.17.6 的 exportToBlob 行为" |
| 价格 / 配额 / 性能数字 | 3 个月 | "blob 23KB / 20ms 冷启动" |

**不用标**（无半衰期）：算法原理、设计哲学、方法论、协议语义、决策记录（当时为什么这么选，永远成立）。

拿不准时**宁可标**——多标的代价是一次复核，漏标的代价是 AI 拿过期信息干活。

## 四、落地：创建时带、消费时查

**创建时**（skill 生产流程的 Q6 / Stage 5.2 沉淀环节）：
- 每个经验文档、案例档案的 frontmatter 必须含三字段
- 写内容时自查："这段话里有版本号/URL/路径/数字吗？" 有 → 估 stale_after

**消费时**（AI 检索到知识文件的纪律）：
- 先看 frontmatter：`stale_after` 已过 → 内容当"待验证假设"用，标注"此结论可能过期（预计失效于 X），使用前需复核"
- `status: deprecated` → 直接跳到替代笔记，不消费正文
- `verified` 距今超过一年 → 提高警惕，关键操作前实测

## 五、示例

```yaml
---
title: excalidraw 渲染宿主页方案
status: stable
verified: 2026-09-20
stale_after: 2027-03-20   # esm.sh 依赖 + @excalidraw/excalidraw@0.17.6 版本锚定
---

（正文：渲染页用 esm.sh 加载 exportToBlob……）

<!-- 复核清单（stale_after 到期时过一遍）：
  1. esm.sh 还可达吗
  2. 0.17.6 的 exportToBlob 签名变了吗
  3. lz-string 1.5.0 命名导出方式变了吗
-->
```

> 复核清单写进文件尾部注释——到期后核对的人（或 AI）照着清单验，全部通过就更新 verified 并延长 stale_after，不通过就修内容。
