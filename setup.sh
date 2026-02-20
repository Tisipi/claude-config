#!/bin/bash
# setup.sh - Links claude-config to ~/.claude/

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

# Create ~/.claude if it doesn't exist
mkdir -p "$CLAUDE_DIR"

# Symlink CLAUDE.md
ln -sf "$SCRIPT_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"

# Symlink commands directory
ln -sf "$SCRIPT_DIR/commands" "$CLAUDE_DIR/commands"

# Symlink stacks directory
ln -sf "$SCRIPT_DIR/stacks" "$CLAUDE_DIR/stacks"

echo "Claude config linked from $SCRIPT_DIR to $CLAUDE_DIR"
