---
status: stable
verified: 2026-09-20
stale_after: 2027-03-20
---
# hook 设计规范

## 目录

0. 零、先确认目标 Agent（写 hook 前必做）
1. 一、什么时候需要 hook
2. 二、核心机制：hook 常挂，脚本内判断
3. 三、三个必验的坑
4. 四、成本控制
5. 五、必须遵守的四条
6. 六、配置结构
7. 七、测试方法（必须做）


Stage 4 门禁 hook 的实现依据。**动手前必读三个坑，每个都会导致"门禁看起来在工作、实际从未生效"。**

## 零、先确认目标 Agent（写 hook 前必做）

**hook 语法不通用。** 三家各有一套，照搬会静默失效。

### 第一步永远是问用户：你在用哪个 Agent？

| Agent | Hook 官方文档 | 配置文件位置 | 格式 |
|-------|-------------|-------------|------|
| **CodeBuddy** | `https://www.codebuddy.cn/docs/cli/hooks` | 项目 `.codebuddy/settings.json`<br>用户 `~/.codebuddy/settings.json` | JSON |
| **Claude Code** | `https://code.claude.com/docs/zh-CN/hooks`<br>（**加 `.md` 后缀**可得纯 markdown，省 token） | 项目 `.claude/settings.json`<br>用户 `~/.claude/settings.json` | JSON |
| **Codex** | `https://learn.chatgpt.com/docs/hooks`<br>（**加 `.md` 后缀**可得纯 markdown） | 用户 `~/.codex/hooks.json` 或 `~/.codex/config.toml`<br>项目 `<repo>/.codex/hooks.json` 或 `.codex/config.toml` | **JSON 或 TOML**（两种都支持，同一层别混用） |

### 第二步：查官方文档（写 hook 前必做）

**查询顺序**：

1. 打开上面对应 Agent 的官方文档（优先加 `.md` 后缀，拿纯 markdown）
2. 地址不可访问 → `web_search` 搜「`<Agent名> hooks 官方文档`」
3. 把关键页（事件列表 / matcher 语义 / 输入输出 schema / 废弃说明）**抓下来存进本仓库 `references/hooks-ref/`**，作为你的本地快照（见该目录 README）
4. 按**该 Agent 的语法**写，写完在本机跑一次验证（模拟输入，看返回值）

**为什么必须查**（都是实测踩过的）：

- **字段会废弃**。CodeBuddy 的 `decision: "block"` 三处已标注废弃，PreToolUse 现在要用 `hookSpecificOutput.permissionDecision`，Stop 要用 `continue: false` 或 `systemMessage`。照记忆写出来的配置会被静默忽略。
- **事件集差异大**。Claude Code 有 30 个事件，CodeBuddy 和 Codex 各有一套。
- **matcher 支持范围不同**。Codex 的 `Stop` / `UserPromptSubmit` / `Interrupt` **不支持 matcher**，配了也被忽略。
- **Codex 有 trust 机制**。非托管 hook 要人工 review + trust 才会运行（`/hooks` 命令），写完不 trust 等于没写。

### 已知差异（2026-09-14 实抓核实，动手前仍需查最新）

| 维度 | CodeBuddy | Claude Code | Codex |
|------|-----------|-------------|-------|
| 配置格式 | JSON | JSON | JSON（`hooks.json`）或 TOML（`config.toml` 内联 `[hooks]`） |
| 配置结构 | 事件 → `[{matcher, hooks[]}]` | 事件 → matcher 分组 → hook 列表 | 事件 → matcher 分组 → hook handlers[] |
| matcher 语义 | 正则 `new RegExp(m).test(name)` | 正则 | 正则（`"*"` / `""` / 省略 = 匹配所有） |
| matcher 支持 | PreToolUse / PostToolUse | 多数事件 | **部分**（`Stop`/`UserPromptSubmit`/`Interrupt` 不支持） |
| 写文件工具名 | `Edit` / `Write` / `MultiEdit` / `NotebookEdit` | 需查文档 | `apply_patch`（也可用 `Edit` / `Write` 匹配） |
| PreToolUse 阻断 | `hookSpecificOutput.permissionDecision` | 查文档 | 查文档（另有 `PermissionRequest` 事件） |
| Stop 阻断 | `{continue: false, reason}` | 查文档 | `{continue: false, stopReason}` |
| Stop 仅提醒 | `{systemMessage}` | 查文档 | `{systemMessage}` |
| 额外门槛 | — | — | **非托管 hook 需 review + trust** |

> ⚠️ 本 skill 的**具体代码示例**以 CodeBuddy 为准（实测过）。给其他 Agent 写时，**结构可以照搬，语法必须按目标文档改写并验证**。

### 本地快照（你自己的兜底）

`references/hooks-ref/` 初始只含说明文档：官方文档快照因版权与时效原因**不随仓库分发**，需要时按上面第二步自行抓取存入。三家建议各存一份 `{agent}.md`，断网时兜底。

## 一、什么时候需要 hook

| 约束类型 | 需要 hook？ | 原因 |
|---------|-----------|------|
| **负面约束**（不许做 X） | ✅ **必须** | 提醒对负面约束无效，AI 会做 |
| **正面引导**（该做 X） | ⚠️ 可选 | 引导脚本已能覆盖，hook 是兜底 |
| **硬标准**（必须达成 Y） | ✅ 需要 | 如"证据必须有出处" |

**判断口诀**：能靠"告诉 AI 该做什么"解决的，不用 hook；必须"阻止 AI 做某事"的，才用 hook。

## 二、核心机制：hook 常挂，脚本内判断

**常见误解**：A 阶段要拦、B 阶段不要，是不是要动态插拔配置？

**正确做法**：hook 常挂，由脚本内部读状态文件判断这次拦不拦。

```
第一层（配置层 matcher）  → 只对特定工具触发（粗过滤）
        ↓ 命中
第二层（脚本内判断）      → 读状态文件，按阶段决定拦/放行（业务判断）
```

配置层的 matcher **只能匹配工具名**，匹配不了"现在是不是规划阶段"这种业务语义。所以业务判断必须落在脚本里。

**源码证据**（codebuddy bundle 内 `matchesTool`）：

```js
matchesTool(matcher, name) {
  if (!matcher) return true;        // 空 matcher = 匹配所有
  if (!name) return false;
  try { return new RegExp(matcher).test(name); }  // 正则 test，不是全等
  catch { return name === matcher; }
}
```

**两层分工的根本原因：信息可见时机**。matcher 只能匹配工具名不是设计缺陷，而是信息边界——`tool_name` 在 spawn 之前 CodeBuddy 就知道（所以能做进程外零成本过滤），而 `tool_input` 里的 `file_path`/阶段状态等业务信息，只有 spawn 后通过 stdin 传给脚本才能看到。**能按工具筛的放 L0（免费），必须看输入内容的放 L1（spawn 后）**——这条边界决定了任何 hook 的过滤结构怎么设计。

**L1 脚本内的关卡顺序原则：越廉价越靠前**。以 excalidraw-render-gate.js 为参考实现，从上到下依次是：

1. 环境变量总开关（`XXX_GATE_OFF`）——一个 if 秒退
2. 工具名复验——对 L0 的防御性重复（脚本可能被手工测试/异常路径调用，自身逻辑要独立成立）
3. 文件路径正则 + `fs.existsSync`——真正的目标判定，兼容多种字段名（file_path/filePath/path/target_file）
4. 依赖存在性（如渲染脚本路径）——目标命中但依赖缺失也不空转
5. 以上全过才进重活（子进程执行业务校验）

任何一关不过都 `emit({})` 静默退出——对非目标场景零打扰、零额外逻辑开销（实测早退路径与空启动同为 ~20ms，边际成本≈0，见第四节实测数据）。

## 三、三个必验的坑

### 坑 1：工具名想当然

**错误**：在脚本里写 IDE 的工具名（`write_to_file` / `replace_in_file`）。

**验证**（以 CodeBuddy CLI 为例，路径按你的安装方式调整）：
```bash
cd <你的 codebuddy CLI 安装目录>/dist
grep -c 'write_to_file' codebuddy.js    # → 0，不存在
```

**CLI 权威工具名**（v2.148.0 实测）：`Edit` / `MultiEdit` / `Write` / `NotebookEdit` / `Glob` / `Grep` / `Bash` / `PowerShell` / `Read` / `LSP` / `Skill` / `Agent` / `TaskCreate` / `TaskGet` / `TaskUpdate` / `TaskList` / `TaskStop` / `TaskOutput` / `SendMessage` / `ToolSearch` / `AskUserQuestion` / `EnterPlanMode` / `ExitPlanMode` / `present_files` / `read_me` / `show_widget` / `StructuredOutput` / `TeamCreate` / `TeamDelete` / `SkillManage` / `DeferExecuteTool`

> ⚠️ **后果最严重**：工具名写错 → hook 在真实调用时全部静默放过。你会以为门禁在工作，实际一次都没拦住。

### 坑 2：matcher 必须加锚点

`new RegExp("Edit").test(name)` 会匹配任何**包含** "Edit" 的名字（如 `NotebookEdit`）。

```json
{ "matcher": "^(Edit|MultiEdit|Write|NotebookEdit)$" }
```

> 官方文档说"`Write` 会匹配任何包含 Write 的工具名"是在**描述行为**，不是推荐写法。

### 坑 3：`decision: "block"` 已废弃

官方文档三处标注已废弃。正确 API：

| 事件 | 正确写法 | 语义 |
|------|---------|------|
| **PreToolUse** | `hookSpecificOutput.permissionDecision: "allow"/"deny"/"ask"` | deny 阻止并告知 Agent |
| **Stop** | `{ continue: false, reason }` | 阻止停止，reason 注入对话历史 |
| **Stop** | `{ systemMessage }` | 仅显示给用户，不传给 Agent |

## 四、成本控制

| 选择 | 成本 | 适用 |
|------|------|------|
| `type: "command"` | **零 LLM 调用、零 token**，毫秒级 | 判定标准确定（字段非空/有出处） |
| `type: "prompt"` | 调 `lite` 槽位小模型，慢且花钱 | 判定需要语义理解 |

**Stop hook 的两种返回**：
- `systemMessage` → 仅界面提醒，零成本，不打断对话（**默认选这个**）
- `continue: false` → 让 AI 继续工作，本质是**注入一条内部 user message 再跑一轮**（多一次 LLM 调用 + 循环风险）

**设计决策**：默认 `systemMessage`，用环境变量控制升级为阻断。

### 冷启动实测与分层提速（macOS M3，10 次均值，2026-09-20）

| 路径 | 耗时 | 结论 |
|------|------|------|
| node 空启动 | ~20ms | **node 比 python 快**（V8 快照优化），换 python 提速是伪命题 |
| python3 空启动 | ~32ms | import 开销更大 |
| node 早退路径（stdin+正则+输出） | ~20ms | **早退逻辑边际成本 ≈ 0**——20ms 几乎全是进程 spawn 税 |

**开销大头是 spawn（进程创建），不是脚本逻辑，更不是语言**。分层提速策略（按性价比排序）：

| 层 | 手段 | 成本 | 说明 |
|----|------|------|------|
| L0 | **matcher 前置** | 0ms | CodeBuddy 进程内正则，不命中**根本不 spawn**——第一防线永远是收紧 matcher |
| L1 | **脚本内早退** | spawn 后 +0ms | stdin 解析 + 路径判断放脚本最前面，非目标立即 exit（省的是逻辑时间，省不了 spawn） |
| L2 | 语言选择 | 20ms vs 32ms | 差 12ms 感知不到，**不值得为提速混语言**；选语言看项目统一性 |
| L3 | **dispatcher 合并** | N×20ms → 20ms | 同事件 N 个 hook 合一进程按路径分发，spawn 税只交一次——**hook 超过 3-5 个时的正解** |
| L4 | 常驻 daemon（unix socket） | ~5ms | 冷启动变 IPC，但引入进程管理复杂度；hook <10 个不值得 |

> 同一事件的多个 hook 按 CodeBuddy 文档**并行执行**——最坏情况耗时 ≈ 最慢 hook 而非总和，但 10 个并行 spawn 的 CPU 争抢在低核机器上仍可感知。数量控制是根本。

## 五、必须遵守的四条

1. **fail-open**：脚本任何异常都放行，绝不因 hook 自身出错阻塞 AI
   ```js
   try { result = handle(hook); } catch { result = null; }
   emit(result || {});
   ```
2. **零打扰**：没有进行中的任务时静默放行（`{}`）
3. **开关**：提供环境变量（如 `XXX_GATE_OFF=1`）临时关闭
4. **配置备份**：改 `settings.json` 前先备份（它是共享文件，别改坏别人的 hook）

## 六、配置结构

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^(Edit|MultiEdit|Write|NotebookEdit)$",
        "hooks": [
          { "type": "command", "command": "node .codebuddy/hooks/xxx-gate.js", "timeout": 10 }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "node .codebuddy/hooks/xxx-gate.js", "timeout": 15 }
        ]
      }
    ]
  }
}
```

**验证配置合法性**：
```bash
node -e "const c=require('./.codebuddy/settings.json'); console.log(Object.keys(c.hooks))"
```

## 七、测试方法（必须做）

```bash
# 模拟 PreToolUse 输入
echo '{"hook_event_name":"PreToolUse","tool_name":"Edit","cwd":"'$PWD'","tool_input":{"file_path":"/tmp/foo.py"}}' \
  | node .codebuddy/hooks/xxx-gate.js

# 模拟 Stop 输入
echo '{"hook_event_name":"Stop","cwd":"'$PWD'"}' | node .codebuddy/hooks/xxx-gate.js
```

**必测四个场景**：
1. 该拦的拦住（合规检查失败）
2. 该放的放行（留痕区 / 非写文件工具）
3. 阶段切换后行为正确（A 阶段拦、B 阶段放行）
4. 无任务时静默（`{}`）
