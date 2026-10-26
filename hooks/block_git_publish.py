#!/usr/bin/env python3
# ABOUTME: PreToolUse hook for Bash. Blocks git commands that create commits or publish work
# (commit, push, tag, rebase, merge, cherry-pick, revert) and gh PR create/merge, in any form.
# Permission deny rules only match the literal text `git commit ...`; this also catches
# `git -C <dir> commit`, `git -c k=v push`, quoted subcommands, subshells and `bash -c "..."`.

import json
import re
import shlex
import sys

BLOCKED_GIT_SUBCOMMANDS = {"commit", "push", "tag", "rebase", "merge", "cherry-pick", "revert"}
BLOCKED_GH_SUBCOMMANDS = {("pr", "create"), ("pr", "merge")}
COMMAND_RUNNERS = {"bash", "sh", "zsh", "dash", "eval", "env", "sudo", "xargs", "ssh", "watch", "nohup", "time"}
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix"}
BLOCK_EXIT_CODE = 2
MAX_NESTING_DEPTH = 5
HEREDOC_MARKER = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
SEPARATORS = re.compile(r"&&|\|\||\|&|[;&|\n`()]|\$\(")


def find_violation(command, depth=0):
    if depth > MAX_NESTING_DEPTH:
        return None
    command = drop_data_heredocs(command)
    for segment in SEPARATORS.split(command):
        tokens = split_tokens(segment)
        violation = violation_in_tokens(tokens)
        if violation:
            return violation
    return violation_in_quoted_arguments(command, depth)


def drop_data_heredocs(command):
    """Remove heredoc bodies that are plain data (cat, python3, ...). Bodies fed to a shell stay."""
    kept = []
    body = []
    delimiter = None
    body_is_script = False
    for line in command.split("\n"):
        if delimiter is None:
            kept.append(line)
            marker = HEREDOC_MARKER.search(line)
            if marker:
                delimiter = marker.group(2)
                body_is_script = runs_arguments(split_tokens(line))
            continue
        if line.strip() == delimiter:
            kept.extend(body if body_is_script else [])
            kept.append(line)
            delimiter, body = None, []
        else:
            body.append(line)
    kept.extend(body)  # unterminated heredoc: keep everything visible to the scan
    return "\n".join(kept)


def violation_in_quoted_arguments(command, depth):
    tokens = split_tokens(command)
    if not runs_arguments(tokens):
        return None
    for token in tokens:
        if " " in token:
            nested = find_violation(token, depth + 1)
            if nested:
                return nested
    return None


def runs_arguments(tokens):
    return any(token.rsplit("/", 1)[-1] in COMMAND_RUNNERS for token in tokens)


def split_tokens(segment):
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def violation_in_tokens(tokens):
    for index, token in enumerate(tokens):
        program = token.rsplit("/", 1)[-1]
        if program == "git":
            subcommand = git_subcommand(tokens[index + 1:])
            if subcommand in BLOCKED_GIT_SUBCOMMANDS:
                return f"git {subcommand}"
        if program == "gh":
            rest = [t for t in tokens[index + 1:] if not t.startswith("-")]
            if tuple(rest[:2]) in BLOCKED_GH_SUBCOMMANDS:
                return "gh " + " ".join(rest[:2])
    return None


def git_subcommand(args):
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in GIT_OPTIONS_WITH_VALUE:
            skip_next = True
            continue
        if arg.startswith("-"):
            continue
        return arg
    return None


def main():
    payload = json.load(sys.stdin)
    command = payload.get("tool_input", {}).get("command", "")
    violation = find_violation(command)
    if violation:
        print(
            f"Blocked: '{violation}'. The user does all commits and pushes; "
            "leave changes in the working tree.",
            file=sys.stderr,
        )
        return BLOCK_EXIT_CODE
    return 0


if __name__ == "__main__":
    sys.exit(main())
