#!/bin/bash
# ABOUTME: Claude Code status line: model, current directory, git branch, context percentage used.
# Needs jq; without it the line stays empty instead of failing.

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)
model=$(jq -r '.model.display_name // "?"' <<<"$input")
dir=$(jq -r '.workspace.current_dir // .cwd // ""' <<<"$input")
used=$(jq -r '.context_window.used_percentage // empty | floor' <<<"$input")

branch=$(GIT_OPTIONAL_LOCKS=0 git -C "$dir" branch --show-current 2>/dev/null)

line="$model | ${dir/#$HOME/~}"
[ -n "$branch" ] && line="$line | $branch"
[ -n "$used" ] && line="$line | ctx $used%"
echo "$line"
