#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_guide.py — 超级 skill 生产引导器（skillforge）

职责：
  1. `--new "<名称>"`  创建生产任务的状态文件
  2. `<state.md>`      读状态 → 返回当前阶段 / 下一步 / 怎么做 / 检查清单
  3. `--advance`       把当前阶段标记为完成，进入下一阶段
  4. `--list`          列出所有进行中的生产任务

设计：吃自己的狗粮 —— skillforge 自己就是"状态文件 + 引导脚本"的示范。

用法:
    python3 skill_guide.py --new "问题定位流程"
    python3 skill_guide.py <state.md>
    python3 skill_guide.py <state.md> --advance
    python3 skill_guide.py <state.md> --json
    python3 skill_guide.py --list

退出码:
    0 = 正常
    1 = 有阻塞项（当前阶段缺必填内容）
    2 = 用法错误
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from typing import Dict, List, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(BASE_DIR, "tasks")

# ---------------------------------------------------------------------------
# 阶段定义（这就是本 skill 的状态机）
# ---------------------------------------------------------------------------

STAGES: List[Dict[str, Any]] = [
    {
        "id": "collect",
        "title": "Stage 0 接收澄清",
        "next": "问清四件事（含目标 Agent），产出工作流摘要",
        "how": "只收事实，禁止设计。缺则追问，不要猜。目标 Agent 决定 hook 语法。",
        "checklist": [
            "触发场景（谁 / 何时 / 为什么用这个流程）",
            "产物（文件 / 报告 / 决策 / 代码变更）",
            "判定标准（优先选能写成确定性检查的）",
            "目标 Agent（CodeBuddy / Claude Code / Codex）",
        ],
    },
    {
        "id": "assess",
        "title": "Stage 1 复杂度评估",
        "next": "按决策树逐项判断 Q1~Q5，给结论",
        "how": "读 references/stage-design.md；逐项给判断依据，不要跳过",
        "checklist": [
            "Q1 会重复执行吗（否则不做 skill）",
            "Q2 步骤数量与结构（≤3 线性 / ≥4 或含分支）",
            "Q3 会跨会话吗（否则不需状态文件）",
            "Q4 AI 易跑偏吗（否则引导脚本可选）",
            "Q5 有负面约束吗（有则必须加 hook）",
            "结论：做 / 不做 + 拆几个状态",
        ],
    },
    {
        "id": "design",
        "title": "Stage 2 状态机设计",
        "next": "逐个推荐状态（一次一个，等确认）",
        "how": "每个状态定义五要素：状态名 / 进入条件 / 产出 / 判定标准 / 下一步",
        "checklist": [
            "状态名有语义（不是 step1/step2）",
            "判定标准可机器校验（写得出检查代码）",
            "允许循环（验证失败能回到上一步）",
            "输出状态流转图（mermaid）",
            "用户已逐个确认",
        ],
    },
    {
        "id": "guide",
        "title": "Stage 3 引导脚本",
        "next": "判断是否需要 → 设计并实现",
        "how": "参考 references/guide-script-spec.md：零依赖、只读、返回结构化引导",
        "checklist": [
            "判断结论 + 依据（Q4 为是则必做）",
            "脚本实现（零依赖、只读不写）",
            "状态文件顶部钉引导指令",
            "实测跑通（真实状态文件）",
        ],
    },
    {
        "id": "hook",
        "title": "Stage 4 门禁 hook",
        "next": "判断是否需要 → 确认目标 Agent → 查官方文档 → 设计并实现",
        "how": "先查该 Agent 的 hook 官方文档（地址见 hook-spec.md 第零节），再读三个坑",
        "checklist": [
            "判断结论 + 依据（Q5 有负面约束则必做）",
            "目标 Agent 已确认 + 已查该 Agent 官方 hook 文档",
            "两层过滤（matcher 匹配工具名 + 脚本内业务判断）",
            "用 command 类型（零 token）",
            "fail-open（异常时放行）",
            "注册到该 Agent 的配置文件（改前备份）",
        ],
    },
    {
        "id": "verify",
        "title": "Stage 5 验证与沉淀",
        "next": "实测验证 L1~L4 → 判断是否沉淀案例",
        "how": "L3 必须造违规样本，证明门禁能拦住；沉淀格式见 references/note-format.md",
        "checklist": [
            "L1 引导脚本在真实状态文件上跑通",
            "L2 合规样本放行",
            "L3 违规样本被拦住（必做）",
            "L4 阶段切换后行为正确",
            "沉淀判断（有新方法论/新坑才值得）",
        ],
    },
]

STAGE_BY_ID = {s["id"]: s for s in STAGES}
STATUS_DONE = "✅"
STATUS_DOING = "🟡"
STATUS_TODO = "⏸"

STATE_HEADER = """# skill 生产：{name}

> 🔁 **引导机制 —— 每个动作前先跑，不要凭记忆推进**
>
> ```bash
> python3 .codebuddy/skills/skillforge/scripts/skill_guide.py {self_path}
> ```
>
> 它会读本文件、返回：**当前阶段 / 下一步做什么 / 怎么做 / 检查清单 / 缺什么**。
> 阶段完成后跑 `--advance` 推进。

"""


# ---------------------------------------------------------------------------
# 状态文件读写
# ---------------------------------------------------------------------------

def stage_block(stage: Dict[str, Any], status: str = STATUS_TODO, extra: str = "") -> str:
    lines = ["## %s" % stage["title"], "", "- 状态：%s" % status]
    if extra:
        lines.append(extra.rstrip())
    lines.append("")
    return "\n".join(lines)


def new_state_file(name: str) -> str:
    os.makedirs(TASKS_DIR, exist_ok=True)
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", name).strip("-")
    path = os.path.join(TASKS_DIR, "%s-%s.md" % (date.today().isoformat(), slug))
    if os.path.exists(path):
        path = path.replace(".md", "-%d.md" % (len(os.listdir(TASKS_DIR)) + 1))

    body = [STATE_HEADER.format(name=name, self_path=os.path.relpath(path))]
    for i, st in enumerate(STAGES):
        body.append(stage_block(st, STATUS_DOING if i == 0 else STATUS_TODO))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(body))
    return path


def parse_state(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    lines = raw.replace("\r\n", "\n").split("\n")

    name = ""
    for line in lines:
        if line.startswith("# "):
            name = line[2:].replace("skill 生产：", "").strip()
            break

    stages: Dict[str, Dict[str, Any]] = {}
    current_id = None
    for line in lines:
        m = re.match(r"^##\s+(Stage\s*\d+\s*.*)$", line.strip())
        if m:
            title = m.group(1).strip()
            sid = None
            for st in STAGES:
                if st["title"].split()[1] == title.split()[1]:  # 比对 Stage N
                    sid = st["id"]
                    break
            current_id = sid
            if sid:
                stages[sid] = {"status": STATUS_TODO, "body": []}
            continue
        if current_id:
            sm = re.match(r"^-\s*状态\s*[:：]\s*(\S+)", line.strip())
            if sm:
                stages[current_id]["status"] = sm.group(1)
            elif line.strip() and not line.strip().startswith(">"):
                stages[current_id]["body"].append(line.strip())

    # 当前阶段 = 第一个未完成的
    current = None
    for st in STAGES:
        info = stages.get(st["id"], {"status": STATUS_TODO, "body": []})
        if info["status"] != STATUS_DONE:
            current = st
            break

    return {"name": name, "path": path, "stages": stages, "current": current, "raw": raw}


def advance(path: str) -> Optional[str]:
    st = parse_state(path)
    cur = st["current"]
    if not cur:
        return None
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    # 当前阶段标 ✅
    raw = re.sub(
        r"(##\s+%s\b[^\n]*\n\n-\s*状态\s*[:：]\s*)\S+" % re.escape(cur["title"]),
        r"\g<1>" + STATUS_DONE,
        raw,
        count=1,
    )
    # 下一阶段标 🟡
    idx = STAGES.index(cur)
    if idx + 1 < len(STAGES):
        nxt = STAGES[idx + 1]
        raw = re.sub(
            r"(##\s+%s\b[^\n]*\n\n-\s*状态\s*[:：]\s*)\S+" % re.escape(nxt["title"]),
            r"\g<1>" + STATUS_DOING,
            raw,
            count=1,
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw)
    return STAGES[idx + 1]["id"] if idx + 1 < len(STAGES) else None


# ---------------------------------------------------------------------------
# 引导生成
# ---------------------------------------------------------------------------

def build_guidance(st: Dict[str, Any]) -> Dict[str, Any]:
    cur = st["current"]
    stages = st["stages"]

    done = [s["id"] for s in STAGES if stages.get(s["id"], {}).get("status") == STATUS_DONE]

    if not cur:
        return {
            "task": st["name"],
            "state_file": st["path"],
            "stage": "done",
            "stage_title": "全部阶段已完成",
            "progress": "%d/%d" % (len(STAGES), len(STAGES)),
            "next": "判断是否沉淀案例（references/note-format.md），然后归档",
            "how": "有新方法论或新坑才值得沉淀；常规实现不沉淀",
            "gaps": [],
            "checklist": [],
            "reminder": "沉淀判断：有其一即可 —— 新方法论 / 新坑 / 可复用模板",
        }

    body = stages.get(cur["id"], {}).get("body", [])
    # 缺口：检查清单里提到的必填项，body 里是否有对应内容
    gaps = []
    if cur["id"] == "collect":
        for key in ["触发场景", "产物", "判定标准"]:
            if not any(key in b for b in body):
                gaps.append("缺「%s」" % key)
    elif cur["id"] == "assess":
        if not any("结论" in b for b in body):
            gaps.append("缺「结论：做/不做 + 拆几个状态」")
    elif cur["id"] == "design":
        if not any(re.search(r"状态名|状态定义", b) for b in body):
            gaps.append("缺「状态定义表」")
    elif cur["id"] == "guide":
        if not any(re.search(r"需要|不需要|判断", b) for b in body):
            gaps.append("缺「是否需要引导脚本」的判断结论")
    elif cur["id"] == "hook":
        if not any(re.search(r"需要|不需要|判断", b) for b in body):
            gaps.append("缺「是否需要 hook」的判断结论")
    elif cur["id"] == "verify":
        if not any(re.search(r"L3|违规样本", b) for b in body):
            gaps.append("缺「L3 违规样本验证」结果")

    return {
        "task": st["name"],
        "state_file": st["path"],
        "stage": cur["id"],
        "stage_title": cur["title"],
        "progress": "%d/%d" % (len(done), len(STAGES)),
        "next": cur["next"],
        "how": cur["how"],
        "gaps": gaps,
        "checklist": cur["checklist"],
        "reminder": "先判断再动手；判定标准必须能机器校验；验证要造违规样本",
    }


def render_text(g: Dict[str, Any]) -> str:
    out = ["=" * 66, "🛠  %s" % g["task"], "=" * 66, ""]
    out.append("【当前阶段】%s（进度 %s）" % (g["stage_title"], g["progress"]))
    out.append("")
    out.append("▶ 下一步：%s" % g["next"])
    out.append("   怎么做：%s" % g["how"])
    out.append("")
    if g["checklist"]:
        out.append("📋 检查清单（本阶段做完前逐项确认）")
        for c in g["checklist"]:
            out.append("   ☐ %s" % c)
        out.append("")
    if g["gaps"]:
        out.append("⚠️ 缺口（%d 处，补齐后才能 --advance）" % len(g["gaps"]))
        for x in g["gaps"]:
            out.append("   - %s" % x)
        out.append("")
    out.append("💡 提醒：%s" % g["reminder"])
    out.append("")
    return "\n".join(out)


def list_tasks() -> int:
    if not os.path.isdir(TASKS_DIR):
        print("（无进行中的生产任务）")
        return 0
    files = [os.path.join(TASKS_DIR, f) for f in sorted(os.listdir(TASKS_DIR)) if f.endswith(".md")]
    if not files:
        print("（无进行中的生产任务）")
        return 0
    print("进行中的 skill 生产任务（%d）：" % len(files))
    for f in files:
        try:
            st = parse_state(f)
            cur = st["current"]
            print("  - %s" % f)
            print("      %s | 阶段：%s" % (st["name"], cur["title"] if cur else "已完成"))
        except Exception as exc:  # noqa: BLE001
            print("  - %s（解析失败：%s）" % (f, exc))
    return 0


# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="超级 skill 生产引导器（skillforge）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("state", nargs="?", help="状态文件路径")
    parser.add_argument("--new", metavar="NAME", help="新建生产任务（生成状态文件）")
    parser.add_argument("--advance", action="store_true", help="当前阶段标记完成，进入下一阶段")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON")
    parser.add_argument("--list", action="store_true", help="列出所有生产任务")
    args = parser.parse_args(argv)

    if args.list:
        return list_tasks()

    if args.new:
        path = new_state_file(args.new)
        st = parse_state(path)
        g = build_guidance(st)
        print("✅ 已创建状态文件：%s" % path)
        print()
        print(render_text(g))
        return 0

    if not args.state:
        parser.print_help()
        return 2

    path = args.state
    if not os.path.isabs(path) and not os.path.isfile(path):
        cand = os.path.join(TASKS_DIR, path)
        if os.path.isfile(cand):
            path = cand
        elif not path.endswith(".md"):
            cand = os.path.join(TASKS_DIR, path + ".md")
            if os.path.isfile(cand):
                path = cand
    if not os.path.isfile(path):
        sys.stderr.write("状态文件不存在：%s\n" % args.state)
        return 2

    if args.advance:
        nxt = advance(path)
        print("✅ 已推进" + ("到 %s" % nxt if nxt else "，全部阶段完成"))

    st = parse_state(path)
    g = build_guidance(st)
    if args.json:
        print(json.dumps(g, ensure_ascii=False, indent=2))
    else:
        print(render_text(g))
    return 1 if g["gaps"] else 0


if __name__ == "__main__":
    sys.exit(main())
