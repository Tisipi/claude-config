# Claude Config

Portable Claude Code configuration for use across multiple development projects.

## Setup

Clone this repository and run the setup script:

```bash
git clone git@github.com:youruser/claude-config.git ~/claude-config
cd ~/claude-config
chmod +x setup.sh
./setup.sh
```

This creates symlinks from `~/.claude/` to this repository.

## Structure

```
claude-config/
├── CLAUDE.md              # Instructions for working on this repo itself
├── global/
│   └── CLAUDE.md          # Global instructions (applies to all projects, linked to ~/.claude/)
├── hooks/
│   ├── block_git_publish.py        # PreToolUse hook: blocks git commit/push and friends
│   └── test_block_git_publish.py   # Its tests
├── settings/
│   ├── settings.shared.json        # Shared, generic part of ~/.claude/settings.json
│   ├── merge_settings.py           # Merges it into ~/.claude/settings.json (additive)
│   └── test_merge_settings.py      # Its tests
├── statusline/
│   └── statusline-command.sh       # Status line: model, directory, git branch, context % (needs jq)
├── setup.sh               # Links everything into ~/.claude/ and merges the shared settings
├── rules/                 # Language guides, path-scoped: load when Claude touches matching files
│   ├── csharp.md          # *.cs, *.csproj, .editorconfig, ...
│   └── java.md            # *.java, pom.xml, *.gradle
├── skills/                # One folder per skill: SKILL.md (+ optional reference files)
│   ├── conductor-sharp/   # ConductorSharp guide: SKILL.md + task-types, configuration, orchestration, testing
│   ├── hone-idea/         # /hone-idea - Develop spec through Q&A
│   ├── plan/              # /plan - Generate implementation plan
│   ├── continue/          # /continue - Execute next step
│   ├── find-missing-tests/    # /find-missing-tests - Identify missing test cases
│   ├── fix-missing-tests/     # /fix-missing-tests - Implement missing tests
│   ├── security-review-full/  # /security-review-full - Full codebase security review
│   ├── security-review-area/  # /security-review-area - Targeted security review
│   ├── fix-security-issues/   # /fix-security-issues - Fix security vulnerabilities
│   ├── diagram/           # /diagram - Create architecture diagram
│   └── repomix/           # /repomix - Generate LLM-friendly repository dump
└── tests/
    └── test_setup.py      # Runs setup.sh against a throwaway HOME
```

`CLAUDE.md` in `~/.claude/` is a link to `global/CLAUDE.md`; the `CLAUDE.md` in the repo root only applies when working on this repo.

## Usage

Language guides and the ConductorSharp guide load on their own:

- **C# and Java** are path-scoped rules. They load the first time Claude reads, writes or edits a matching file (`*.cs`, `*.java`, ...), not at session start
- **ConductorSharp** is a skill: Claude loads it when the task involves Conductor workflows. Its larger reference files are read only when needed

## Development Workflow

### Starting a New Project (Greenfield)

```
1. /hone-idea      Start Q&A to develop requirements
                   → Creates: spec.md

2. /plan           Generate implementation plan from spec
                   → Creates: prompt_plan.md, todo.md

3. /continue       Execute next step (repeat until done)
                   → Implements step with TDD
                   → Updates todo.md
                   → Leaves the changes uncommitted: you review and commit
```

Use any current model for these steps; a more capable one pays off for `/plan`.

### Working on Existing Projects (Brownfield)

```
1. Work normally            The language rules load when Claude touches matching files
2. Mention Conductor        The conductor-sharp skill loads when the task needs it
```

#### Repository Context Tools

For large brownfield projects, use repository dumping tools to provide Claude with full codebase context in a single document. This is more efficient than exploring files incrementally.

**Tip:** Use the `/repomix` command for an interactive prompt that generates the right repomix command for your needs.

**Available tools:**
- **[repomix](https://github.com/yamadashy/repomix)** — Recommended. Generates markdown with file tree and code, respects .gitignore
- **[repo2txt](https://github.com/donoceidon/repo2txt)** — Text-based output, similar functionality
- **[files-to-prompt](https://github.com/simonw/files-to-prompt)** — Converts files to LLM-friendly format

**Installation:**
```bash
npm install -g repomix
```

**Usage:**

**Without `--include` (default, full dump):**
```bash
# Includes ALL files in the repository (except .gitignore'd items)
# Language-agnostic—good for multi-language repos or unknown codebases
repomix /path/to/repo --output context.md
```

**With `--include` (filtered, language-specific):**
```bash
# Include only specific file types to reduce context size
# Filter by file types (use recursive glob **/pattern)
repomix /path/to/repo --output context.md --include "**/*.cs,**/*.csproj,**/*.sln"

# For C# projects with config files
repomix /path/to/csharp-project --output context.md \
  --include "**/*.cs,**/*.csproj,**/*.sln,**/*.yaml,**/*.yml,**/*.json"

# Common language patterns:
# TypeScript/JavaScript: "**/*.ts,**/*.tsx,**/*.js,**/*.json"
# Python: "**/*.py,**/*.toml,**/*.yaml"
# Java: "**/*.java,**/*.gradle,**/*.properties"
```

**Glob Pattern Tips:**
- Use `**/` prefix for recursive matching through all subdirectories
- Without `**/`, patterns only match files in the root directory
- Comma-separate multiple patterns
- Exclude files via `.gitignore` (automatically respected)


### Key Principles

- **TDD**: Write tests before implementation
- **Small steps**: Each step should be self-contained
- **You commit**: Claude never commits or pushes (see Safety Guards); commit after reviewing each completed step
- **spec.md**: Source of truth for requirements
- **prompt_plan.md**: Step-by-step implementation guide
- **todo.md**: Track progress with checkboxes

## Available Skills (slash commands)

### Greenfield (New Project Development)

| Command | Purpose |
|---------|---------|
| `/hone-idea` | Develop spec through Q&A |
| `/plan` | Generate implementation plan from spec.md |
| `/continue` | Execute next step from prompt_plan.md |

### Code Quality & Review

| Command | Purpose | Output File |
|---------|---------|------------|
| `/find-missing-tests` | Identify missing test cases | `missing-tests.md` |
| `/fix-missing-tests` | Implement missing tests | — |
| `/security-review-full` | Full codebase security review | `security-issues.md` |
| `/security-review-area <area>` | Security review of a specific code area | `security-issues.md` |
| `/fix-security-issues` | Fix security vulnerabilities | — |

For reviewing code changes, use the built-in `/code-review` (add `--fix` to apply the findings) and `/security-review` (pending changes on the branch). The skills above cover what those do not: whole-codebase and per-area security reviews, and missing-test analysis.

### Architecture & Documentation

| Command | Purpose | Requirements |
|---------|---------|--------------|
| `/diagram` | Create architecture diagram from spec files | Graphviz installed |

### Stack-Specific Conventions

Not commands: see Usage above (`rules/` and `skills/`).

## Command Workflows

### Development Workflow Example
```bash
/hone-idea         # Define requirements → spec.md
/plan              # Create plan → prompt_plan.md, todo.md
/continue          # Implement each step (repeat)
/continue
/diagram           # Create architecture visualization
```

### Code Quality Workflow Example
```bash
/code-review --fix       # Built-in: review the current changes and apply the findings
/find-missing-tests      # Identify gaps → missing-tests.md
/fix-missing-tests       # Implement missing tests
/security-review-full    # Check security → security-issues.md
/fix-security-issues     # Fix vulnerabilities
```

### Targeted Review Workflow
```bash
# Deep dive into security concerns
/security-review-area    # (after specifying area of concern)
```

## Diagram Command (requires Graphviz)

The `/diagram` command creates a visual architecture diagram from your project documentation using Graphviz. This helps visualize components, dependencies, and data flows.

**Installation:**

```bash
# macOS (Homebrew)
brew install graphviz

# Linux (Debian/Ubuntu)
sudo apt-get install graphviz

# Linux (Fedora)
sudo dnf install graphviz

# Windows (Chocolatey)
choco install graphviz
```

After installation, you can use `/diagram` to auto-generate `project.dot` and `project.svg` files. The SVG file provides a scalable visual representation suitable for documentation and version control.

### ast-grep (Code Analysis Tool)

`ast-grep` (`sg`) is the preferred tool for code analysis, searching, and refactoring across the codebase. It understands code structure (AST) rather than just text patterns, making it much more powerful than regex-based tools.

**Installation:**

```bash
# macOS (Homebrew)
brew install ast-grep

# npm (cross-platform)
npm install -g @ast-grep/cli

# Linux (Debian/Ubuntu)
curl -LSs https://github.com/ast-grep/ast-grep/releases/latest/download/app-x86_64-unknown-linux-gnu.zip -o /tmp/ast-grep.zip && unzip -o /tmp/ast-grep.zip -d /usr/local/bin

# Windows (Chocolatey)
choco install ast-grep
```

**Verify installation:**
```bash
sg --version
```

Use `sg` for finding patterns, refactoring code, and understanding code structure across projects.

## Safety Guards

Claude never commits or pushes: the user does all version control. Unrelated bugs Claude notices while working are appended to `ISSUES.md` in the project root instead of being fixed on the side. `global/CLAUDE.md` states the rule, but instructions are advisory, so it is enforced in three layers:

| Layer | Where | What it does |
|---|---|---|
| Deny rules | `~/.claude/settings.json` | Block `git commit` (incl. `--amend`), `push`, `tag`, `rebase`, `merge`, `cherry-pick`, `revert`, `gh pr create`, `gh pr merge` |
| Ask rules | `~/.claude/settings.json` | Prompt before `git reset --hard`, `clean`, `checkout --`, `restore`, `branch -D`, `stash drop/clear` (possible data loss) |
| PreToolUse hook | `hooks/block_git_publish.py` | Parses the Bash command and blocks the same git/gh operations in any form |

Why the hook: deny rules match the literal command text. Per the Claude Code docs they do not catch `git -C . push`, `git -c k=v push` or `git 'push'`, and `git -C <dir>` is a form Claude uses when working across directories. The hook also sees through `&&`, `;`, `$(...)`, `/usr/bin/git`, `sudo`, `xargs`, `bash -c "..."` and heredocs fed to a shell. Heredocs that are plain data (`cat <<EOF`, `python3 - <<EOF`) are ignored, so documentation text mentioning git commands is not blocked. Read-only git (`status`, `diff`, `log`) is untouched.

Limit: it inspects the command text only. A script that runs `git commit` internally is not caught.

### Shared settings

`~/.claude/settings.json` holds personal settings (voice, plugins, model, permission mode, and every "don't ask again" rule Claude Code adds), so it is **not** tracked. Only the shared part lives in this repo, in `settings/settings.shared.json`: the deny and ask rules above, the hook registration and the status line registration (an existing `statusLine` in `settings.json` wins).

`setup.sh` links `hooks/` to `~/.claude/hooks` and merges the shared file into `~/.claude/settings.json` with `settings/merge_settings.py`:
- Additive: lists are unioned, objects merged recursively, existing scalar values win. Nothing you already have is removed or overridden
- Idempotent: running it again changes nothing. When it does change the file, the previous version is saved as `settings.json.bak`
- Invalid JSON in `settings.json` aborts the merge and leaves the file untouched
- Preview without writing: `python3 settings/merge_settings.py --dry-run`
- Limit: list entries are matched by equality, so if a shared hook command is ever changed, the old entry has to be removed from `settings.json` by hand

Tests (stdlib only), run from the repo root:

```bash
python3 -m unittest discover -s hooks -v
python3 -m unittest discover -s settings -v
python3 -m unittest discover -s tests -v
```

Change the hook and the merge script only together with their tests. To verify the guard in a live session, run `git -C . commit --dry-run`: it must be blocked.

## Adding New Stacks

- **A language guide**: add `rules/<language>.md` with a `paths:` list in its frontmatter (for example `"**/*.go"`). `setup.sh` links it into `~/.claude/rules/`
- **A framework or library guide** (large, needed only for some tasks): add `skills/<name>/SKILL.md` with a specific `description` (it is the trigger), keep `SKILL.md` under 500 lines and move detail into reference files linked from it
- Run `python3 -m unittest discover -s tests -v`, then review the change; you commit and push

## Sources

- https://harper.blog/2025/02/16/my-llm-codegen-workflow-atm/
- https://harper.blog/2025/05/08/basic-claude-code/
- https://github.com/harperreed/dotfiles/tree/master/.claude
- https://github.com/harperreed/dotfiles/blob/master/.claude/CLAUDE.md
- https://github.com/obra/dotfiles/blob/main/.claude/CLAUDE.md

Claude Code documentation (consulted 2026-10-26):

- https://code.claude.com/docs/en/memory (CLAUDE.md, `.claude/rules/`, auto memory)
- https://code.claude.com/docs/en/best-practices (writing an effective CLAUDE.md, verification, hooks, skills)
- https://code.claude.com/docs/en/skills (SKILL.md format, frontmatter, commands merged into skills)

Java documentation (consulted 2026-11-04), used for `rules/java.md`:

- https://openjdk.org/projects/jdk/21/ and https://openjdk.org/projects/jdk/25/ (which JEPs are final: virtual threads, pattern matching for switch, record patterns, sequenced collections, scoped values)
- https://openjdk.org/jeps/491 (`synchronized` no longer pins virtual threads, Java 24)
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html (`Optional` as a return type)
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ExecutorService.html (`close()`, since 19)
- https://google.github.io/styleguide/javaguide.html (Google Java Style)
- https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html (constructor injection)
- https://docs.spring.io/spring-boot/reference/features/external-config.html (`@ConfigurationProperties` with records)
- https://docs.spring.io/spring-boot/reference/testing/testcontainers.html (`@ServiceConnection`)
- https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html (`spring.threads.virtual.enabled`)
- https://maven.apache.org/plugins/maven-compiler-plugin/compile-mojo.html (`maven.compiler.release`)
- https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html (dependencyManagement, BOM import)
- https://docs.gradle.org/current/userguide/toolchains.html (Java toolchains)
- https://docs.junit.org/6.0.2/release-notes (JUnit 6 requires Java 17)


## Notes and Things to do

Plugins.   
Skills.   
Pre-commit hooks.   

**TODO:** document rollback phases (preparation, feasibility, fulfillment rollback) in the ConductorSharp orchestration chapter.
