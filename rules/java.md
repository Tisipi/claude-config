---
paths:
  - "**/*.java"
  - "**/pom.xml"
  - "**/*.gradle"
  - "**/*.gradle.kts"
---

# Java Development Conventions

Best-practice baseline. The project's own conventions, formatter config and Java version win over this guide.

## Language
- Target the newest LTS the project allows (21 or 25); the build pins it: Maven `<maven.compiler.release>21</maven.compiler.release>` (`-release` also checks the JDK API level), Gradle `java { toolchain { languageVersion = JavaLanguageVersion.of(21) } }`
- Records for DTOs and value objects; validate in the compact constructor
- `switch` expressions, pattern matching for `switch` and record patterns (final since 21); sealed interfaces for closed type hierarchies, so the compiler checks exhaustiveness
- Sequenced collections (21): `getFirst()`, `getLast()`, `reversed()`
- Preview features (string templates, structured concurrency, stable values) only when the project already enables previews
- `var` for locals when the type is obvious from the right-hand side; never for fields or parameters
- Text blocks for multi-line strings (SQL, JSON)

## Null handling
- `Optional` only as a return type for "no result". Never as a field, parameter or collection element, and never `null` itself (Oracle's API note)
- Never return `null` for a collection or array: return an empty one
- Validate arguments at public boundaries with `Objects.requireNonNull(x, "x")`; not on private paths
- Prefer `Optional.map`/`orElseThrow` over `isPresent()` + `get()`
- Nullability annotations (JSpecify) when the project uses them; follow its choice

## Style
- Follow the project's formatter. Without one: Google Java Style (2-space indent, 100 columns, no wildcard imports, braces on every `if`/`for`/`while`)
- Constants are `static final` with immutable contents, `UPPER_SNAKE_CASE`. A `static final` list or map is not a constant: wrap it with `List.of`/`Map.of`/`Collections.unmodifiable*`
- Immutability by default: `final` fields, unmodifiable collections (`List.of`, `.toList()`), defensive copies at boundaries
- Package by feature, not by layer, in applications; keep implementation types package-private

## Concurrency
- Virtual threads for blocking I/O workloads (final since 21); don't pool them and don't use them for CPU-bound work
- Since Java 24, `synchronized` no longer pins virtual threads; on 21 prefer `ReentrantLock` around blocking calls
- `ExecutorService` is `AutoCloseable` since 19: use try-with-resources
- Share state with `java.util.concurrent` types; no hand-rolled `wait`/`notify`
- Scoped values (final in 25) instead of `ThreadLocal` for per-request data
- Interrupts: restore the flag (`Thread.currentThread().interrupt()`) when you catch `InterruptedException` and can't rethrow

## Errors & logging
- Specific exception types; wrap with the cause (`new FooException("msg", e)`), never swallow, never `catch (Exception)` except at a top-level boundary
- Unchecked exceptions for programming errors and unrecoverable failures; checked only when the caller can realistically recover
- `try-with-resources` for everything `AutoCloseable`
- SLF4J with parameterised messages: `log.info("Order {} shipped", orderId)`, no string concatenation. Pass the exception as the last argument. One log per event: log or throw, not both
- Levels: ERROR = operation failed, WARN = recovered/degraded, INFO = business events, DEBUG = diagnostics
- Never log secrets, tokens or personal data

## Spring Boot (when the project uses it)
- Constructor injection with `final` fields; a single constructor needs no `@Autowired`. Field injection only in tests
- Typed configuration: `@ConfigurationProperties` on a record (constructor binding), registered with `@ConfigurationPropertiesScan` or `@EnableConfigurationProperties`, plus `@Validated`. No scattered `@Value`
- `spring.threads.virtual.enabled=true` turns on virtual threads for the auto-configured executors (Java 21+)
- Keep controllers thin; transactions on the service layer (`@Transactional`), never on controllers
- Don't expose entities through the API; map to DTO records

## Testing
General rules (TDD, unit + integration + e2e, real data over mocks) are in CLAUDE.md.
- **JUnit Jupiter** (JUnit 6 needs Java 17+; use 5 only when the project is on it), **AssertJ** for assertions, `@ParameterizedTest` for value variations
- Prefer, in order: the real thing (Testcontainers, WireMock) → hand-written fake → mock. When a mock is needed, use the project's library (Mockito is the default). Mock only what is external to the class under test
- Spring Boot integration tests: Testcontainers with `@ServiceConnection` on the container field (needs `spring-boot-testcontainers`); `@DynamicPropertySource` only for properties it does not cover. A container that outlives the test class goes in a `@Bean`
- Test names state behaviour: `rejectsExpiredToken()`, or `method_condition_result` if the project uses it. One behaviour per test, no shared mutable state
- Assert outcomes, not call counts (`verify(..., times(n))` only when the interaction is the behaviour)
- Run: `./mvnw verify` (unit tests in `test`, integration tests in `verify`) or `./gradlew test`

## Build
- Use the project's build tool and wrapper (`./mvnw`, `./gradlew`). Maven is the default for new projects; with Gradle, use the Kotlin DSL
- Maven: versions in `<dependencyManagement>` and imported BOMs (`<type>pom</type>`, `<scope>import</scope>`), so dependencies omit versions; Gradle: a version catalog (`libs.versions.toml`). No version ranges or `+`
- CI: build with warnings as errors, run tests, a dependency vulnerability check
