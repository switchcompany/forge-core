---
mode: agent
description: "Detect backend language, framework, module boundaries, test stack, and coverage tooling across single-repo and monorepo layouts"
tools: ["bash", "glob", "grep", "view"]
---

# Detect Tech Stack

Detect the backend stack accurately before any analysis or test generation.

## Step 1 — Scan for build and runtime signals
Search the repository root and backend module roots for these files.

| Signal Files | Language / Build Stack |
|---|---|
| `pom.xml` | Java + Maven |
| `build.gradle`, `build.gradle.kts` | Java/Kotlin + Gradle |
| `package.json` | Node.js / TypeScript / JavaScript |
| `pyproject.toml`, `requirements.txt`, `setup.py`, `Pipfile` | Python |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `*.csproj`, `*.sln` | C# / .NET |
| `Gemfile` | Ruby |
| `composer.json` | PHP |

Also inspect:
- lockfiles,
- CI workflows,
- Dockerfiles,
- `Makefile`,
- test config files,
- coverage config files,
- module manifests under `services/`, `apps/`, `packages/`, `modules/`, `components/`.

---

## Step 2 — Infer backend framework

### Java / Kotlin
Look for:
- Spring Boot (`spring-boot-starter-*`)
- Ktor (`io.ktor`)
- Micronaut
- Quarkus
- Javalin
- Dropwizard

### Node.js
Look for dependencies such as:
- `express`
- `fastify`
- `koa`
- `@nestjs/core`
- `hapi`
- `loopback`

### Python
Look for:
- `fastapi`
- `starlette`
- `flask`
- `django`
- `aiohttp`
- `sqlalchemy`
- `pydantic`

### Go
Look for:
- `net/http`
- `gin-gonic/gin`
- `labstack/echo`
- `gofiber/fiber`
- `go-chi/chi`

### Rust
Look for:
- `actix-web`
- `axum`
- `rocket`
- `warp`

### C# / .NET
Look for:
- ASP.NET Core
- Minimal APIs
- Entity Framework Core
- MediatR

### Ruby
Look for:
- Rails
- Sinatra
- Hanami

### PHP
Look for:
- Laravel
- Symfony
- Slim

---

## Step 3 — Detect test framework, mocks, and coverage

Use config files, manifests, and existing tests to identify the real stack in use.

| Language | Test Framework Signals | Mock Signals | Coverage Signals |
|---|---|---|---|
| Java | `junit-jupiter`, `surefire`, `failsafe` | Mockito | JaCoCo |
| Kotlin | JUnit 5, Kotest | MockK | Kover / JaCoCo |
| Python | `pytest`, `pytest-asyncio` | `unittest.mock`, `pytest-mock` | `pytest-cov`, `coverage` |
| Node.js | Jest, Vitest, Mocha | `jest.mock`, `sinon`, `vi.mock` | `c8`, `nyc`, built-in coverage |
| Go | `go test`, `testing` | `testify`, `gomock` | `go test -cover*` |
| Rust | built-in test, nextest | `mockall` | `tarpaulin`, `llvm-cov`, `grcov` |
| C# | xUnit, NUnit, MSTest | Moq, NSubstitute | coverlet |
| Ruby | RSpec, Minitest | rspec-mocks | SimpleCov |
| PHP | PHPUnit, Pest | Mockery, Prophecy | PHPUnit coverage |

Also detect:
- DI framework,
- ORM or persistence layer,
- queue/messaging,
- cache,
- external API clients,
- auth/security libraries.

---

## Step 4 — Monorepo detection
Treat the repo as a monorepo if multiple independent build roots exist.

### What to do in a monorepo
1. List every backend-capable module with its path.
2. Ignore clearly frontend-only packages unless the user explicitly asks for them.
3. Note shared libraries and test utilities.
4. Record whether each module has:
   - its own build file,
   - its own test command,
   - its own coverage command,
   - its own reports directory.
5. Prefer the narrowest command that exercises the target backend module.

---

## Step 5 — Identify key paths and commands
Capture:
- source roots,
- test roots,
- fixture/resource roots,
- exact test command,
- exact coverage command,
- likely report locations,
- commands that already exist in scripts or CI.

Prefer project-defined commands over invented ones.

---

## Step 6 — Output format
Produce a stack report like this:

```markdown
## Tech Stack Report

### Repository Shape
- Single repo / monorepo
- Backend modules: ...

### Primary Module
- Language:
- Framework:
- Build Tool:
- Test Framework:
- Mock Library:
- Coverage Tool:
- DI:
- Database / ORM:
- Cache:
- Queue:
- Security:

### Commands
- Build:
- Test:
- Coverage:

### Paths
- Source Root:
- Test Root:
- Coverage Report:

### Confidence Notes
- Why this detection is correct
- Ambiguities or multiple valid test runners
```

---

## Quality Bar
Do not stop at language detection alone.
You must detect enough detail to choose:
- the right test style,
- the right mocking style,
- the right coverage tool and fallback chain,
- the correct module scope for later phases.
