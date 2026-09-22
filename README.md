# skillforge

**A meta-skill that forges skills — state-machine driven, gate-enforced, grows with every use.**

[中文](README.zh-CN.md) | **English**

> Turn a workflow into a *super skill*: a state file that remembers, a guide script that computes the next step, and a gate hook that enforces the rules.

AI agents drift on long tasks. Not because they're dumb — because the rules were written in the wrong place.

**Rules written in prompts get diluted as the context grows. Rules compiled into code hold.**

skillforge forges a workflow into a **super skill**. It is itself a super skill — it eats its own dogfood: the process of forging a skill is driven by its own state machine.

Ships with a real-world case: **question-diagnosis**, an incident-diagnosis skill that forces the agent to show evidence before drawing conclusions.

---

## What is a "super skill"?

Three parts, none optional:

| Part | Role | Solves |
|------|------|--------|
| **State file** | Memory | Disk-backed, survives compaction and new sessions — *memory lives on disk, not in context* |
| **Guide script** | Direction | Computed on the spot: where you are, what's next, what's missing, what the red lines are |
| **Gate hook** | Enforcement | Turns the written protocol into code — violations get blocked, not trusted |

A state file alone is just a record. A guide script alone gets forgotten in long tasks. A gate hook alone has no state to check against.

**The completion criterion is the litmus test**: if you can't write a 10-line check script for it, the gate can't enforce it. "Evidence is sufficient" is mush; "every assumption marked 🟢 must carry a source in its evidence block" is enforceable.

---

## Install

### Option 1: npx skills (recommended, 35+ agents)

```bash
npx skills add <owner>/skillforge
```

### Option 2: install script

```bash
git clone https://github.com/<owner>/skillforge.git
cd skillforge
./install.sh                          # auto-detects installed agents
./install.sh --agent codebuddy        # or: codebuddy / claude-code / codex / cursor
./install.sh --link                   # symlink instead of copy (easy to update)
```

No clone needed:

```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/skillforge/main/install.sh | bash -s -- --agent codebuddy
```

### Option 3: let your agent do it

Paste the repo URL to your AI coding agent with this line:

> Clone this repo and install the `skillforge/` directory into your skills directory (CodeBuddy: `~/.codebuddy/skills/`, Claude Code: `~/.claude/skills/`). Then verify with `python3 <target>/skillforge/scripts/skill_guide.py --list`.

### Verify

```bash
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py --new "test workflow"
```

---

## Quick start

```bash
# 1. Start a new forging task (generates a state file)
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py --new "release process"

# 2. Before every action, run the guide — it tells you the current stage, next step, and gaps
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py <path/to/state.md>

# 3. Advance when a stage is done
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py <path/to/state.md> --advance

# List all forging tasks in progress
python3 ~/.codebuddy/skills/skillforge/scripts/skill_guide.py --list
```

The guide returns: `stage` / `next` / `how` / `gaps` / `checklist` / `reminder`.

---

## How it works

### Five stages

```
Stage 0  Intake      →  Clarify 4 things (trigger / artifact / criterion / target agent)
Stage 1  Complexity  →  Decision tree: worth it? how many states?
Stage 2  State design→  Propose states one by one, wait for confirmation
Stage 3  Guide script→  Decide if needed; design it if so
Stage 4  Gate hook   →  Decide if needed; design it if so
Stage 5  Verify      →  Test for real + decide whether to keep the case
```

### The decision tree (the core value of Stage 1)

```
Q1 Will this workflow run repeatedly?
   └─ No → don't build a skill at all
Q2 ≤3 steps and linear?
   └─ Yes → just write a SKILL.md, no state machine / scripts / hooks
Q3 Cross-session? Will one run blow up the context?
   └─ Yes → you need a state file (entering super-skill territory)
Q4 Does the agent drift on long tasks?
   └─ Yes → add a guide script
Q5 Any negative constraints (never do X)?
   └─ Yes → a gate hook is mandatory (reminders don't work on negative constraints)
```

**Order matters. Most workflows don't need a super skill — the decision itself is a deliverable.**

### Verification (Stage 5, must actually run)

| Layer | What to verify |
|-------|----------------|
| L1 | The guide script runs on a real state file |
| L2 | The gate lets compliant samples pass |
| L3 | The gate blocks a violating sample (**to test a lock, play the thief**) |
| L4 | Behavior switches correctly across stages (block in A, pass in B) |

L3 is the one people skip. "It runs" is not a test — you must prove it blocks what it should.

---

## Repo structure

```
skillforge/
├── README.md                        # English (you are here)
├── README.zh-CN.md                  # 中文
├── install.sh                       # installer (multi-agent / idempotent / curl-able)
├── skillforge/                      # ← the skill itself; copy into your skills dir
│   ├── SKILL.md                     # main flow (five stages)
│   ├── scripts/
│   │   └── skill_guide.py           # guide script (zero-dependency, read-only)
│   ├── references/
│   │   ├── stage-design.md          # state decomposition methodology
│   │   ├── guide-script-spec.md     # guide script spec
│   │   ├── hook-spec.md             # gate hook spec (incl. three must-verify pitfalls)
│   │   ├── note-format.md           # case-study format
│   │   ├── hooks-ref/               # local snapshots of 3 agents' hook docs
│   │   └── cases/                   # case library (grows with use)
│   └── assets/
│       └── skill-skeleton.md        # skill skeleton template
└── examples/
    └── question-diagnosis/          # a real case forged by skillforge
```

---

## Case: question-diagnosis

An incident-diagnosis skill driven by a hypothesize–verify loop — and the best stress test of this methodology.

- **State machine**: `collect → hypothesize → verify → conclude`; failed verifications loop back, with explicit exit conditions
- **Guide script**: `flow_guide.py` reads `task.md`, returns the next step and evidence gaps; `--check` gate-keeps before conclusions (exit code 1 = gaps exist, no root cause allowed)
- **Gate hook**: blocks three classes of violations — "confirmed" without a traceable source, a judged assumption missing its criterion, a conclusion with no confirmed assumption behind it
- **Real-world result**: a case with 5 assumptions (3 confirmed, 2 open) was correctly flagged: *"2 assumptions still open, yet a conclusion was written"*

---

## Supported agents

| Agent | Skills directory | Hook config | Status |
|-------|-----------------|-------------|--------|
| CodeBuddy | `~/.codebuddy/skills/` | `.codebuddy/settings.json` | Fully tested |
| Claude Code | `~/.claude/skills/` | `.claude/settings.json` | Structure portable; rewrite syntax per official docs |
| Codex | `~/.codex/skills/` | `.codex/hooks.json` / `config.toml` | Same; plus a trust mechanism |
| Cursor | `~/.cursor/skills/` | see official docs | Supported by the installer |

**Hook syntax is not portable across agents** — copy-pasting silently fails. Check the target agent's official docs first; `references/hooks-ref/` keeps local snapshots of three of them as a fallback.

---

## Design principles

1. **Memory lives on disk, not in context** — state files survive compaction, new sessions, new models
2. **Discipline and data are separate** — scripts provide deterministic input (computed on the spot); discipline lives in the skill
3. **Completion criteria must be machine-checkable** — if you can't code the check, the gate can't enforce it
4. **Remind by default, block on demand** — `systemMessage` costs nothing; `continue: false` costs an LLM turn
5. **Fail-open** — if the gate script itself errors, let it pass; better a miss than a false block
6. **The decision is a deliverable** — saying "don't build this" saves an hour and counts as output
7. **Verify with fake samples** — "it runs" is not a test

---

## FAQ

**Q: How is this different from the official skill-creator?**

The official skill-creator covers the basics (how to write a SKILL.md, how to package). skillforge covers advanced hardening (state machines, guide scripts, gate hooks). They complement each other: start with the official one, then use skillforge to decide whether hardening is worth it.

**Q: Does it work with non-English workflows?**

Yes. Zero dependencies, any language.

**Q: What is the state machine built on?**

No framework — a state is just a Markdown file, and the script reads it to compute the stage. Simple, diffable, hand-editable.

**Q: Isn't this overkill? I just want a simple skill.**

Then don't use it. If Q1/Q2 don't pass, a plain SKILL.md is enough — that judgment call is the value itself.

**Q: npx skills doesn't support my agent (e.g. CodeBuddy)?**

CodeBuddy is not in the npx skills agent list — use the bundled installer:

```bash
./install.sh --agent codebuddy
```

---

## Related reading

- Where the mechanics come from: abstracted from the [openspec](https://github.com/Fission-AI/OpenSpec) source — instructions computed on the spot, validation on artifacts, machine-checkable criteria
- Companion article (Chinese): 《写给 AI 的规矩，越写越没用》

## License

MIT
