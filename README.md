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
├── CLAUDE.md              # Global instructions (applies to all projects)
├── commands/              # Custom slash commands
│   ├── hone-idea.md       # /hone-idea - Develop spec through Q&A
│   ├── plan.md            # /plan - Generate implementation plan
│   ├── continue.md        # /continue - Execute next step
│   ├── review.md          # /review - Review code for issues
│   ├── review-fix.md      # /review-fix - Fix issues from review-comments.md
│   ├── find-missing-tests.md       # /find-missing-tests - Identify missing test cases
│   ├── fix-missing-tests.md        # /fix-missing-tests - Implement missing tests
│   ├── security-review.md          # /security-review - Full codebase security review
│   ├── security-review-area.md     # /security-review-area - Targeted security review
│   ├── fix-security-issues.md      # /fix-security-issues - Fix security vulnerabilities
│   ├── diagram.md         # /diagram - Create architecture diagram
│   ├── use-java.md        # /use-java - Load Java conventions
│   ├── use-csharp.md      # /use-csharp - Load C# conventions
│   └── use-conductor-sharp.md  # /use-conductor-sharp - Load ConductorSharp conventions
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
| `/review` | Review code for bugs, clarity, and issues | `review-comments.md` |
| `/review-fix` | Fix issues from review-comments.md | — |
| `/find-missing-tests` | Identify missing test cases | `missing-tests.md` |
| `/fix-missing-tests` | Implement missing tests | — |
| `/security-review` | Full codebase security review | `security-issues.md` |
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
/review                  # Identify issues → review-comments.md
/review-fix              # Fix reported issues
/find-missing-tests      # Identify gaps → missing-tests.md
/fix-missing-tests       # Implement missing tests
/security-review         # Check security → security-issues.md
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
curl -LSs https://github.com/ast-grep/ast-grep/releases/download/0.25.3/ast-grep-x86_64-unknown-linux-gnu.tar.gz | tar xz -C /usr/local/bin

# Windows (Chocolatey)
choco install ast-grep
```

**Verify installation:**
```bash
sg --version
```

Use `sg` for finding patterns, refactoring code, and understanding code structure across projects.

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


## Notes and Things to do

Plugins.   
Skills.   
Pre-commit hooks.   
Block dangerous git commands.   
