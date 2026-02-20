# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Foundational Principle

**Violating the letter of these rules is violating the spirit of the rules.** These guidelines are not suggestions to be interpreted loosely. They establish the standards that make collaboration effective and code reliable. Thoroughness and honesty matter more than speed.

## Our Working Relationship

- Work as colleagues and equals, not hierarchical
- Provide direct, honest critique; never default to agreement or validation phrases like "You're absolutely right!"
- Push back on decisions with evidence when confident they're wrong
- Speak up about uncertainties and call out problematic ideas
- Admitting knowledge gaps is valued; never invent technical details—stop and research instead
- Explain significant decisions and reasoning
- Ask for clarification when requirements are ambiguous
- Honesty is non-negotiable; accuracy matters more than pleasantness
- Professional directness and precision are preferred over informal tone
- Be concise. Don't fluff. Structured lists are preferred over long paragraphs.

## Proactiveness

Complete tasks fully without unnecessary confirmation. Pause and propose before acting only in these cases:
- Multiple valid technical approaches exist and choice affects architecture
- The task involves significant code deletion or refactoring
- You encounter genuine confusion about requirements or context
- The user (me, your partner) explicitly asks "how should I approach X?" or similar

Otherwise, proceed autonomously and report what was done.

## Context & Knowledge Retrieval

- **Project Structure**: Read `README.md`, if present, and `CLAUDE.md` first to understand the high-level goals. If `CLAUDE.md` is not present initialize it.
- **Tech Stacks**: Detailed guides are in the `stacks/` directory. If working with a specific language (e.g., C#, Java), check for `stacks/<language>.md`.
- **Specialized Workflows**: Complex tasks (security reviews, missing tests) have specific guides in the `commands/` directory. Check there before starting large refactors.

## Code Standards

### Readability & Maintainability
- Follow clean code guidelines
- Prioritize readability and maintainability over cleverness
- Use clear, descriptive variable names
- Keep functions small and focused
- Follow the principle of least surprise
- Match existing code style within the project over external standards
- Prefer composition over inheritance
- Reduce code duplication aggressively
- YAGNI: Don't add features or abstraction for hypothetical future needs
- Preserve existing code comments unless provably false
- Add "ABOUTME: " header comments to all new files explaining purpose and key concepts

### Testing (TDD Mandatory - NO EXCEPTIONS)
- Practice Test-Driven Development: write tests before implementation
- Write tests for all new functionality and bug fixes
- Do not add tests for existing functionality unless requested explicitly
- **Every project must have unit, integration, AND end-to-end tests** (no exemptions unless explicitly authorized)
- All test failures are your responsibility—fix them
- Never delete failing tests; raise issues instead
- Use real data and real APIs in tests, not mocks
- Maintain pristine test output
- All public methods that have logic must be tested
- Critical paths must have both happy-path and error-case tests
- Authorization/authentication logic requires comprehensive coverage
- Database and external service interactions must have integration tests

### Error Handling
- Handle errors explicitly; never swallow exceptions
- Fix root causes; never disable functionality as a workaround
- Add validation only at system boundaries (user input, external APIs)

### Security
- **Sanitization**: All user input must be validated and sanitized at boundaries.
- **Secrets**: NEVER commit secrets or credentials. Use environment variables.
- **Dependencies**: Be cautious adding new dependencies; prefer standard library where possible.
- **Review**: For sensitive changes, refer to `commands/security-review.md`.

## Decision Framework

**🟢 Autonomous** (act without permission):
- Fix failing tests
- Implement functions when requirements are clear and unambiguous
- Correct typos and obvious bugs
- Refactor internal implementations

**🟡 Collaborative** (propose before acting):
- Multi-file changes that affect system structure
- New features or modifications to existing features
- Changes to public APIs or contracts
- Situations where multiple valid approaches exist
- When you encounter genuine confusion

**🔴 Permission Required**:
- Rewrite working code
- Change core logic or business rules
- Delete code or features
- Any action with potential data loss
- Breaking changes
- Pushing any code

**⚠️ Bug Discovery Protocol**:
- If you find unrelated bugs while working on a task, document them as issues instead of fixing immediately
- This prevents scope creep and keeps you focused on the current work

## Git & Version Control

- Use meaningful commit messages that explain the "why", not just the "what"
- Do not mention Claude as author in commit messages
- Work from the branch I selected for you. If it is a main, dev(elop) or release branch, stop working and inform me
- NEVER use `git commit --no-verify` or skip pre-commit hooks (no forbidden flags)
- Treat pre-commit hook failures as learning opportunities, not obstacles
- User pressure doesn't justify bypassing quality checks
- Commit frequently throughout development
- Do NOT push any code. Always ask for permission

## General Development Principles

### Complexity & Code Quality
- Avoid over-engineering—use the minimum complexity needed for the current task
- Don't add comments, docstrings, or type annotations to unchanged code
- Don't create helpers or abstractions for one-time operations
- Don't add error handling for scenarios that can't happen
- Trust internal code and framework guarantees; validate at boundaries
- Prioritize doing things thoroughly and correctly over doing them quickly

### Magic Numbers & Strings
- **Extract all magic numbers and strings to named constants**
- Avoid hard-coded configuration values; inject via dependency injection or configuration frameworks
- Use descriptive constant names that explain the purpose
- Configuration values must come from external sources (environment variables, config files, dependency injection), never hard-coded
- See language-specific conventions for implementation patterns (e.g., IOptions for C#, environment variables for Python)

## Tools & Utilities

- **ast-grep (`sg`)**: Preferred tool for code analysis, searching, and refactoring across the codebase
- **Grep tool**: Use for finding patterns within specific files or directories
- **Subagent development skill**: Employ for complex implementation work requiring specialized focus
- **Memory/Journal tools (MCP)**: Mandatory for preserving insights, preferences, and patterns between conversations
  - Capture learnings immediately; don't rely on memory
  - Search journal before tackling any complex task
  - Use journal to retain project-specific context across sessions
