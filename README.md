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
├── commands/              # Custom slash commands
│   ├── hone-idea.md       # /hone-idea - Develop spec through Q&A
│   ├── plan.md            # /plan - Generate implementation plan
│   ├── continue.md        # /continue - Execute next step
│   ├── review-session.md  # /review-session - Review code for issues
│   ├── review-fix.md      # /review-fix - Fix issues from review-comments.md
│   ├── find-missing-tests.md       # /find-missing-tests - Identify missing test cases
│   ├── fix-missing-tests.md        # /fix-missing-tests - Implement missing tests
│   ├── security-review-full.md     # /security-review-full - Full codebase security review
│   ├── security-review-area.md     # /security-review-area - Targeted security review
│   ├── fix-security-issues.md      # /fix-security-issues - Fix security vulnerabilities
│   ├── diagram.md         # /diagram - Create architecture diagram
│   ├── use-java.md        # /use-java - Load Java conventions
│   ├── use-csharp.md      # /use-csharp - Load C# conventions
│   ├── use-conductor-sharp.md  # /use-conductor-sharp - Load ConductorSharp conventions
│   └── repomix.md       # /repomix - Generate LLM-friendly repository dump
└── stacks/                # Stack-specific instructions
    ├── java.md
    ├── csharp.md
    └── conductor-sharp.md
```

## Usage

In any project, run the relevant stack command:

```
/use-java
/use-csharp
/use-conductor-sharp
```

## Development Workflow

### Starting a New Project (Greenfield)

```
1. /hone-idea      Start Q&A to develop requirements
                   Model: Conversational (GPT-4o, Claude)
                   → Creates: spec.md

2. /plan           Generate implementation plan from spec
                   Model: Reasoning (o1, o3, r1)
                   → Creates: prompt_plan.md, todo.md

3. /continue       Execute next step (repeat until done)
                   Model: Claude Code
                   → Implements step with TDD
                   → Commits changes
                   → Updates todo.md

Note: models are outdated 
```

### Working on Existing Projects (Brownfield)

```
1. /use-java                Load stack conventions (or /use-csharp, /use-conductor-sharp, etc.)
2. Work normally            Claude follows the loaded conventions
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
- **Commit often**: After each completed step
- **spec.md**: Source of truth for requirements
- **prompt_plan.md**: Step-by-step implementation guide
- **todo.md**: Track progress with checkboxes

## Available Commands

### Greenfield (New Project Development)

| Command | Purpose |
|---------|---------|
| `/hone-idea` | Develop spec through Q&A |
| `/plan` | Generate implementation plan from spec.md |
| `/continue` | Execute next step from prompt_plan.md |

### Code Quality & Review

| Command | Purpose | Output File |
|---------|---------|------------|
| `/review-session` | Review code for bugs, clarity, and issues | `review-comments.md` |
| `/review-fix` | Fix issues from review-comments.md | — |
| `/find-missing-tests` | Identify missing test cases | `missing-tests.md` |
| `/fix-missing-tests` | Implement missing tests | — |
| `/security-review-full` | Full codebase security review | `security-issues.md` |
| `/security-review-area` | Security review of specific code area | `security-issues.md` |
| `/fix-security-issues` | Fix security vulnerabilities | — |

### Architecture & Documentation

| Command | Purpose | Requirements |
|---------|---------|--------------|
| `/diagram` | Create architecture diagram from spec files | Graphviz installed |

### Stack-Specific Conventions

| Command | Purpose |
|---------|---------|
| `/use-java` | Load Java development conventions |
| `/use-csharp` | Load C# development conventions |
| `/use-conductor-sharp` | Load ConductorSharp workflow orchestration conventions |

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
/review-session           # Identify issues → review-comments.md
/review-fix              # Fix reported issues
/find-missing-tests      # Identify gaps → missing-tests.md
/fix-missing-tests       # Implement missing tests
/security-review-full    # Check security → security-issues.md
/fix-security-issues     # Fix vulnerabilities
```

### Targeted Review Workflows
```bash
# Review specific area for issues
/review-area             # (after specifying area)

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

Claude never commits or pushes: the user does all version control. `global/CLAUDE.md` states the rule, but instructions are advisory, so it is enforced in three layers:

| Layer | Where | What it does |
|---|---|---|
| Deny rules | `~/.claude/settings.json` | Block `git commit` (incl. `--amend`), `push`, `tag`, `rebase`, `merge`, `cherry-pick`, `revert`, `gh pr create`, `gh pr merge` |
| Ask rules | `~/.claude/settings.json` | Prompt before `git reset --hard`, `clean`, `checkout --`, `restore`, `branch -D`, `stash drop/clear` (possible data loss) |
| PreToolUse hook | `hooks/block_git_publish.py` | Parses the Bash command and blocks the same git/gh operations in any form |

Why the hook: deny rules match the literal command text. Per the Claude Code docs they do not catch `git -C . push`, `git -c k=v push` or `git 'push'`, and `git -C <dir>` is a form Claude uses when working across directories. The hook also sees through `&&`, `;`, `$(...)`, `/usr/bin/git`, `sudo`, `xargs`, `bash -c "..."` and heredocs fed to a shell. Heredocs that are plain data (`cat <<EOF`, `python3 - <<EOF`) are ignored, so documentation text mentioning git commands is not blocked. Read-only git (`status`, `diff`, `log`) is untouched.

Limit: it inspects the command text only. A script that runs `git commit` internally is not caught.

### Shared settings

`~/.claude/settings.json` holds personal settings (voice, plugins, model, permission mode, and every "don't ask again" rule Claude Code adds), so it is **not** tracked. Only the shared part lives in this repo, in `settings/settings.shared.json`: the deny and ask rules above and the hook registration.

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
```

Change the hook and the merge script only together with their tests. To verify the guard in a live session, run `git -C . commit --dry-run`: it must be blocked.

## Adding New Stacks

1. Create a new file in `stacks/` (e.g., `typescript.md`)
2. Create a corresponding command in `commands/` (e.g., `use-typescript.md`)
3. Commit and push


## Sources

- https://harper.blog/2025/02/16/my-llm-codegen-workflow-atm/
- https://harper.blog/2025/05/08/basic-claude-code/
- https://github.com/harperreed/dotfiles/tree/master/.claude
- https://github.com/harperreed/dotfiles/blob/master/.claude/CLAUDE.md
- https://github.com/obra/dotfiles/blob/main/.claude/CLAUDE.md

Claude Code documentation (consulted 2026-10-26):

- https://code.claude.com/docs/en/memory (CLAUDE.md, `.claude/rules/`, auto memory)
- https://code.claude.com/docs/en/best-practices (writing an effective CLAUDE.md, verification, hooks, skills)
- https://code.claude.com/docs/en/skills (SKILL.md format, commands merged into skills)


## Notes and Things to do

Plugins.   
Skills.   
Pre-commit hooks.   
Block dangerous git commands.   

**TODO: update this README once the modernisation is done.** It is stale in at least these places:

- Structure and Usage: `commands/` and `stacks/` will become skills and rules (see the modernisation plan)
- `setup.sh` description: it must also link the new skills/rules folders
- Greenfield workflow: names outdated models and says `/continue` commits, which contradicts the "never commit or push" rule in `CLAUDE.md`
- "Key Principles" says "Commit often" (same contradiction)
- "Adding New Stacks" ends with "Commit and push"
- "Targeted Review Workflows" mentions `/review-area`, which does not exist
- Structure tree: add the `hooks/` folder (the git guard itself is documented under Safety Guards)
- Sources: keep the Claude documentation list above in sync with what was actually consulted
