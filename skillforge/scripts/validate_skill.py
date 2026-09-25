#!/usr/bin/env python3
"""
validate_skill.py — skill 基础规范校验（零依赖，仅标准库）

检查项：
  1. SKILL.md 存在，且以 YAML frontmatter（---）开头
  2. frontmatter 字段白名单：name / description / license / allowed-tools / metadata
  3. name：hyphen-case（小写字母、数字、连字符），≤ 64 字符
  4. description：非空，≤ 1024 字符，不含尖括号 < >
  5. 体积提示：SKILL.md 超过 500 行 → warning（建议拆到 references/）

用法:
    python3 validate_skill.py <skill目录>
    python3 validate_skill.py .            # 校验当前目录

退出码: 0 = 通过（可能带 warning）；1 = 有错误；2 = 用法错误
"""

import re
import sys
from pathlib import Path

ALLOWED_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024
MAX_SKILL_LINES = 500


def parse_frontmatter(text):
    """解析简单 YAML frontmatter，返回 (fields, error)。支持 | / > 多行值。"""
    if not text.startswith("---"):
        return None, "SKILL.md 必须以 YAML frontmatter（---）开头"
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.DOTALL)
    if not m:
        return None, "frontmatter 格式不合法：缺少结束的 ---"

    lines = m.group(1).split("\n")
    fields = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        mm = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not mm:
            i += 1
            continue
        key, val = mm.group(1), mm.group(2).strip()
        if val in ("|", ">", "|-", ">-", "|+", ">+"):
            block, j = [], i + 1
            while j < len(lines) and (lines[j].startswith((" ", "\t")) or not lines[j].strip()):
                if lines[j].strip():
                    block.append(lines[j].strip())
                j += 1
            val = " ".join(block)
            i = j
        else:
            i += 1
        fields[key] = val
    return fields, None


def validate(skill_dir):
    """返回 (errors: list, warnings: list)"""
    errors, warnings = [], []
    p = Path(skill_dir)
    skill_md = p / "SKILL.md"
    if not skill_md.exists():
        return [f"SKILL.md 不存在：{skill_md}"], warnings

    text = skill_md.read_text(encoding="utf-8", errors="replace")

    fields, err = parse_frontmatter(text)
    if err:
        return [err], warnings

    # 1. 字段白名单
    unexpected = set(fields) - ALLOWED_PROPERTIES
    if unexpected:
        errors.append(
            "frontmatter 含未允许字段：%s（白名单：%s）"
            % (", ".join(sorted(unexpected)), ", ".join(sorted(ALLOWED_PROPERTIES)))
        )

    # 2. name
    name = fields.get("name", "")
    if not name:
        errors.append("缺少 name 字段")
    else:
        if len(name) > MAX_NAME_LEN:
            errors.append("name 超长（%d > %d 字符）" % (len(name), MAX_NAME_LEN))
        if not NAME_RE.match(name):
            errors.append("name 必须是 hyphen-case（小写字母/数字/连字符）：%r" % name)

    # 3. description
    desc = fields.get("description", "")
    if not desc:
        errors.append("缺少 description —— AI 只读 name + description 决定是否触发，必填")
    else:
        if len(desc) > MAX_DESC_LEN:
            errors.append("description 超长（%d > %d 字符）" % (len(desc), MAX_DESC_LEN))
        if "<" in desc or ">" in desc:
            errors.append("description 不能包含尖括号 < >")

    # 4. 体积提示
    n_lines = text.count("\n") + 1
    if n_lines > MAX_SKILL_LINES:
        warnings.append(
            "SKILL.md 有 %d 行（建议 ≤ %d 行，超出的内容拆到 references/ 按需加载）"
            % (n_lines, MAX_SKILL_LINES)
        )

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)

    target = sys.argv[1]
    errors, warnings = validate(target)

    for w in warnings:
        print("⚠️  %s" % w)
    if errors:
        for e in errors:
            print("❌ %s" % e)
        print("\n校验未通过：%d 个错误" % len(errors))
        sys.exit(1)

    print("✅ 校验通过：%s" % Path(target).resolve())
    sys.exit(0)


if __name__ == "__main__":
    main()
