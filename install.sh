#!/usr/bin/env bash
#
# skillforge installer
# --------------------
# Install the skillforge skill into one or more AI agents' skills directory.
#
# Usage:
#   ./install.sh                          # install for every detectable agent
#   ./install.sh --agent codebuddy        # install for specific agent(s)
#   ./install.sh --agent claude-code codex
#   ./install.sh --link                   # symlink instead of copy (easy to update)
#   ./install.sh --dir ~/custom/skills    # install into a custom directory
#   ./install.sh --list-agents            # show all supported agents and their paths
#
# One-liner (no clone needed):
#   curl -fsSL https://raw.githubusercontent.com/<owner>/skillforge/main/install.sh | bash -s -- --agent codebuddy
#
# Paths follow the vercel-labs/skills (npx skills) agent mapping, the de-facto standard.
# For the full list of 79 supported agents run: npx skills add <owner>/skillforge --agent list
#
set -euo pipefail

SKILL_NAME="skillforge"
REPO_URL="${SKILLFORGE_REPO:-https://github.com/pengyuxiang1/skillforge.git}"

MODE="copy"
AGENTS=()
CUSTOM_DIR=""

info() { printf '  %s\n' "$*"; }
ok()   { printf '✅ %s\n' "$*"; }
warn() { printf '⚠️  %s\n' "$*" >&2; }
err()  { printf '❌ %s\n' "$*" >&2; }

usage() {
  sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# --- agent -> global skills dir ----------------------------------------------
# Source: vercel-labs/skills README agent mapping table (2026-09).
# Each agent also has a project-level directory; this script installs globally.
agent_skills_dir() {
  case "$1" in
    codebuddy)              echo "$HOME/.codebuddy/skills" ;;
    claude-code|claude)     echo "$HOME/.claude/skills" ;;
    codex)                  echo "$HOME/.codex/skills" ;;
    cursor)                 echo "$HOME/.cursor/skills" ;;
    gemini-cli|gemini)      echo "$HOME/.gemini/skills" ;;
    opencode)               echo "$HOME/.config/opencode/skills" ;;
    windsurf)               echo "$HOME/.codeium/windsurf/skills" ;;
    cline)                  echo "$HOME/.agents/skills" ;;
    github-copilot|copilot) echo "$HOME/.copilot/skills" ;;
    trae)                   echo "$HOME/.trae/skills" ;;
    qoder)                  echo "$HOME/.qoder/skills" ;;
    qwen-code)              echo "$HOME/.qwen/skills" ;;
    roo|roo-code)           echo "$HOME/.roo/skills" ;;
    goose)                  echo "$HOME/.config/goose/skills" ;;
    kiro-cli|kiro)          echo "$HOME/.kiro/skills" ;;
    continue)               echo "$HOME/.continue/skills" ;;
    amp)                    echo "$HOME/.config/agents/skills" ;;
    crush)                  echo "$HOME/.config/crush/skills" ;;
    junie)                  echo "$HOME/.junie/skills" ;;
    iflow-cli|iflow)        echo "$HOME/.iflow/skills" ;;
    agents|universal)       echo "$HOME/.agents/skills" ;;
    *) return 1 ;;
  esac
}

list_agents() {
  echo "Supported agents (global skills dir):"
  echo
  for a in codebuddy claude-code codex cursor gemini-cli opencode windsurf cline \
           github-copilot trae qoder qwen-code roo goose kiro-cli continue \
           amp crush junie iflow-cli agents; do
    printf '  %-18s %s\n' "$a" "$(agent_skills_dir "$a")"
  done
  echo
  echo "Full list (79 agents): see https://github.com/vercel-labs/skills"
  exit 0
}

# --- parse args -------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent|-a)
      shift
      while [[ $# -gt 0 && "$1" != --* ]]; do AGENTS+=("$1"); shift; done
      ;;
    --link|-l)      MODE="link"; shift ;;
    --dir|-d)       CUSTOM_DIR="${2:?--dir needs a path}"; shift 2 ;;
    --list-agents)  list_agents ;;
    --help|-h)      usage ;;
    *) err "Unknown option: $1"; usage ;;
  esac
done

# --- locate skill source ----------------------------------------------------
SCRIPT_DIR=""
if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
SRC_DIR="$SCRIPT_DIR/$SKILL_NAME"

if [[ ! -f "$SRC_DIR/SKILL.md" ]]; then
  info "Skill source not found next to the script; cloning from $REPO_URL ..."
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  git clone --depth 1 "$REPO_URL" "$TMP_DIR/repo"
  SRC_DIR="$TMP_DIR/repo/$SKILL_NAME"
fi

if [[ ! -f "$SRC_DIR/SKILL.md" ]]; then
  err "Cannot locate skill source (no SKILL.md in $SRC_DIR)"
  exit 1
fi

# --- resolve targets --------------------------------------------------------
TARGETS=()

if [[ -n "$CUSTOM_DIR" ]]; then
  TARGETS+=("$CUSTOM_DIR|custom")
fi

if [[ ${#AGENTS[@]} -eq 0 && -z "$CUSTOM_DIR" ]]; then
  # auto-detect: install for agents whose config dir already exists
  for a in codebuddy claude-code codex cursor gemini-cli opencode windsurf; do
    d="$(agent_skills_dir "$a")" || continue
    if [[ -d "$(dirname "$d")" ]]; then
      TARGETS+=("$d|$a")
    fi
  done
  if [[ ${#TARGETS[@]} -eq 0 ]]; then
    TARGETS+=("$(agent_skills_dir codebuddy)|codebuddy")
  fi
else
  for a in "${AGENTS[@]:-}"; do
    [[ -z "$a" ]] && continue
    d="$(agent_skills_dir "$a")" || {
      err "Unknown agent: $a"
      err "Run './install.sh --list-agents' to see supported agents."
      exit 1
    }
    TARGETS+=("$d|$a")
  done
fi

# --- install ----------------------------------------------------------------
echo "skillforge installer"
echo "===================="
echo
info "source : $SRC_DIR"
info "mode   : $MODE"
echo

DEST_LIST=()
for entry in "${TARGETS[@]}"; do
  target_parent="${entry%%|*}"
  label="${entry##*|}"
  dest="$target_parent/$SKILL_NAME"

  mkdir -p "$target_parent"

  # guard: refuse to delete something that doesn't look like a previous install
  if [[ -e "$dest" ]]; then
    if [[ -f "$dest/SKILL.md" || -z "$(ls -A "$dest" 2>/dev/null)" ]]; then
      rm -rf "$dest"
    else
      err "$dest exists but does not look like a previous skillforge install; refusing to overwrite."
      exit 1
    fi
  fi

  if [[ "$MODE" == "link" ]]; then
    ln -s "$SRC_DIR" "$dest"
  else
    cp -R "$SRC_DIR" "$dest"
  fi

  ok "$label → $dest"
  DEST_LIST+=("$dest")
done

echo
echo "Verify:"
for d in "${DEST_LIST[@]}"; do
  info "python3 $d/scripts/skill_guide.py --list"
done
echo
echo "Next:"
info "1. Restart your agent so it picks up the new skill."
info "2. Ask it to read the skill, or open SKILL.md yourself:"
info "   python3 ~/.codebuddy/skills/$SKILL_NAME/scripts/skill_guide.py --new \"my workflow\""
