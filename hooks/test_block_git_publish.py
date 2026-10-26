# ABOUTME: Tests for the git guard hook (block_git_publish.py).
# Run from the repo root: python3 -m unittest discover -s hooks -v
# Unit tests call find_violation directly; process tests check the real hook contract (stdin JSON, exit code, stderr).

import json
import subprocess
import sys
import unittest
from pathlib import Path

from block_git_publish import BLOCK_EXIT_CODE, find_violation

HOOK_PATH = Path(__file__).with_name("block_git_publish.py")

BLOCKED_COMMANDS = [
    "git commit -m 'x'",
    "git commit --amend",
    "git push origin main",
    "git -C /some/dir commit -m x",
    "git -c core.x=y push",
    "git 'push' origin",
    "/usr/bin/git push",
    "cd foo && git push",
    "echo hi; git tag v1",
    "echo $(git push)",
    "git --no-pager rebase main",
    "git merge feature",
    "git cherry-pick abc",
    "git revert HEAD",
    "gh pr create --title x",
    "gh pr merge 5",
    "bash -c 'git commit -m x'",
    'sh -c "cd x && git push"',
    "eval 'git tag v1'",
    "xargs git push",
    "sudo git push",
    "cd a && bash -c 'cd b; git commit -m x'",
    "git commit -m \"it's fine\"",
    "bash <<'EOF'\ngit push\nEOF",
    "sh -s <<EOF\ngit commit -m x\nEOF",
    "cat <<EOF\nhi\nEOF\ngit push",
    "cat <<< 'x'\ngit push",
    "cat <<EOF\ngit push",
]

ALLOWED_COMMANDS = [
    "git status",
    "git diff HEAD",
    "git log --oneline --grep=commit",
    "git log --grep 'push'",
    "git -C /some/dir log --oneline",
    "git show HEAD:CLAUDE.md | grep push",
    "git branch --list",
    "git stash list",
    "git status && git diff",
    "gh pr view 5",
    "echo 'git commit is forbidden'",
    'grep -rn "git push" docs',
    "ls -la && dotnet test",
    "",
    "python3 - <<'EOF'\nprint('git commit -m x')\nEOF",
    "cat <<EOF\ngit push origin main\nEOF",
    "cat <<-'DOC'\n\tgit tag v1\n\tDOC\nls",
]


def run_hook(payload):
    return subprocess.run(
        [sys.executable, "-I", str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )


class FindViolationTests(unittest.TestCase):
    def test_blocks_commands_that_commit_or_publish(self):
        for command in BLOCKED_COMMANDS:
            with self.subTest(command=command):
                self.assertIsNotNone(find_violation(command))

    def test_allows_read_only_and_unrelated_commands(self):
        for command in ALLOWED_COMMANDS:
            with self.subTest(command=command):
                self.assertIsNone(find_violation(command))

    def test_reports_which_command_was_blocked(self):
        self.assertEqual("git push", find_violation("git -C . push origin main"))
        self.assertEqual("gh pr create", find_violation("gh pr create --fill"))


class HookProcessTests(unittest.TestCase):
    def test_blocked_command_exits_with_block_code_and_explains_on_stderr(self):
        result = run_hook(json.dumps({"tool_input": {"command": "git -C . commit -m x"}}))

        self.assertEqual(BLOCK_EXIT_CODE, result.returncode)
        self.assertIn("git commit", result.stderr)

    def test_allowed_command_exits_zero_silently(self):
        result = run_hook(json.dumps({"tool_input": {"command": "git status"}}))

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)

    def test_payload_without_command_is_allowed(self):
        self.assertEqual(0, run_hook("{}").returncode)


if __name__ == "__main__":
    unittest.main()
