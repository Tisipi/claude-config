# Java Development Conventions

## Language
- Use Java 21+ features when available (records, pattern matching, virtual threads)
- Prefer Optional over null returns
- Use records for DTOs and value objects

## Style
- Follow Google Java Style Guide
- Use meaningful package structure
- Prefer immutability where practical

## Logging & Errors
- Use SLF4J for logging
- Use specific exception types, avoid generic Exception
- Log at appropriate levels (ERROR for failures, WARN for recoverable issues, INFO for business events, DEBUG for troubleshooting)

## Testing
- Use JUnit 5 for unit tests
- Use Mockito for mocking
- Run tests with: ./gradlew test (or ./mvnw test for Maven)

## Build
- Prefer Gradle with Kotlin DSL
- Keep dependencies up to date

## Workflow
- Always write tests BEFORE implementation (TDD: Red → Green → Refactor)
- Run pre-commit hooks before committing (tests, linting, formatting)
- Create spec.md for requirements and prompt_plan.md for implementation steps
- Commit after each completed step
