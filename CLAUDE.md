# CLAUDE.md

Instructions for working on this repository (the portable Claude Code configuration). The user's global instructions live in `global/CLAUDE.md` and are linked to `~/.claude/CLAUDE.md` by `setup.sh`; they apply here too.

## This repo is public

It is pushed to GitHub and meant for general use. Before finishing any change:
- No company-, employer- or product-specific details: no company, product or project names, internal package or namespace names, hostnames, ticket IDs, or descriptions of private codebases
- Examples are generic (`Foo`, `Payment`, `Order`), never taken from a private project
- Learnings from private projects are written as plain best practice and never attributed to them ("seen in", "observed in", "reference project")
- Search the changed files for such terms before reporting the work as done

## Layout

- `global/CLAUDE.md`: the user-level instructions (keep them short, concrete, free of duplicates and contradictions)
- `stacks/`: language and framework guides (best-practice baseline, repo conventions win over the guide)
- `commands/`: slash commands (to be migrated to skills and rules)
- `hooks/`: the git guard hook and its tests
- `setup.sh`: links the above into `~/.claude/`; update it whenever a folder is added or moved
- `README.md`: keep structure, usage and the Sources list in sync with reality

## Working on this repo

- Verify language claims in the guides by compiling or running them, and check them against the official documentation; list consulted documentation in the README Sources
- Change `hooks/block_git_publish.py` only together with its tests: `python3 -m unittest discover -s hooks -v`
- `~/.claude/settings.json` holds personal settings and is not tracked here; document needed settings snippets in the README instead
