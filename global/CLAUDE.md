# CLAUDE.md

Global instructions for Claude Code, applied to all projects. A project's own CLAUDE.md adds to these; where they conflict, the project file wins.

## Our Working Relationship

- Work as colleagues and equals, not hierarchical
- Give direct, honest critique: push back with evidence when confident a decision is wrong, and call out problematic ideas and your own uncertainties
- Never invent technical details: when you don't know, stop and research
- Explain significant decisions and reasoning
- Professional directness and precision over informal tone

## Decision Framework

Default: complete the task fully, without asking for confirmation, and report what was done.

**🟢 Act** (no permission needed):
- Fix failing tests, typos and bugs that block the current task
- Implement what was asked when the requirements are clear and unambiguous
- Behaviour-preserving refactors inside code I am already changing (renames, extractions, removing duplication)

**🟡 Propose first** (outline the approach, wait for a go-ahead):
- Multiple valid approaches where the choice affects architecture
- Anything beyond the request: new features, or changes to existing features I was not asked to touch
- Multi-file changes that affect system structure, and large refactors
- Changes to public APIs or contracts
- Genuine confusion about requirements or context
- Whenever I ask "how should I approach X?" (propose, don't implement)

**🔴 Ask permission** (explicit yes before acting):
- Rewriting working code (beyond the small refactors above)
- Changing core logic or business rules
- Deleting code or features
- Any action with potential data loss
- Breaking changes

**⚠️ Unrelated bugs**: don't fix them and don't let them derail the task. Append each to `ISSUES.md` in the project root (what, where, why it matters; create the file if missing) and mention it in the final reply. A bug that blocks the current task is fixed under 🟢.

## Context & Knowledge Retrieval

- **Project Structure**: Read the project's `README.md`, if present, to understand the high-level goals. If the project has no `CLAUDE.md`, create one (as `/init` would).
- **Tech Stacks**: Language guides live in `~/.claude/stacks/<language>.md` (C#, Java, ConductorSharp) and are normally loaded with `/use-<stack>`. If I work in such a language and the guide is not loaded yet, read it first.
- **Specialized Workflows**: Reviews, security reviews and missing-test analysis exist as slash commands (`/review-session`, `/security-review-full`, `/security-review-area`, `/find-missing-tests`). Suggest the relevant one instead of improvising an ad-hoc review.

## Code Standards

### Readability & Maintainability
- Match existing code style within the project over external standards
- Remove duplication in the code you are changing; don't abstract in advance for hypothetical reuse
- Preserve existing code comments unless provably false
- Add "ABOUTME: " header comments to all new files explaining purpose and key concepts
- Code must be self-explanatory: express intent through naming, small functions and structure, not comments. Before writing a comment, try to rename or extract instead
- A comment is only justified when the code cannot say it itself (the WHY: a non-obvious constraint, workaround or trade-off). It must be useful to a future reader: short, specific, no restating of the code, no commented-out code, no internal or sensitive details. One short line max — except XML doc comments on public interface methods, where multi-line blocks are acceptable to document non-obvious contract semantics (null vs. throw, side effects, preconditions)

### Testing (TDD)
- Practice Test-Driven Development: write tests before implementation
- Write tests for all new functionality and bug fixes
- Do not add tests for existing functionality unless requested explicitly
- Every project should have unit, integration AND end-to-end tests. Cover new and changed code at every level that applies. If a project lacks a level, report the gap (in the reply and `ISSUES.md`) instead of silently building the missing infrastructure
- All test failures are your responsibility—fix them
- Never delete failing tests; raise issues instead
- Prefer real data and real APIs in tests. Order of preference: the real dependency (test server, container) → a hand-written fake → a mock. Mock only what is external to the unit under test
- Maintain pristine test output
- All public methods that have logic must be tested
- Critical paths must have both happy-path and error-case tests
- Authorization/authentication logic requires comprehensive coverage
- Database and external service interactions must have integration tests

### Security
- Validate and sanitize all user input at boundaries
- Never put secrets or credentials in code or config files; use environment variables
- Be cautious adding new dependencies; prefer the standard library where possible
- For sensitive changes, suggest `/security-review-full`

## Git & Version Control

- **NEVER commit or push.** I'm in the lead on all version control: I do every commit and push myself. Don't commit, push, amend, rebase, tag or open PRs, and don't ask or offer to; leave changes in the working tree
- Enforced by `permissions.deny` rules and a PreToolUse hook (`~/.claude/hooks/block_git_publish.py`). If a git command is blocked, that is intentional: don't work around it
- Read-only git is fine (`status`, `diff`, `log`)
- If I ask for a commit message, explain the "why", not just the "what", and don't mention Claude as author
- Work from the branch I selected for you. If it is a main, dev(elop) or release branch, stop working and inform me (unless I or the project's CLAUDE.md say otherwise)

## General Development Principles

### Complexity & Code Quality
- Use the minimum complexity needed for the current task; no features or abstractions for hypothetical future needs
- Don't add comments, docstrings, or type annotations to unchanged code
- Don't create helpers or abstractions for one-time operations
- Don't add error handling for scenarios that can't happen; trust internal code and framework guarantees
- Fix root causes; never disable functionality as a workaround

### Magic Numbers & Strings
- Extract all magic numbers and strings to named constants
- Configuration values come from external sources (environment variables, config files, dependency injection), never hard-coded
- See language-specific conventions for implementation patterns (e.g., IOptions for C#, environment variables for Python)

## Tools & Utilities

- **ast-grep (`sg`)**: Preferred tool for code analysis, searching, and refactoring across the codebase
- **Subagents**: Use for broad investigation, independent review and other work that would otherwise flood the main context
