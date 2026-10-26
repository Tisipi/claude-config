# ABOUTME: Tests for merge_settings.py, which merges the shared Claude Code settings into ~/.claude/settings.json.
# Run from the repo root: python3 -m unittest discover -s settings -v
# The merge must be additive and idempotent: it may never remove or override a user's own settings.

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from merge_settings import merge, merge_files

SETTINGS_DIR = Path(__file__).parent
SHARED_PATH = SETTINGS_DIR / "settings.shared.json"
SCRIPT_PATH = SETTINGS_DIR / "merge_settings.py"
HOOK_ENTRY = {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 -I ~/.claude/hooks/guard.py"}]}


class MergeTests(unittest.TestCase):
    def test_unions_lists_without_duplicates_and_keeps_existing_entries(self):
        shared = {"permissions": {"deny": ["Bash(git push *)", "Bash(git commit *)"]}}
        existing = {"permissions": {"deny": ["Bash(rm -rf *)", "Bash(git push *)"]}}

        merged = merge(shared, existing)

        self.assertEqual(["Bash(rm -rf *)", "Bash(git push *)", "Bash(git commit *)"], merged["permissions"]["deny"])

    def test_adds_a_nested_hook_entry_once(self):
        shared = {"hooks": {"PreToolUse": [HOOK_ENTRY]}}

        once = merge(shared, {})
        twice = merge(shared, once)

        self.assertEqual([HOOK_ENTRY], twice["hooks"]["PreToolUse"])

    def test_keeps_unrelated_personal_settings(self):
        shared = {"permissions": {"deny": ["Bash(git push *)"]}}
        existing = {"voice": {"enabled": True}, "permissions": {"defaultMode": "auto", "allow": ["Bash(ls *)"]}}

        merged = merge(shared, existing)

        self.assertEqual({"enabled": True}, merged["voice"])
        self.assertEqual("auto", merged["permissions"]["defaultMode"])
        self.assertEqual(["Bash(ls *)"], merged["permissions"]["allow"])

    def test_existing_scalar_wins_over_shared_scalar(self):
        merged = merge({"theme": "dark"}, {"theme": "light"})

        self.assertEqual("light", merged["theme"])

    def test_scalar_is_added_when_missing(self):
        self.assertEqual("dark", merge({"theme": "dark"}, {})["theme"])

    def test_does_not_modify_its_inputs(self):
        shared = {"permissions": {"deny": ["a"]}}
        existing = {"permissions": {"deny": ["b"]}}

        merge(shared, existing)

        self.assertEqual({"permissions": {"deny": ["a"]}}, shared)
        self.assertEqual({"permissions": {"deny": ["b"]}}, existing)


class MergeFilesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.shared = self.dir / "shared.json"
        self.target = self.dir / "settings.json"
        self.shared.write_text(json.dumps({"permissions": {"deny": ["Bash(git push *)"]}}))

    def test_creates_the_target_when_missing(self):
        changed = merge_files(self.shared, self.target)

        self.assertTrue(changed)
        self.assertEqual(["Bash(git push *)"], json.loads(self.target.read_text())["permissions"]["deny"])

    def test_second_run_changes_nothing_and_leaves_bytes_identical(self):
        merge_files(self.shared, self.target)
        before = self.target.read_bytes()

        changed = merge_files(self.shared, self.target)

        self.assertFalse(changed)
        self.assertEqual(before, self.target.read_bytes())

    def test_writes_a_backup_of_the_previous_content_only_when_it_changes(self):
        self.target.write_text(json.dumps({"voice": {"enabled": True}}))
        backup = self.dir / "settings.json.bak"

        merge_files(self.shared, self.target)
        self.assertEqual({"voice": {"enabled": True}}, json.loads(backup.read_text()))

        backup.unlink()
        merge_files(self.shared, self.target)
        self.assertFalse(backup.exists())

    def test_invalid_json_in_the_target_aborts_and_leaves_the_file_untouched(self):
        self.target.write_text("{ not json")

        with self.assertRaises(ValueError):
            merge_files(self.shared, self.target)

        self.assertEqual("{ not json", self.target.read_text())

    def test_dry_run_reports_a_change_without_writing(self):
        changed = merge_files(self.shared, self.target, dry_run=True)

        self.assertTrue(changed)
        self.assertFalse(self.target.exists())

    def test_writes_through_a_symlinked_target(self):
        real = self.dir / "real.json"
        real.write_text("{}")
        link = self.dir / "link.json"
        os.symlink(real, link)

        merge_files(self.shared, link)

        self.assertTrue(link.is_symlink())
        self.assertEqual(["Bash(git push *)"], json.loads(real.read_text())["permissions"]["deny"])


class CommandLineTests(unittest.TestCase):
    def test_exit_code_signals_failure_on_invalid_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "settings.json"
            target.write_text("{ not json")

            result = subprocess.run(
                [sys.executable, "-I", str(SCRIPT_PATH), "--shared", str(SHARED_PATH), "--target", str(target)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("not valid JSON", result.stderr)


class CommandLineMessageTests(unittest.TestCase):
    def run_cli(self, target):
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT_PATH), "--shared", str(SHARED_PATH), "--target", str(target)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_reports_creation_without_mentioning_a_backup_when_the_target_did_not_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(Path(tmp) / "settings.json")

        self.assertEqual(0, result.returncode)
        self.assertIn("created", result.stdout)
        self.assertNotIn("saved as", result.stdout)

    def test_reports_the_backup_when_an_existing_target_is_updated(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "settings.json"
            target.write_text("{}")
            result = self.run_cli(target)

        self.assertIn("previous version saved as settings.json.bak", result.stdout)


class SharedSettingsFileTests(unittest.TestCase):
    def setUp(self):
        self.shared = json.loads(SHARED_PATH.read_text())

    def test_denies_commits_and_pushes(self):
        deny = self.shared["permissions"]["deny"]

        self.assertIn("Bash(git commit *)", deny)
        self.assertIn("Bash(git push *)", deny)

    def test_registers_the_git_guard_hook_that_exists_in_the_repo(self):
        commands = [
            hook["command"]
            for entry in self.shared["hooks"]["PreToolUse"]
            for hook in entry["hooks"]
        ]

        self.assertEqual(1, len(commands))
        self.assertIn("hooks/block_git_publish.py", commands[0])
        self.assertTrue((SETTINGS_DIR.parent / "hooks" / "block_git_publish.py").exists())

    def test_contains_no_personal_or_machine_specific_settings(self):
        self.assertEqual({"permissions", "hooks"}, set(self.shared))
        self.assertEqual({"deny", "ask"}, set(self.shared["permissions"]))


if __name__ == "__main__":
    unittest.main()
