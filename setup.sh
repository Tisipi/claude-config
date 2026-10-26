#!/bin/bash
# setup.sh - Links claude-config to ~/.claude/

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

# Create ~/.claude if it doesn't exist
mkdir -p "$CLAUDE_DIR"

# Symlink global instructions (the repo root CLAUDE.md is for this repo itself)
ln -sf "$SCRIPT_DIR/global/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"

# Symlink commands directory
ln -sfn "$SCRIPT_DIR/commands" "$CLAUDE_DIR/commands"

# Symlink stacks directory
ln -sfn "$SCRIPT_DIR/stacks" "$CLAUDE_DIR/stacks"

# Symlink hooks directory (git guard referenced from ~/.claude/settings.json)
ln -sfn "$SCRIPT_DIR/hooks" "$CLAUDE_DIR/hooks"

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
