# 案例：excalidraw-draw（渲染验证版画图 skill）

> 生产日期：2026-09-20 ｜ 形态：**轻量 skill + 渲染门禁 hook（无状态机/无引导脚本的混合形态）**

## 一、工作流

生成 Excalidraw 图（Obsidian md / 标准 / 动画三模式）：需求分类 → 深度评估（概念图 vs 技术图）→ 概念→视觉模式映射 → 坐标规划 → 生成 JSON → **渲染验证闭环** → 落盘 Obsidian。

## 二、形态决策（本案例最重要的方法论）

**不是所有带 hook 的 skill 都要完整超级 skill 五件套。** 决策过程：

| skillforge 判定 | 本案例答案 | 推论 |
|--------------------------|-----------|------|
| Q3 跨会话？ | ❌ 图文件本身即产物状态 | 不需要状态文件 + 引导脚本 |
| Q5 硬标准？ | ✅ 渲染验证不可跳过 | 需要 hook |
| 循环结构？ | ✅ 生成→渲染→修复循环 | 由 hook 的收敛拉回实现，无需状态机 |

结论：**轻量 skill（SKILL.md + references + scripts）+ 1 个 PostToolUse 门禁 hook**。跳过了 Stage 2/3——"先判断再动手"意味着砍掉不需要的阶段也是正确产出。

## 三、门禁 hook 的收敛式拉回（新方法论）

**"continue:false 拉回"与"循环风险"的调和**：PostToolUse 返回 `{continue: false, reason}` 会注入消息让 Agent 继续工作，有无限循环担忧。本案例的解法——**脚本内判定收敛条件**：

- 机器检测通过（exit 0）→ 放行 `{}`（循环出口）
- 有问题（exit 1）→ `{continue: false, reason: 具体问题列表}` 拉回修复
- 问题修完 → 自然放行，循环收敛

机器检测项本身就是收敛条件的判定器（锚点/ID 唯一/字号/重叠/越界——全部可确定性计算）。**"硬标准必须能机器校验"在这里不只是 hook 能不能拦的问题，而是循环能不能收敛的问题**。

## 四、新坑（研读上游源码才发现）

1. **Obsidian Excalidraw 插件默认压缩保存**：AI 生成明文 ```json 的图，用户在 Obsidian 里一打开保存就变 ```compressed-json（LZString.compressToBase64）。**读取用户编辑过的图必然遇到压缩格式**，工具链必须支持解压（解压前须剔除插件每 256 字符插入的 `\n\n`——源码 sceneDataUtils.ts 证实）。
2. **esm.sh 的 lz-string 是命名导出**：`import { decompressFromBase64 } from "esm.sh/lz-string&exports=decompressFromBase64"`，不是 `{ LZString }` 对象。
3. **AI 盲画图翻车率极高**：文字偏移/元素重叠/箭头悬空在 JSON 里完全看不出来。渲染验证闭环（exportToBlob → PNG → Read 看图）是唯一可靠的质量兜底，实测第一张真实图就跑了 2 轮微调。

## 五、技术栈（可复用）

| 组件 | 实现 | 备注 |
|------|------|------|
| 渲染 | playwright + 本地 HTML 宿主页 + esm.sh 的 `@excalidraw/excalidraw` `exportToBlob` | 纯函数 API 无需挂载 React；网络依赖仅在渲染，机器检测零依赖 |
| 解压 | 渲染页同加载 `lz-string` 暴露 `decompressExcalidraw` | 复用 playwright，Python 零新依赖（pip 无 lz-string 包） |
| 机器检测 | 纯 Python：锚点正则/ID 去重/字号阈值/AABB 重叠（背景层按 opacity≤50 与面积比排除） | exit 0/1/2 = 通过/有问题/脚本异常 |
| 门禁 | `.codebuddy/hooks/excalidraw-render-gate.js`（PostToolUse） | 两层过滤 + fail-open + `EXCALIDRAW_GATE_OFF` 开关 |

## 六、遗留

- ExcalidrawAutomate（Obsidian 插件脚本接口）经 osb eval 调用 `ea.create()` 报错（疑似需要活跃 Excalidraw 视图），未深究——playwright 方案已够用，留作未来离线渲染的探索方向
- 渲染依赖 esm.sh 网络；若需完全离线，可把 excalidraw UMD/ESM bundle 缓存进 skill assets
