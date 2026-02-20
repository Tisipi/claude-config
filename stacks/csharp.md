# C# Development Conventions

## Language & Features
- Use latest C# features (.NET 10.0+, C# 14+)
- Enable nullable reference types (`#nullable enable`)
- Prefer records for DTOs and immutable data
- Use top-level statements for console apps
- Use file-scoped namespaces (not nested namespaces)

## C# 14 Specific Features

### Collection Expressions
- **Always use collection expressions** for creating lists, arrays, spans: `int[] numbers = [1, 2, 3];`
- Preferred over `new List<T> { ... }` or `new List<T>()` syntax
- Works with `List<T>`, `Array`, `Span<T>`, and custom collection types
- Initialize empty collections: `IList<Item> items = [];` not `new List<Item>()`
- Example: `var users = [new User("Alice"), new User("Bob")];`
- Apply consistently across entire codebase to avoid mixing patterns

### Primary Constructors
- Use for concise class initialization when all constructor parameters become properties
- Example: `public class User(string Name, int Age) { ... }`
- Reduces boilerplate for DTOs and data classes
- Avoid when logic is needed in constructor; use traditional constructors instead

### Record Structs
- Use `record struct` for immutable value types
- Preferred over regular structs for domain models
- Example: `public record struct Point(double X, double Y);`
- Automatically generates equality, hashing, and ToString

### Params Collections
- Use collection expressions with `params`: `void Log(params string[] messages) { ... }`
- Call with `Log(["msg1", "msg2"])` using collection expression syntax

### Discard Operator
- Use `_` for unused variables to indicate intentional discard
- Example: `var (name, _) = GetUserData();` if age is not needed
- Clearer than naming variables `unused`, `temp`, etc.

### Async Enumerables
- Use `IAsyncEnumerable<T>` for streaming data from async sources
- Pair with `await foreach` for iteration
- More efficient than loading all data into memory first
- Example: `await foreach (var item in GetItemsAsync()) { ... }`

## Style & Naming
- Follow Microsoft C# coding conventions
- Use PascalCase for public members, camelCase for private
- Use file-scoped namespaces
- Interface names start with `I` prefix (`IRepository`, `IService`)
- Generic type parameters use `T`, `TKey`, `TValue`, etc. (not `T1`, `T2`)
- Private/readonly fields use `_camelCase` prefix
- Constants use `PascalCase` (not SCREAMING_SNAKE_CASE)

## Code Organization (C# Specific)
- **One public class per file** (exceptions: nested types, extension methods)
- **Order class members**: fields → properties → constructors → methods → nested types
- For general SRP and code organization principles, see CLAUDE.md

## Null Handling
- Leverage nullable reference types (`#nullable enable`)
- Use null-coalescing operator: `x ?? defaultValue`
- Use null-conditional operators: `obj?.Property`, `collection?[index]`
- Null checks with guard clauses at method start
- Avoid nested null checks; use `?.` operator

## String Handling
- Use string interpolation: `$"Hello {name}"` (preferred over `string.Format()`)
- Use StringBuilder for performance-critical string concatenation in loops
- Use `string.IsNullOrEmpty()` or `string.IsNullOrWhiteSpace()` for validation
- Use `@"..."` verbatim strings for paths and multi-line strings

## Patterns & Async
- Use dependency injection for all external dependencies
- Prefer async/await for all I/O operations (database, HTTP, file I/O)
- Use `ConfigureAwait(false)` in library code (not UI code) for better performance
- Return `Task` (not `void`) from async methods, except event handlers
- Use `Task.FromResult()` for sync results in async methods
- Use `IAsyncEnumerable<T>` with `await foreach` for streaming async data (C# 14)
- Use IOptions pattern for configuration (inject `IOptions<T>` or `IOptionsSnapshot<T>`)
- Use Result pattern for expected failures (vs. throwing exceptions)
- Guard clauses: return early to reduce nesting depth
- Use switch expressions (`x switch { ... }`) instead of switch statements where possible
- Use pattern matching: `if (obj is string str)` for type checks and deconstruction

## Immutability
- Prefer records for DTOs and immutable data
- Use `record struct` for immutable value types (C# 14)
- Use init-only properties: `public string Name { get; init; }`
- Use `required` keyword for properties that must be initialized
  - **Never use `= default!` as a workaround** — always use `required` if initialization is mandatory
  - Example: `public required string UserId { get; init; }` not `public string UserId { get; init; } = default!;`
- Make fields readonly when they don't change after construction
- Use `with` expressions to create modified copies of records
- Use primary constructors (C# 14) to reduce boilerplate in immutable types

## Extension Methods & Fluent Interfaces
- Use extension methods for utility functions or fluent APIs
- Place extension methods in a dedicated `Extensions` namespace
- Use fluent chaining for builder patterns and query operations
- Avoid extension methods that clash with LINQ or existing methods

## LINQ
- Prefer method syntax over query syntax for consistency
- Use descriptive variable names in `Select()`: `.Select(user => user.Name)` not `.Select(x => x.Name)`
- Filter before projection: `.Where(...).Select(...)` (applies to collections)
- Use `FirstOrDefault()` or `SingleOrDefault()` cautiously (throws on `First()` if not found)
- Avoid `.ToList()` on large collections unless necessary
- Use LINQ lazy evaluation for deferred execution

## Logging & Errors

**Note**: For general error handling principles (don't swallow exceptions, handle explicitly), see CLAUDE.md. This section covers C# specific syntax and patterns.

### C# Specific Exception Handling
- Use throw expressions: `x ?? throw new InvalidOperationException(...)`
- Use guard clauses with `ArgumentNullException.ThrowIfNull()`
- **NEVER use empty catch blocks**: `catch { }` is forbidden
  - Exception handlers must either:
    1. Log the exception with context: `catch (SpecificException ex) { _logger.LogError(ex, "..."); }`
    2. Transform and rethrow: `catch (Ex ex) { throw new DomainException(..., ex); }`
    3. Handle with recovery: `catch (Ex ex) { /* handle recovery */ }`
- Always catch specific exceptions, not base `Exception`
- Always include meaningful context in exception messages

### Exception Types & Patterns
- Create custom exceptions for domain-specific errors
- Use Result pattern for expected failures (recoverable errors)
- Log at appropriate levels: Debug < Information < Warning < Error < Critical
- Use Microsoft.Extensions.Logging with dependency injection
- Use IOptions pattern for configuration (inject `IOptions<T>` or `IOptionsSnapshot<T>`)

## Resource Management & IDisposable
- Prefer `using` declarations (C# 8+): `using var resource = GetResource();` over `using (var resource = GetResource()) { ... }`
- Use statements only when you need disposal at a specific point before method end
- Implement `IDisposable` and `IAsyncDisposable` when managing unmanaged resources
- Override `Dispose(bool)` pattern if implementing IDisposable
- Never suppress finalizers without proper cleanup

## Documentation

### XML Documentation Standards
- **Minimum 75% coverage** for public API (baseline); higher for critical business logic, public SDKs, and complex methods
- Document parameters with `<param>`, return values with `<returns>`, exceptions with `<exception>`
- **Inline comments**: Focus on "why" (code shows "what"). Avoid redundant comments like `i++; // increment i`
- **XML docs**: Document "what" first (`<summary>` for purpose, `<param>` for parameters, `<returns>` for return value), then explain "why" if non-obvious
- Use `<summary>` for class-level and method-level documentation
- Do not document internal/private members unless logic is complex
- Include examples for complex public APIs

### Documentation Best Practices
- Document *constraints* on parameters (e.g., "case-sensitive", "cannot be null")
- Explicitly document nullable returns (e.g., "or null if authentication fails")
- List all checked exceptions; omit framework exceptions (NullReferenceException, etc.)
- Add `<remarks>` for behavior that isn't obvious from the summary
- Include `<example>` for complex public APIs showing typical usage

### What NOT to Document
- Private/internal members (unless extremely complex)
- Self-explanatory property getters: `public string Name { get; set; }` needs no docs
- Simple pass-through methods
- Override methods that clearly inherit parent documentation

## Code Analysis & Tooling
- Enable Roslyn analyzers in the project file
- Use StyleCop analyzers for code style consistency
- Run code analysis: `dotnet analyze` or `dotnet build` (if analyzers configured)
- Address all warnings as errors in CI/CD pipelines
- Use `#pragma warning disable` sparingly and only with justification


## Testing
**Note**: For general testing principles (TDD, unit/integration/e2e requirements, test coverage minimums), see CLAUDE.md. This section covers C# specific tooling and patterns.

### Test Framework & Mocking
- Use xUnit for unit tests
- Use Shouldly for assertions (readable, assertion-first syntax)
- Use NSubstitute for mocking (preferred over Moq for clarity)
- Use Testcontainers for integration tests (databases, external services)
- Follow AAA pattern: Arrange → Act → Assert

### Test Organization & Project Structure
- Create parallel test projects: `Project.Tests` (unit), `Project.Integration` (integration)
- One test class per production class (or logical feature)
- Test file naming: `[ClassName]Tests.cs`
- Test method naming: `MethodName_Scenario_ExpectedOutcome()`
- Example: `GetUser_WithValidId_ReturnsUser()`
- Group related tests with `[Trait("Category", "Auth")]`
- Use `xunit` fixtures for shared setup

### Test Data & Mocking

**Unit Tests:**
- Mock external dependencies (APIs, file systems, databases)
- Use NSubstitute for mocks
- Avoid over-mocking; mock only what's external to your class
- Use test fixtures to reduce boilerplate

**Integration Tests:**
- Use Testcontainers for real databases and services (PostgreSQL, MySQL, Redis, etc.)
- Use real data against containerized services instead of mocks
- Testcontainers automatically manages container lifecycle
- Keep integration tests focused on single feature or flow

**General:**
- Keep tests focused on single responsibility
- Test one behavior per test method
- Use meaningful assertion messages: `result.ShouldBe(expected, "user should be retrieved")`

## Build & Dependencies
- Use `dotnet` CLI for all build operations
- Keep NuGet packages up to date (run `dotnet outdated` or check for vulnerabilities)
- Pin dependencies to stable versions; avoid floating versions in production
- Use `.csproj` project files (not legacy `.csproj.json`)
- Target specific frameworks (.NET 10.0+) rather than broad compatibility
- Use deterministic builds where possible for reproducibility

## Workflow & Commands

### Development Commands
```bash
# Build
dotnet build

# Run tests
dotnet test

# Run single test
dotnet test --filter "TestClassName"

# Code analysis
dotnet analyze

# Format code
dotnet format

# Run specific project
dotnet run --project ./src/ProjectName
```

### Development Process
- Write both unit tests AND integration tests for new features
- Run `dotnet test` locally before committing
- Run code analysis: `dotnet analyze` or `dotnet build` to catch warnings
- Use `dotnet format` to ensure consistent formatting
- Pre-commit hooks should enforce: tests pass, no warnings, formatted code

## Project Structure & Architecture

### Folder Organization
This is an example only. NEVER change the folder structure of an existing project without my permission!
```
src/
  ├── Project.Api/           # ASP.NET Core API layer
  ├── Project.Core/          # Domain logic, entities, interfaces
  ├── Project.Data/          # Data access, repositories, DbContext
  ├── Project.Services/      # Business logic services
  └── Project.Common/        # Shared utilities, extensions
tests/
  ├── Project.Tests/         # Unit tests
  └── Project.Integration/   # Integration tests
```

### Architecture Principles
- **Separation of Concerns**: API layer, business logic, data access should be separate
- **Dependency Rule**: Inner layers shouldn't depend on outer layers
- **SOLID Principles**: Apply throughout (Single Responsibility, Open/Closed, etc.)
- **Repository Pattern**: Abstract data access behind interfaces
- **Service Layer**: Business logic between API and data access
- **Minimal API Surface**: Expose only what's necessary; use `internal` liberally
- **Entity vs. DTO**: Keep entities (domain models) separate from DTOs (API contracts)

