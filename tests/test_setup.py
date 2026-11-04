# ABOUTME: Tests for setup.sh: runs it against a throwaway HOME and checks what gets linked into ~/.claude/.
# Run from the repo root: python3 -m unittest discover -s tests -v
# Personal files already in ~/.claude must survive, and a second run must change nothing.

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class SetupScriptTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.claude = self.home / ".claude"

    def run_setup(self):
        return subprocess.run(
            ["bash", str(REPO / "setup.sh")],
            env={**os.environ, "HOME": str(self.home)},
            capture_output=True,
            text=True,
            check=False,
        )

    def test_links_each_rule_file_into_user_rules(self):
        result = self.run_setup()

        self.assertEqual(0, result.returncode, result.stderr)
        for rule in (REPO / "rules").glob("*.md"):
            link = self.claude / "rules" / rule.name
            self.assertTrue(link.is_symlink(), rule.name)
            self.assertEqual(rule.resolve(), link.resolve())

    def test_keeps_personal_rules_that_are_not_part_of_the_repo(self):
        personal = self.claude / "rules" / "personal.md"
        personal.parent.mkdir(parents=True)
        personal.write_text("mine")

        self.run_setup()

        self.assertFalse(personal.is_symlink())
        self.assertEqual("mine", personal.read_text())

    def test_second_run_succeeds_and_creates_no_nested_links(self):
        self.run_setup()
        result = self.run_setup()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((REPO / "rules" / "rules").exists())

    def test_links_each_skill_folder_into_user_skills(self):
        self.run_setup()

        for skill in (REPO / "skills").iterdir():
            link = self.claude / "skills" / skill.name
            self.assertTrue(link.is_symlink(), skill.name)
            self.assertEqual(skill.resolve(), link.resolve())

    def test_keeps_personal_skills_that_are_not_part_of_the_repo(self):
        personal = self.claude / "skills" / "mine" / "SKILL.md"
        personal.parent.mkdir(parents=True)
        personal.write_text("mine")

        self.run_setup()

        self.assertEqual("mine", personal.read_text())

    def test_removes_retired_links_into_the_repo_but_not_foreign_ones(self):
        for retired in ("stacks", "commands"):
            with self.subTest(retired=retired):
                self.claude.mkdir(exist_ok=True)
                link = self.claude / retired
                os.symlink(REPO / retired, link)
                self.run_setup()
                self.assertFalse(link.is_symlink())

                foreign = self.home / f"elsewhere-{retired}"
                foreign.mkdir()
                os.symlink(foreign, link)
                self.run_setup()
                self.assertTrue(link.is_symlink())
                link.unlink()

    def test_rules_are_scoped_to_their_language_files(self):
        csharp = (REPO / "rules" / "csharp.md").read_text()

        self.assertTrue(csharp.startswith("---\npaths:"))
        self.assertIn('"**/*.cs"', csharp.split("---")[1])


class SkillFileTests(unittest.TestCase):
    def test_every_skill_has_a_matching_name_and_a_bounded_description(self):
        for skill in (REPO / "skills").iterdir():
            with self.subTest(skill=skill.name):
                text = (skill / "SKILL.md").read_text()
                front = text.split("---")[1]
                self.assertIn(f"name: {skill.name}\n", front)
                description = next(l for l in front.splitlines() if l.startswith("description:"))
                self.assertLessEqual(len(description), 1536)
                self.assertLess(len(text.splitlines()), 500)

    def test_no_skill_tells_claude_to_commit_or_push(self):
        for skill in (REPO / "skills").rglob("*.md"):
            for number, line in enumerate(skill.read_text().splitlines(), 1):
                with self.subTest(file=skill.name, line=number):
                    lowered = line.lower()
                    if "commit" in lowered or "push" in lowered:
                        allowed = ("do not commit", "never", "without committing", "uncommitted", "suggest a commit message")
                        self.assertTrue(any(phrase in lowered for phrase in allowed), line)

    def test_skill_links_to_reference_files_resolve(self):
        import re
        for skill in (REPO / "skills").iterdir():
            text = (skill / "SKILL.md").read_text()
            for target in re.findall(r"\]\(([\w./-]+\.md)\)", text):
                with self.subTest(skill=skill.name, target=target):
                    self.assertTrue((skill / target).exists())


if __name__ == "__main__":
    unittest.main()
