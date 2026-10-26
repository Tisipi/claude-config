# C# Development Conventions

Targets .NET 10 / C# 14. For general principles (TDD, error handling, comments, magic numbers) see CLAUDE.md; this file adds the C#-specific detail.

## How to use this file

1. **The existing repo wins** over this file: `.editorconfig`, `Directory.Build.props`, analyzer config and surrounding code. Never restructure an existing solution without permission.
2. **Best practice is the baseline** for everything the repo doesn't decide, and for greenfield or large projects.
3. **[enforced]** = produced as a build warning by a shared code-style config (analyzer package or `.editorconfig`). Treat as mandatory in repos that have it.

## Solution & Build Setup

- `Directory.Build.props` holds shared settings once: `TargetFramework`, `LangVersion` latest, `Nullable` enable, `ImplicitUsings` enable, `EnableNETAnalyzers`, `AnalysisLevel` latest, `AnalysisMode` Recommended (or All for libraries), `EnforceCodeStyleInBuild`, `NuGetAuditLevel`
- **Central Package Management**: versions only in `Directory.Packages.props` (`ManagePackageVersionsCentrally`); `.csproj` uses `<PackageReference Include="X"/>` without `Version`. Shared test-only references go there under `Condition="'$(IsTestProject)' == 'true'"`
- Pin to stable versions; no floating versions (`*`) in production. Audit regularly: `dotnet list package --vulnerable --include-transitive`, `dotnet list package --outdated`
- Use `.csproj` SDK-style projects; target specific frameworks (.NET 10+), not broad compatibility. Deterministic builds (`ContinuousIntegrationBuild=true` in CI)
- Solution format `.slnx` where the tooling supports it
- `.editorconfig` + analyzers define style. Default (Microsoft convention): four spaces, no tabs. Indentation and line endings of the source files can differ per repo (tabs/CRLF and spaces/LF both occur) and are set in `.editorconfig` (line endings often also in `.gitattributes`): read them, never assume
- Shared style can ship as an analyzer NuGet package with a `.globalconfig` (`PrivateAssets="all"`); don't copy its rules into the repo
- Every `NoWarn` entry gets a reason comment, and design/performance rules (e.g. CA1848, CA1852) are not suppressed just for convenience. Extend with `$(NoWarn);X`. Avoid `#pragma warning disable`; if unavoidable, scope it tightly and justify. Sonar: `// NOSONAR: <reason>` or an `S####` `NoWarn` entry with reason
- `TreatWarningsAsErrors`: best practice is **on** in CI. A repo may have it off while refactoring; don't flip it in an existing repo without permission, but never add new warnings
- `InternalsVisibleTo` in the csproj: `<InternalsVisibleTo Include="Foo.Tests"/>`
- Generated code (`Generated/` folders) is never edited by hand; change the source spec and regenerate
- Commands: `dotnet build` (runs analyzers), `dotnet test`, `dotnet test --filter "FullyQualifiedName~Name"`, `dotnet format --verify-no-changes`, `dotnet run --project ./src/X`. There is no `dotnet analyze`

## Language & Style

### Core rules
- Nullable reference types enabled; no `#nullable disable` without justification
- File-scoped namespaces; `using` directives outside the namespace; namespace matches folder
- Follow Microsoft C# coding conventions. Naming: PascalCase for types, members, constants; camelCase for locals/parameters; `_camelCase` for private fields; `I` prefix on interfaces; generic parameters `T`, `TKey`, `TValue` (not `T1`, `T2`); no SCREAMING_CASE
- Braces always, even for single-line bodies; Allman style
- Explicit accessibility on every non-interface member
- **Methods use block bodies** (`{ return ...; }`); expression bodies only for properties, accessors, indexers, lambdas. This is a team rule (IDE0022) stricter than Microsoft's default
- Top-level statements for console apps and `Program.cs`
- Line length: follow the repo (120 is common); Microsoft's 65 applies only to their documentation samples
- `var` when the type is apparent from the right-hand side (`new`, cast, literal), explicit type otherwise (Microsoft convention; also an explicit type for `foreach` variables). Some repos enforce `var` everywhere via `.editorconfig`: then follow the repo. Target-typed `new()` where the type is apparent
- Mark non-capturing lambdas and local functions `static` **[enforced]**
- Use `string`/`int` keywords, not `String`/`Int32`; no `this.` qualification; discard `_` for unused values

### Class layout
- **One public type per file** (exceptions: nested types, extension classes, a small interface beside its only implementation, a `[LoggerMessage]` class at the bottom of its file)
- Member order: fields → properties → constructors → methods → nested types
- Prefer composition over inheritance. Seal classes unless designed for inheritance
- Keep methods small and single-purpose; early returns instead of deep nesting

### Modern language features
Verified on SDK 10.0.101.
- **Collection expressions**: `List<int> x = [];`, `int[] a = [1, 2];`, `[..xs, y]`. They need a target type: `var x = [1, 2];` does **not** compile (CS9176). Use them consistently instead of `new List<T> { }` / `new T[] { }`
- **Primary constructors**: parameters are *captured*, not properties (only `record`s promote them). Ideal for DI classes. Copy to a field only to transform or cache (`private readonly int _batchSize = options.Value.BatchSize;`). Avoid when the constructor needs logic
- **Records**: `record`/`sealed record` for immutable DTOs and value-like data; `record struct` for small immutable value types (`public readonly record struct Point(double X, double Y);`); `with` for modified copies
- **`required` + `init`** for mandatory members; never `= default!` to silence nullable warnings
- **Pattern matching and switch expressions** over `if` chains and `switch` statements: `is not null`, `is { Length: > 0 } s`, property/relational/list patterns
- **Params collections** (C# 13): `void Log(params IEnumerable<string> messages)`
- **C# 14**: `field` keyword (`set => field = value.Trim();`), null-conditional assignment (`p?.Name = "x";`), extension members (`extension(string s) { public bool IsShouty => ...; }`), unbound generic `nameof(List<>)`. Use when they remove boilerplate; don't mix with older styles in one file without reason. Classic `this` extension methods stay fine
- `System.Threading.Lock` instead of `lock (object)` for sync sections **[enforced]**
- `IAsyncEnumerable<T>` + `await foreach` (C# 8) for streaming; don't materialise large sets first
- Prefer raw string literals (`"""`) over escape sequences and verbatim strings, especially for multi-line JSON/SQL

### Immutability
- Prefer records and `init`-only properties; make fields `readonly`
- Return `IReadOnlyList<T>`/`IReadOnlyDictionary<K,V>` from public APIs instead of mutable collections
- Config-bound **options classes** are the exception: usable defaults on every property (`= string.Empty`, `= new()`), `{ get; set; }` or `init`

### Extension methods & fluent APIs
- Use for utility functions and fluent builders; keep them in a dedicated namespace/static class per concern
- Don't clash with LINQ or existing instance methods; don't extend `object` or very broad types

### Strings
- Interpolation (`$"Hello {name}"`) over `string.Format`; `StringBuilder` for concatenation in loops
- `string.IsNullOrWhiteSpace` for validation
- Always pass `StringComparison`/`StringComparer` (`Ordinal`, `OrdinalIgnoreCase`) for comparison, `Contains`, `StartsWith`, dictionary keys. Use `CultureInfo.InvariantCulture` for non-user-facing formatting/parsing
- Prefer `DateTimeOffset` (UTC) over `DateTime`; inject `TimeProvider` where "now" matters

### LINQ
- Method syntax; descriptive lambda names (`.Select(user => user.Name)`)
- Filter before projecting (`Where` → `Select`); avoid multiple enumeration (materialise once when reused)
- `First/Single` throw when empty; use `...OrDefault` deliberately and handle `null`
- Avoid `.ToList()` on large sequences unless needed; lazy evaluation is the default; avoid LINQ in hot paths
- Don't use `Count() > 0`: use `Any()` (or `Count > 0` on collections with a `Count`)

## Null Handling & Guards

- Model absence with `T?`, not sentinel values
- Boundary/public methods start with guard clauses: `ArgumentNullException.ThrowIfNull(x)`, `ArgumentException.ThrowIfNullOrWhiteSpace(s)`. Don't repeat guards on private/internal paths
- `??`, `??=`, `?.`, `x ?? throw new ...`
- Expected absence/failure: return `T?`, `TryX(out ...)` or a Result type (see Errors). Don't use exceptions for control flow

## Async & Concurrency

- `Async` suffix on all async methods; return `Task`/`Task<T>`, never `async void` (except event handlers); never block with `.Result`/`.Wait()`/`GetAwaiter().GetResult()`
- `CancellationToken cancellationToken` is the last parameter and flows through every call
  - Public library API: `= default`
  - Application-internal code: no default, so callers can't forget it
- `ConfigureAwait(false)` in **library** code only; not in ASP.NET Core/worker application code
- Distinguish timeout from cancellation:
  - `catch (TaskCanceledException ex) when (!cancellationToken.IsCancellationRequested)` = timeout
  - `catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)` = caller cancelled
- Use `Task.FromResult`/`ValueTask.FromResult` for synchronous results; `ValueTask` only for hot paths and lifetime hooks
- Don't fire-and-forget; background work belongs in a `BackgroundService`
- Async critical sections: `SemaphoreSlim(1, 1)` with `await WaitAsync(ct)` and `Release()` in `finally`; dispose it
- Cached async values in a singleton (e.g. auth token): check without lock → acquire → **re-check** → refresh → release; provide `Invalidate()` for server rejection
- Parallel I/O: `Task.WhenAll`, `Parallel.ForEachAsync` with `MaxDegreeOfParallelism`; no unbounded fan-out
- Retry/poll intervals come from options so tests can set `TimeSpan.Zero`
- Background jobs: `BackgroundService` reading a bounded `Channel<T>` (`SingleReader = true`, `FullMode = Wait`), a new scope per job (`await using var scope = scopeFactory.CreateAsyncScope();`), and the final job state persisted in `finally` with `CancellationToken.None`

## Dependency Injection, Configuration, Options

- Constructor injection for all external dependencies; no service locator (`IServiceProvider` only in factories/composition roots); no static mutable state
- Registration through one `AddX(this IServiceCollection, ...)` extension per library/feature, returning `IServiceCollection`; offer `IConfigurationSection` and `Action<TOptions>` overloads
- Lifetimes: be deliberate. Singleton must not capture scoped services; use `IServiceScopeFactory` in singletons/background services
- Options pattern: `IOptions<T>` (static), `IOptionsSnapshot<T>` (per request), `IOptionsMonitor<T>` (live reload). `public const string SectionName`. Validate with data annotations and/or `.Validate(...)` plus **`.ValidateOnStart()`** so bad config fails at startup
- Configuration comes from files/environment/vault, never hard-coded; secrets never in source or logs
- Required values without an options class: `config.GetValue<string>("A:B") ?? throw new InvalidOperationException("Configuration A:B is required.")`
- Interfaces `public`; implementations default to `internal sealed`
- **HttpClient**: always via `IHttpClientFactory`/typed clients (`AddHttpClient<IFoo, Foo>()`), never `new HttpClient()` per call. Add resilience with `Microsoft.Extensions.Http.Resilience` (retry with backoff + jitter, circuit breaker, timeouts); retry only transient failures and honour `Retry-After`. Redact secret headers in logs (`.RedactLoggedHeaders([...])`)
- Minimal APIs: group routes in `Map<Feature>Api(this IEndpointRouteBuilder)`, private static handlers returning `IResult`, `.Produces<T>(StatusCodes.StatusNNN)` per outcome, translate domain exceptions to 4xx in the handler, `MapHealthChecks("/health")`
- Required-config helpers (`RequiredString/Int/Url`) that also reject unreplaced `<PLACEHOLDER>` values and non-absolute URLs, so bad deployments fail at startup with the key name in the message
- Put shared host setup (logging, health checks, pipelines) in one `WebApplicationBuilder` extension so several hosts stay identical
- Outgoing auth: a `DelegatingHandler` that attaches a cached bearer token, a separate named `HttpClient` for the token request (so the handler can't call itself), cache invalidation on 401
- Resilience helpers as extension methods on `ResiliencePipelineBuilder<HttpResponseMessage>`; pass context such as the client name via `ResilienceContextPool.Shared.Get(ct)` + `request.SetResilienceContext(ctx)` and `Return` it in `finally`
- Pre-serialise request bodies to `StringContent` when the API needs an explicit `Content-Length` (`JsonContent` streams chunked); keep `JsonSerializerOptions` in `static readonly` fields

## Errors & Exceptions

General principles are in CLAUDE.md. C#-specific:
- Guard with `ArgumentNullException.ThrowIfNull`, `ArgumentException.ThrowIfNullOrWhiteSpace`; throw expressions (`x ?? throw ...`)
- **Never an empty `catch`.** A handler must (1) log with context, (2) wrap and rethrow with the inner exception, or (3) genuinely recover
- Catch the most specific exception. Use `throw;` (not `throw ex;`) to rethrow
- A broad `catch (Exception)` is acceptable only at a top-level boundary (worker loop, job processor, request pipeline), and then it logs, records failure and is preceded by the `OperationCanceledException when (...)` clause
- Custom exceptions for domain/integration errors: `sealed` unless a hierarchy is needed; constructors for message, message + inner, and domain data; nullable properties documented. Use a small hierarchy with static factories (`Communication.Timeout(ex)`) when callers react differently
- Exception messages include identifying context (endpoint, id, attempt, last status)
- Wrap transport failures in the boundary exception, log first, preserve the inner exception. Map HTTP status → exception in one `switch` expression
- Map exceptions → error codes in exactly one place, by **type**, never by message text
- **Result pattern** (e.g. `Result<T>`/discriminated unions) for expected, recoverable failures; exceptions for the exceptional. Nullable returns are the simpler default; adopt a Result type only where the codebase already uses one or after asking

## Logging

- `Microsoft.Extensions.Logging` via DI (`ILogger<T>`); levels used correctly: Debug < Information < Warning < Error < Critical
- **Structured** templates with named PascalCase placeholders (`{Endpoint}`, `{JobId}`), never string interpolation in the template; pass the `Exception` as its own parameter
- Preferred for new code: `[LoggerMessage]` source generation in an `internal static partial class <Feature>Log` (extension methods on `ILogger`). It avoids boxing, parses the template once, checks the level itself and validates templates at compile time (Microsoft: do not suppress CA1848). In a repo that already logs inline (e.g. with a `"[Tag] ..."` prefix) keep that style: one style per repo
- Pass raw values to the log method or template; never pre-build strings, interpolate or create objects in log arguments (CA1873 flags this, because arguments are evaluated even when the level is off). Fix with `[LoggerMessage]` or an `if (logger.IsEnabled(LogLevel.Debug))` guard. Neither is needed when the arguments are trivially cheap
- Never log secrets, tokens, PII; redact headers
- Configure the sink (e.g. Serilog + Seq) once in a shared host extension

## Resource Management

- Prefer `using` declarations (`using var x = ...;`); `using` blocks only when disposal must happen before method end
- Implement `IDisposable`/`IAsyncDisposable` for owned unmanaged/disposable resources; the full `Dispose(bool)` pattern only when a finalizer exists; `sealed` classes can use a simple `Dispose()`
- Never suppress finalization without proper cleanup; dispose `CancellationTokenSource`, `SemaphoreSlim`, `HttpRequestMessage`/`HttpResponseMessage`
- Use `await using` for async disposables

## Data Access (EF Core)

- `DbContext` with primary constructor; fluent mapping in `OnModelCreating`; scoped lifetime; async APIs only
- `AsNoTracking()` for read-only queries; project to DTOs instead of loading graphs; avoid N+1 (`Include`/projection); paginate
- Migrations in source control; parameterised queries only (no string-built SQL)
- Keep entities (domain) separate from DTOs (API contracts)
- Test against the real database provider (Testcontainers); in-memory SQLite only when no provider-specific behaviour is involved

## Documentation & Comments

- New files start with the 1–4 line `// ABOUTME:` header above the `using`s
- Comment rules are in CLAUDE.md (self-explanatory code first; a comment only for a useful, non-obvious *why*)
- **XML docs**:
  - Public libraries/SDKs/shared packages: document every public member (`<summary>`, `<param>`, `<returns>`, `<exception>`), enable CS1591
  - Application code: document public interface methods where the contract isn't obvious. Multi-line blocks are fine there
  - Document *constraints* (case-sensitive, not null), explicit nullable returns ("or `null` if not found"), side effects, thrown exceptions (not framework ones like `NullReferenceException`)
  - Add `<remarks>`/`<example>` for non-obvious behaviour or complex APIs
  - Don't document private/internal members (unless complex), self-explanatory properties, pass-throughs, or overrides that inherit docs
  - Library code with external consumers needs full XML docs even though application code stays comment-free; apply per project type

## Code Analysis & Tooling

- Roslyn analyzers on (`EnableNETAnalyzers`, `AnalysisLevel` latest, `EnforceCodeStyleInBuild`); StyleCop optional for libraries
- CI: build with warnings as errors, `dotnet format --verify-no-changes`, `dotnet list package --vulnerable`, tests with coverage
- Pre-commit hooks enforce build, tests, formatting; never bypass them

## Testing

General rules (TDD, unit + integration + e2e, real data over mocks) are in CLAUDE.md.

### Stack and principles
- **xUnit** (v3 for new projects), **Shouldly** (assertion-first), **WireMock.Net** (in-process) for HTTP dependencies, **Testcontainers** for real databases/brokers/servers
- Mocking library: match the project. NSubstitute and Moq are both fine; greenfield default is NSubstitute (clearer API)
- Prefer, in order: real thing (WireMock/Testcontainers) → hand-written fake → mock. Mock only what is external to the class under test. Never mock the project's own HTTP client abstraction when a WireMock test can exercise the real one
- Prefer strongly typed builders and helpers over reflection-based test helpers
- Assert on outcomes and captured arguments; avoid interaction call-counting (`Verify(..., Times.X)`) unless the interaction *is* the behaviour
- AAA (Arrange → Act → Assert); one behaviour per test; tests independent and parallel-safe; deterministic (no real clocks, sleeps or network)
- Meaningful assertion messages where the failure isn't self-explanatory: `result.ShouldBe(expected, "user should be retrieved")`
- Critical paths: happy path plus error cases (auth failure, 404, validation error, timeout, 5xx/resilience). Authorization logic gets exhaustive coverage

### Organisation
- Test project per production project: `Foo` ↔ `Foo.Tests`, mirroring the folder tree. Separate **unit** and **integration** projects (`Foo.Tests`, `Foo.IntegrationTests`) in large solutions so unit tests run without Docker; small solutions may use `Unit/` and `Integration/` folders in one project
- `public sealed class <ClassName>Tests`; split big SUTs by concern (`...ResilienceTests`, `...EdgeCaseTests`)
- File naming `[ClassName]Tests.cs`; method naming `Method_Condition_ExpectedResult`. Snake_case sentences and `Should_...` also occur: follow the file, never mix within one
- Categorise with `[Trait("Category", "Integration")]` so CI can filter
- Use fixtures for expensive shared setup; test-class instances are per test, so `Mock<T>` fields and `CreateSut()` helpers are safe
- Test files get an `// ABOUTME:` header

### xUnit v3 specifics
- Test projects: `<OutputType>Exe</OutputType>`, `<IsTestProject>true</IsTestProject>`, `<IsPackable>false</IsPackable>`; packages `xunit.v3`, `xunit.runner.visualstudio`, `Microsoft.NET.Test.Sdk`
- Pass `TestContext.Current.CancellationToken` to async calls under test (analyzer xUnit1051)
- Fixtures implement `IAsyncLifetime` (`ValueTask` methods); share via `[CollectionDefinition(Name, DisableParallelization = true)]` + `[Collection(Name)]`; fixtures arrive through primary constructors: `public sealed class FooTests(WireMockFixture fixture)`
- `[Theory]` + `[InlineData]` for value variations; `[MemberData]` for complex data
- `Should.ThrowAsync<XException>(() => sut.DoAsync(...))`, then assert on exception properties

### Patterns that work
- Build the SUT directly: `Options.Create(new FooOptions { ... })`, `NullLogger<Foo>.Instance`
- WireMock stubs as plain WireMock JSON (`mappings/` + `__files/`) in `src/Wiremocks` (own `Dockerfile` + README), linked into test output (`<Content Include="..\..\src\Wiremocks\**\*"><CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory><Link>Wiremock\%(RecursiveDir)%(Filename)%(Extension)</Link></Content>`) so the same stubs serve local development and tests; the folder-name constant must match the loader's
- Magic IDs that select stub behaviour are `public const string` on the fixture; WireMock **scenarios** model stateful sequences (call `ResetScenarios()` between tests)
- Polling/sequential logic: a hand-written `StubClient` returning queued responses with `Interval = TimeSpan.Zero`; assert on poll count and exception properties
- Large client interfaces: a nested `protected sealed class FakeXClient` in a shared abstract base; unused members throw `NotUsed()`; the fake records its last arguments
- Integration factory (`IntegrationTestFactory<TMarker>`-style, `IAsyncLifetime`): start WireMock/containers → build host → patch configuration to the stub URL with zero retry delays
- Runs in CI without Docker where possible (in-process WireMock)

## Architecture & Project Structure

**Never change the folder structure of an existing project without permission.** The tree below is an example only.

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

### Principles
- **Separation of concerns**: API, business logic, data access separate
- **Dependency rule**: inner layers never depend on outer layers
- **SOLID** throughout; **YAGNI**; reduce duplication (don't clone near-identical classes: make them generic)
- Repository/service layers abstract data access and business logic behind interfaces; don't wrap EF Core in a generic repository without a reason
- **Minimal API surface**: `internal` by default, `public` only as needed
- Entities (domain) separate from DTOs (contracts)
- `[ExcludeFromCodeCoverage]` only for wiring with no logic (log classes, composition roots). Never on code with branches

### Typical solution layout
- Naming `{Company}.{Team}.{Product}.{Part}`; `src/` and `test/` mirror each other
- Typical split: `Application` (host), `Domain` (domain/generated types), `Commons` (shared constants/hosting/options, no logic), `<Thing>Client` (standalone library with no project references to the others; own README/SPEC, options, models, exceptions, tests), separate deployable tools as their own projects
- Several independently deployable hosts (e.g. one per responsibility) can share one `Commons` project; each has its own `Dockerfile`, `appsettings*.json`, launch profile
- Library layout: `Models/`, `Options/`, `Exceptions/`, public interface, internal implementation, `ServiceCollectionExtensions.cs` at the root. Application layout: feature folder first, role second (`Feature/Action/Handlers`)
- For `WebApplicationFactory<T>`-style factories expose an empty `public sealed class <Host>ProgramMarker;` per host (with `// NOSONAR: <reason>`)
- Repo root: `docker-compose.yml` (hosts + stub server), `scripts/`, `docs/`
