Generate a `repomix` command the user can copy/paste to produce an LLM-friendly repository dump.

Ask the user:
1. What is the repo path to dump?
2. Do they want a full dump (default) or a filtered dump via `--include`?
3. If filtered: which stack (C#, TypeScript/JavaScript, Python, Java) or a custom comma-separated glob list?
4. What output filename do they want? Default to `context.md`.

Then output exactly one recommended command.

Rules:
- Prefer the simplest command that satisfies the user’s goal.
- Do not invent files or paths; use the user-provided repo path.
- Use `--include` only when the user asked for filtered output.
- Use recursive globs with `**/`.

Include presets:
- C#: `"**/*.cs,**/*.csproj,**/*.sln,**/*.props,**/*.targets"`
- C# (plus common config): `"**/*.cs,**/*.csproj,**/*.sln,**/*.props,**/*.targets,**/*.json,**/*.yml,**/*.yaml"`
- TypeScript/JavaScript: `"**/*.ts,**/*.tsx,**/*.js,**/*.jsx,**/*.json"`
- Python: `"**/*.py,**/*.toml,**/*.yml,**/*.yaml"`
- Java (Maven/Gradle): `"**/*.java,**/pom.xml,**/*.gradle,**/*.properties,**/*.yml,**/*.yaml"`

Example outputs (use as templates, but substitute the user’s values):
- Full dump:
  `repomix <REPO_PATH> --output <OUTPUT_FILE>`
- Filtered dump:
  `repomix <REPO_PATH> --output <OUTPUT_FILE> --include "<GLOBS>"`
