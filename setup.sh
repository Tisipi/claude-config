#!/bin/bash
# setup.sh - Links claude-config to ~/.claude/

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

# Create ~/.claude if it doesn't exist
mkdir -p "$CLAUDE_DIR"

# Symlink global instructions (the repo root CLAUDE.md is for this repo itself)
ln -sf "$SCRIPT_DIR/global/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"

# Symlink commands directory
ln -sf "$SCRIPT_DIR/commands" "$CLAUDE_DIR/commands"

# Symlink stacks directory
ln -sf "$SCRIPT_DIR/stacks" "$CLAUDE_DIR/stacks"

# Symlink hooks directory (git guard referenced from ~/.claude/settings.json)
ln -sfn "$SCRIPT_DIR/hooks" "$CLAUDE_DIR/hooks"

echo "Claude config linked from $SCRIPT_DIR to $CLAUDE_DIR"
