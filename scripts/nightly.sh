#!/bin/bash
# Nightly Duo wallpaper job (run by launchd at local midnight, or on next wake).
#
#   1. pull the repo
#   2. Claude (headless) runs the duo-wallpaper skill: writes specs/<date>.json,
#      renders latest/, reviews the preview, iterates
#   3. this script checks the output, commits and pushes to main
#
# Claude only gets file tools + the renderer; git is handled here.
#
# Test without publishing:  DRY_RUN=1 WALLPAPER_DATE=2026-11-17 scripts/nightly.sh
# Replace today's design:   FORCE=1 scripts/nightly.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
export TZ=America/Chicago
export PATH="$REPO/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
DATE="${WALLPAPER_DATE:-$(date +%F)}"
DRY_RUN="${DRY_RUN:-0}"
SPEC="specs/$DATE.json"

log() { echo "[$(date '+%F %T')] $*"; }

log "=== Duo wallpaper for $DATE (dry run: $DRY_RUN) ==="

if [ "$DRY_RUN" != 1 ]; then
  git pull --rebase --quiet origin main
fi

REPLACING=""
if [ -f "$SPEC" ]; then
  if [ "${FORCE:-0}" = 1 ]; then
    REPLACING=$(/usr/bin/python3 - "$SPEC" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
print('"%s" (%s, families %s)' % (s["title"], s["style"], ",".join(s.get("families", [])) or "unrecorded"))
PY
)
    log "FORCE=1: replacing today's $REPLACING"
    rm "$SPEC"
  else
    log "$SPEC already exists; today's wallpaper is published. Nothing to do. (FORCE=1 to replace it)"
    exit 0
  fi
fi

if [ ! -x .venv/bin/python ]; then
  log "creating .venv"
  /usr/bin/python3 -m venv .venv
fi
.venv/bin/pip install -q --disable-pip-version-check -r requirements.txt

EXTRA=""
if [ -n "$REPLACING" ]; then
  EXTRA="
- This replaces the earlier design for this date, $REPLACING. Make something clearly different: another style and another colour-family mix."
fi

PROMPT="Use the duo-wallpaper skill (.claude/skills/duo-wallpaper/SKILL.md) to design today's iPhone Duo wallpaper.

- Today's date is $DATE. Write the spec to $SPEC.$EXTRA
- Render with exactly: python generator/render.py $SPEC
- Read latest/preview.png, critique it, and iterate (edit the spec, re-render) per the skill.
- Use the Read/Glob tools to look at recent files in specs/ and at --palette output if needed: python generator/render.py --palette
- Do NOT run git, pip, or any other commands. A wrapper script commits and pushes after you finish.
- Finish with one line: the title, style and families."

# Long-lived token for unattended runs (from `claude setup-token`), kept in the Keychain:
#   security add-generic-password -U -a "$USER" -s duo-wallpaper-claude-token -w
if TOKEN=$(security find-generic-password -a "$USER" -s duo-wallpaper-claude-token -w 2>/dev/null); then
  export CLAUDE_CODE_OAUTH_TOKEN="$TOKEN"
else
  log "note: no Keychain token found; using the normal Claude Code login"
fi

log "running Claude"
claude -p "$PROMPT" \
  --permission-mode acceptEdits \
  --allowedTools "Read" "Write" "Edit" "Glob" "Grep" \
                 "Bash(python generator/render.py *)" \
  --max-turns 40

# Verify Claude produced a complete, valid result before publishing anything.
[ -f "$SPEC" ] || { log "ERROR: Claude did not write $SPEC"; exit 1; }
python - "$SPEC" <<'EOF'
import json, sys
from pathlib import Path
from PIL import Image
spec = json.load(open(sys.argv[1]))
man = json.load(open("latest/manifest.json"))
assert man["date"] == spec["date"], f"latest/ is for {man['date']}, not {spec['date']}"
for m in ("light", "dark"):
    size = Image.open(f"latest/{m}.png").size
    assert size == (1878, 2670), f"{m}.png is {size}"
print(f"verified: {spec['title']} ({spec['style']})")
EOF
TITLE=$(python -c "import json,sys;print(json.load(open(sys.argv[1]))['title'])" "$SPEC")

if [ "$DRY_RUN" = 1 ]; then
  log "dry run: not committing. Output is in latest/ and $SPEC"
  exit 0
fi

git add "$SPEC" latest/
git commit -q -m "Wallpaper $DATE: $TITLE"
for attempt in 1 2 3; do
  if git push -q origin main; then
    log "pushed: $TITLE"
    exit 0
  fi
  log "push failed (attempt $attempt); rebasing and retrying"
  git pull --rebase --quiet origin main || true
  sleep 10
done
log "ERROR: push failed after 3 attempts"
exit 1
