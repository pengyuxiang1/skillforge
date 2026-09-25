# 案例库索引

已沉淀的超级 skill 生产案例。**新增案例必须在此登记**，否则下次找不到。

| 案例 | 工作流 | 状态数 | 引导脚本 | 门禁 hook | 沉淀日期 |
|------|--------|--------|---------|----------|---------|
| [question-diagnosis](question-diagnosis.md) | 问题定位（假设-验证循环） | 5 | ✅ `flow_guide.py` | ✅ `diagnosis-gate.js` | 2026-09-10 |
| [excalidraw-draw](excalidraw-draw.md) | 画 Excalidraw 图（渲染验证闭环） | 0（无状态机） | ❌ | ✅ `excalidraw-render-gate.js` | 2026-09-20 |

## 快速检索

**按方法论找**：
- hook 条件判断而非插拔 → [question-diagnosis](question-diagnosis.md) 三-新方法论 1
- 引导钉在状态文件顶部 → [question-diagnosis](question-diagnosis.md) 三-新方法论 2
- 判定标准可机器校验 → [question-diagnosis](question-diagnosis.md) 三-新方法论 3
- 轻量 skill + hook 的混合形态（跳过状态机的决策依据） → [excalidraw-draw](excalidraw-draw.md) 二
- 收敛式拉回（continue:false 的循环出口设计） → [excalidraw-draw](excalidraw-draw.md) 三

**按坑找**：
- 工具名想当然 / matcher 锚点 / 废弃 API → [question-diagnosis](question-diagnosis.md) 三-新坑
- 解析器漏判（只扫一种格式） → [question-diagnosis](question-diagnosis.md) 三-新坑
- 上游默认压缩保存（读用户文件必须先解压） → [excalidraw-draw](excalidraw-draw.md) 四-坑1
- AI 盲产出无法自检（必须渲染/执行看结果） → [excalidraw-draw](excalidraw-draw.md) 四-坑3

**按可复用模板找**：
- 引导脚本的宽松解析 + 缺口检测 → `scripts/flow_guide.py`
- 门禁脚本的两层过滤 + fail-open → `.codebuddy/hooks/diagnosis-gate.js`
- 状态文件顶部引导指令块 → `templates/task.md`
- 渲染验证闭环（playwright + exportToBlob + 机器检测） → `skills/excalidraw-draw/scripts/render_check.py`

## 登记格式

```markdown
| [案例名](文件名.md) | 工作流一句话 | 状态数 | ✅/❌ 脚本名 | ✅/❌ hook名 | YYYY-MM-DD |
```

并在「快速检索」节补上新增的方法论/坑/模板入口。
