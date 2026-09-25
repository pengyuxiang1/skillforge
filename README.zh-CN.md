# skillforge

**A meta-skill that forges skills — state-machine driven, gate-enforced, grows with every use.**

**中文** | [English](README.md)

> 生产 skill 的 skill：状态机驱动，自带门禁，越用越好。

AI 在长任务里跑偏，不是它笨——是规矩放在了错的地方。

**写在提示词里的规矩，任务一长就会被稀释；写进代码里的规矩，才拦得住。**

skillforge 把一套工作流"锻造"成一个**超级 skill**：有状态文件记住进度，有引导脚本现场算下一步，有门禁 hook 把约束变成代码。它自己也是超级 skill，吃自己的狗粮——生产 skill 的过程，就是用状态机驱动的。

配套仓库 **[question-diagnosis](https://github.com/pengyuxiang1/question-diagnosis)** 是它改造出的真实案例：一个逼着 AI"先交证据再下结论"的问题定位 skill。

---

## 什么是"超级 skill"

三个部件，缺一不可：

| 部件 | 角色 | 解决什么 |
|------|------|---------|
| **状态文件** | 记忆 | 落盘，跨会话、抗上下文压缩——**记忆在磁盘上，不在上下文里** |
| **引导脚本** | 方向 | 每次现场拉取：现在在哪、下一步做什么、缺什么、红线是什么 |
| **门禁 hook** | 执行 | 把文字协议变成代码——不合规就拦，不靠 AI 自觉 |

只有状态文件，是纯记录；只有引导脚本，AI 会忘记调；只有 hook，没有状态可判。

**判定标准是命门**：写不出检查代码的判定标准，门禁就拦不住。"证据充分"是虚的，"标了已证实的假设其证据段必须有出处"是实的——自检方法：能不能写一个十行的检查脚本？

---

## 安装

### 方式一：npx skills（推荐，官方支持 79 个 Agent，含 CodeBuddy）

```bash
npx skills add pengyuxiang1/skillforge                       # 自动检测已安装的 Agent
npx skills add pengyuxiang1/skillforge -a codebuddy -g -y    # 指定 Agent + 全局 + 免确认
```

完整 Agent 映射表见 [vercel-labs/skills](https://github.com/vercel-labs/skills)。

### 方式二：一键脚本

```bash
git clone https://github.com/pengyuxiang1/skillforge.git
cd skillforge
./install.sh                          # 自动检测已安装的 Agent 并安装
./install.sh --agent codebuddy        # 或指定：codebuddy / claude-code / codex / cursor
./install.sh --link                   # 符号链接安装，便于 git pull 更新
```

不想 clone，也可以一行装：

```bash
curl -fsSL https://raw.githubusercontent.com/pengyuxiang1/skillforge/main/install.sh | bash -s -- --agent codebuddy
```

### 方式三：让 AI 帮你装

把仓库地址直接丢给你的 AI 编程助手，附上一句：

> 克隆这个仓库，把 `skillforge/` 目录安装到你的 skills 目录（CodeBuddy 是 `~/.codebuddy/skills/`，Claude Code 是 `~/.claude/skills/`），然后运行 `python3 <目标路径>/skillforge/scripts/skill_guide.py --list` 验证安装。

### 验证

```bash
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py --new "测试流程"
```

---

## 快速开始

```bash
# 1. 开一个新生产任务（生成状态文件）
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py --new "发布流程"

# 2. 每个动作前先跑引导——它告诉你当前阶段、下一步、缺什么
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py <state.md路径>

# 3. 阶段完成后推进
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py <state.md路径> --advance

# 看所有进行中的生产任务
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py --list
```

引导返回：`stage`（当前阶段）/ `next`（下一步）/ `how`（怎么做）/ `gaps`（缺什么）/ `checklist`（检查项）/ `reminder`（硬约束）。

---

## 它怎么工作

### 五阶段流程

```
Stage 0  接收澄清   →  问清 4 件事（触发场景 / 产物 / 判定标准 / 目标 Agent）
Stage 1  复杂度评估 →  决策树判断：值不值得做？拆几个状态？
Stage 2  状态机设计 →  逐个推荐状态，等用户确认
Stage 3  引导脚本   →  判断要不要，要就设计
Stage 4  门禁 hook  →  判断要不要，要就设计
Stage 5  验证沉淀   →  实测跑通 + 判断是否沉淀案例
```

### 决策树（Stage 1 的核心价值）

```
Q1 这个工作流会重复执行吗？
   └─ 否 → 不做 skill，直接做完事就结束
Q2 步骤 ≤3 且线性？
   └─ 是 → 只写 SKILL.md，不要状态机/脚本/hook
Q3 会跨会话吗？单次执行会撑爆上下文吗？
   └─ 是 → 需要状态文件（进入超级 skill 范畴）
Q4 AI 容易在长任务中跑偏吗？
   └─ 是 → 加引导脚本
Q5 有负面约束吗（不许做 X）？
   └─ 有 → 必须加 hook（提醒对负面约束无效）
```

**顺序很重要。多数工作流不需要超级 skill——判断本身，也是产出。**

### 验证（Stage 5，必须实测）

| 层 | 验什么 |
|---|--------|
| L1 | 引导脚本在真实状态文件上跑通 |
| L2 | 门禁在"合规样本"上放行 |
| L3 | 门禁在"违规样本"上拦住（**要试一把锁，先做一回贼**） |
| L4 | 阶段切换后行为正确（A 阶段拦、B 阶段放行） |

L3 最容易漏。只测"能跑通"等于没测——必须证明它能拦住不该发生的。

---

## 仓库结构

```
skillforge/
├── README.md                        # English
├── README.zh-CN.md                  # 中文
├── install.sh                       # 安装脚本（多 Agent / 幂等 / 可 curl 一行装）
├── skillforge/                      # ← skill 本体，复制到你的 skills 目录
│   ├── SKILL.md                     # 主流程（五阶段）
│   ├── scripts/
│   │   └── skill_guide.py           # 引导脚本（零依赖、只读、零参数）
│   ├── references/
│   │   ├── stage-design.md          # 状态拆解方法论（状态三条件、五要素）
│   │   ├── guide-script-spec.md     # 引导脚本设计规范
│   │   ├── hook-spec.md             # 门禁设计规范（含三个必验的坑）
│   │   ├── note-format.md           # 案例沉淀格式
│   │   ├── hooks-ref/               # 三家 Agent hook 官方文档快照
│   │   └── cases/                   # 生产案例库（越用越厚）
│   └── assets/
│       └── skill-skeleton.md        # skill 骨架模板
└── LICENSE                          # MIT 许可
```

---

## 配套仓库：question-diagnosis

[github.com/pengyuxiang1/question-diagnosis](https://github.com/pengyuxiang1/question-diagnosis)

一个"假设—验证"循环驱动的问题定位 skill，也是检验这套方法的最好样本。

- **状态机**：`collect → hypothesize → verify → conclude`，验证失败回到假设，循环有明确出口
- **引导脚本**：`flow_guide.py` 读 task.md，返回下一步和证据缺口；`--check` 做下结论前的自检（退出码 1 = 有缺口，不许给根因）
- **门禁 hook**：拦住三类违规——标了"已证实"但证据无出处、已判定的假设缺判定标准、写了结论却无已证实假设支撑
- **实战效果**：真实案例（5 条假设、3 条证实、2 条未收敛）被门禁准确报出"仍有 2 条假设未收敛，却已写结论"

---

## 支持哪些 Agent

**安装层面**：npx skills 官方支持 **79 个 Agent**（完整映射表见 [vercel-labs/skills](https://github.com/vercel-labs/skills)）；仓库自带的 `install.sh` 覆盖下列 21 个常用 Agent（`./install.sh --list-agents` 可查全部）：

| Agent | `--agent` | 全局 skills 目录 | hooks |
|-------|-----------|-----------------|-------|
| CodeBuddy | `codebuddy` | `~/.codebuddy/skills/` | ✅ 全流程实测 |
| Claude Code | `claude-code` | `~/.claude/skills/` | ✅ |
| Cline | `cline` | `~/.agents/skills/` | ✅ |
| Kiro CLI | `kiro-cli` | `~/.kiro/skills/` | ✅ |
| Codex | `codex` | `~/.codex/skills/` | 按官方文档（另有 trust 机制） |
| Cursor | `cursor` | `~/.cursor/skills/` | 见官方文档 |
| Gemini CLI | `gemini-cli` | `~/.gemini/skills/` | 见官方文档 |
| OpenCode | `opencode` | `~/.config/opencode/skills/` | 见官方文档 |
| Windsurf | `windsurf` | `~/.codeium/windsurf/skills/` | 见官方文档 |
| GitHub Copilot | `github-copilot` | `~/.copilot/skills/` | 见官方文档 |
| Trae / Qoder / Qwen Code / Roo / Goose / Continue / Amp / Crush / Junie / iFlow | 同名参数 | `./install.sh --list-agents` 查看 | 见各自文档 |

**两点要注意：**

1. **门禁 hook 只在支持 hooks 的 Agent 上生效**（CodeBuddy / Claude Code / Cline / Kiro CLI，其余以官方文档为准）。不支持 hooks 的 Agent 仍能获得状态文件和引导脚本——三件套里的两件，收益已经拿到大半。
2. **Hook 语法各家不通用**，照搬会静默失效。写门禁前先查目标 Agent 的官方文档——`references/hooks-ref/` 里有三家文档的本地快照兜底。

---

## 设计原则

1. **记忆在磁盘上，不在上下文里**——状态文件落盘，压缩、换会话、换模型都不怕
2. **纪律与数据分家**——CLI/脚本提供确定性输入（现场算），纪律写在 skill 里
3. **判定标准必须能机器校验**——写不出检查代码的判定，门禁拦不住
4. **默认提醒，按需阻断**——`systemMessage` 零成本；`continue: false` 要付一轮 LLM 调用
5. **fail-open**——门禁脚本自己出错时放行，宁可漏拦，不可误伤
6. **判断本身也是产出**——说"不做"，跟做出一个东西是同样的贡献
7. **验证必须造假样本**——只测"跑通"等于没测

---

## FAQ

**Q：它和官方的 skill-creator 有什么区别？需要都装吗？**

**不用都装。**skillforge 自包含：基础规范（description 即触发、三级加载、资源三分法）已内置，交付前校验用自带的 `scripts/validate_skill.py`（零依赖）——只装它就能完成从创建到硬化的全流程。

官方 skill-creator 可选：需要脚手架（`init_skill.py`）或打包分发（`package_skill.py`）时再装，也可用它的 `quick_validate.py` 做更严格的交叉验证。

**Q：支持中文吗？**

支持。脚本零依赖，中英文工作流都可以。

**Q：它的状态机是什么实现的？**

没有框架——状态就是一份 Markdown 文件，脚本读它算阶段。简单、可 diff、可手改。

**Q：会不会太重？我只想写个简单 skill。**

那就不要用它。Q1/Q2 答不上来的工作流，写个 SKILL.md 就够了——这个判断本身就是它的价值。

**Q：想装到 npx skills 之外的 Agent？**

用仓库自带的 `install.sh`（21 个常用 Agent，`--list-agents` 查看），或直接用 `--dir` 指到任意目录：

```bash
./install.sh --dir ~/your-agent/skills
```

---

## 相关阅读

- 机制的来源与论证：从 [openspec](https://github.com/Fission-AI/OpenSpec) 的源码中抽象——引导现场拉取、校验落在产物、判定可机器校验
- 同名公众号文章：《写给 AI 的规矩，越写越没用》

## License

MIT
