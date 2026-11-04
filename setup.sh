#!/bin/bash
# setup.sh - Links claude-config to ~/.claude/

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

# Create ~/.claude if it doesn't exist
mkdir -p "$CLAUDE_DIR"

# Symlink global instructions (the repo root CLAUDE.md is for this repo itself)
ln -sf "$SCRIPT_DIR/global/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"

# Retired: stacks/ became rules/ and skills/, commands/ became skills/. Remove an old link only if it points into this repo
for retired in stacks commands; do
    if [ -L "$CLAUDE_DIR/$retired" ] && [[ "$(readlink "$CLAUDE_DIR/$retired")" == "$SCRIPT_DIR/"* ]]; then
        rm "$CLAUDE_DIR/$retired"
    fi
done

# Symlink each skill folder; other skills in ~/.claude/skills stay untouched
mkdir -p "$CLAUDE_DIR/skills"
for skill in "$SCRIPT_DIR"/skills/*/; do
    ln -sfn "${skill%/}" "$CLAUDE_DIR/skills/$(basename "$skill")"
done

# Symlink each rule file (path-scoped language guides); other files in ~/.claude/rules stay untouched
mkdir -p "$CLAUDE_DIR/rules"
for rule in "$SCRIPT_DIR"/rules/*.md; do
    ln -sf "$rule" "$CLAUDE_DIR/rules/$(basename "$rule")"
done

# Symlink hooks directory (git guard referenced from ~/.claude/settings.json)
ln -sfn "$SCRIPT_DIR/hooks" "$CLAUDE_DIR/hooks"

# Symlink the status line script (registered by the shared settings; needs jq)
ln -sf "$SCRIPT_DIR/statusline/statusline-command.sh" "$CLAUDE_DIR/statusline-command.sh"

# Merge the shared settings (git guard permissions + hook) into settings.json; existing settings are kept
if command -v python3 >/dev/null 2>&1; then
    python3 -I "$SCRIPT_DIR/settings/merge_settings.py" \
        --shared "$SCRIPT_DIR/settings/settings.shared.json" \
        --target "$CLAUDE_DIR/settings.json" \
        || echo "WARNING: settings merge failed; settings.json was left untouched (see README, Shared settings)"
else
    echo "WARNING: python3 not found; merge settings/settings.shared.json into ~/.claude/settings.json manually"
fi

echo "Claude config linked from $SCRIPT_DIR to $CLAUDE_DIR"
