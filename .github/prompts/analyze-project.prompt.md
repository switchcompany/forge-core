---
mode: agent
description: "Perform deep backend architecture analysis covering HLD, LLD, request/data flows, integrations, security model, and unit-test seams"
tools: ["bash", "glob", "grep", "view"]
---

# Analyze Project

Perform a deep architecture and testability analysis for the backend scope.

## Step 1 — Repository reconnaissance
- map the directory tree to depth 2–3,
- identify backend modules,
- read build files and dependency manifests,
- inspect README/docs/ADR files,
- locate entry points, startup hooks, and environment/config sources,
- note CI commands for build/test/coverage.

## Step 2 — High-Level Design (HLD)
Document the following.

| Area | What to capture |
|---|---|
| System Purpose | What the backend does and who consumes it |
| Module Map | Each backend module/package and its responsibility |
| Architecture Style | Layered, hexagonal, clean architecture, MVC, event-driven, etc. |
| External Integrations | DB, cache, queue, SMTP, storage, third-party APIs, ML services |
| Communication Model | REST, gRPC, GraphQL, workers, consumers, cron, webhooks |
| Security Model | Authentication, authorization, token handling, roles, middleware |
| Operational Risks | Startup side effects, shared state, heavy initialization |

## Step 3 — Low-Level Design (LLD)
For each relevant module/package/class, identify:
- responsibilities,
- public endpoints/APIs,
- service/use-case methods,
- repositories/clients/adapters,
- DTOs/entities/schemas,
- validation logic,
- error handling patterns,
- dependency injection or service construction,
- boundaries where unit tests should mock dependencies.

## Step 4 — Flow analysis
Trace the main flows.

### Required flow categories
1. **Request lifecycle**
   - request entry,
   - middleware/filters,
   - validation,
   - handler/controller,
   - service/use case,
   - repository/client,
   - response mapping.

2. **Business logic flows**
   - happy path,
   - error path,
   - fallback path,
   - retry path,
   - edge-case branches.

3. **Data transformation flows**
   - input DTO → domain → persistence → response DTO.

4. **Async/event flows**
   - queues,
   - scheduled jobs,
   - background workers,
   - pub/sub,
   - consumer handlers.

## Step 5 — Security model review
Identify:
- auth entry points,
- middleware/filters,
- session vs token vs API key,
- role/policy enforcement,
- user-context propagation,
- security-sensitive branches worth testing.

## Step 5.5 — Enterprise Project Graph (4-Level DAG)

Build a 4-level directed acyclic graph that decomposes any project into a testable structure.
This graph is the **structural backbone** used by all subsequent phases.

### Level 0: Project
The root node. Contains project metadata:
- project name, language, framework, build tool
- total source lines, total test lines
- module count

### Level 1: Modules
Backend modules or packages. In monorepos, each service is a module. In single-service projects, each top-level package is a module.
- Module name, path, line count
- Dependencies on other modules
- **Parallelism boundary**: each module can be analyzed and tested independently

### Level 2: Layers
Within each module, classify all classes/files into architectural layers:
- **Route/Controller** — HTTP entry points, request handlers
- **Service/UseCase** — business logic orchestration
- **Adapter** — external system adapters (API clients, cache, queue)
- **Client** — raw HTTP/gRPC/queue clients
- **Mapper/Transformer** — data transformation between layers
- **Repository** — data persistence
- **Validator/Policy** — input validation, business rules
- **Config/DI** — dependency injection, configuration
- **Util/Helper** — shared utilities
- **DTO/Model** — data transfer objects, entities

### Level 3: Journeys
Trace complete request-response flows that cross multiple layers. Each journey represents a real user action:
- Journey name (e.g., "getCart", "placeOrder", "searchProducts")
- Entry point (route/controller method)
- Layer traversal path: Route → Service → Adapter → Client → Mapper
- DTOs consumed and produced at each layer boundary
- Versioned variants (v1/v2/v3 of the same journey)
- Branch points (error paths, cache hit/miss, feature flags)

### Level 4: Components
Individual classes/functions within each layer:
- Function name, signature, line count, branch count
- Testability score (0-10 based on: pure logic=high, heavy I/O=low)
- Which journeys pass through this component
- Mock boundary (what must be mocked to test this in isolation)

### DAG Output Format
```markdown
## Enterprise Project Graph

### Project: {name}
- Language: {lang} | Framework: {framework}
- Source: {lines} lines | Modules: {count}

### Module: {name}
#### Layers
| Layer | Classes | Lines | Coverage |
|-------|---------|-------|----------|

#### Journeys
| Journey | Entry Point | Layers Traversed | DTOs | Versions |
|---------|-------------|------------------|------|----------|

#### Components (top uncovered)
| Component | Layer | Lines | Branches | Testability | Journeys |
|-----------|-------|-------|----------|-------------|----------|
```

### Rules
- **Decompose at Level 1** for parallelism — distribute modules across agents.
- **Trace at Level 3** for understanding — know WHY each function exists before testing it.
- **Prioritize at Level 4** for efficiency — test high-testability components in critical journeys first.
- **Detect versioned flows** — if v1/v2/v3/v4 exist, group them as variants of the same journey, not separate targets. Tests for one version inform tests for others.

This graph feeds directly into the **Journey Mapping** phase (Phase 2.5) and **Journey-Weighted Prioritization** (Phase 4).

## Step 6 — Testability map
Classify backend files by unit-test suitability.

| Category | Definition |
|---|---|
| Easy wins | Pure logic, stateless services, mappers, utils |
| Moderate | Services with mockable repositories/clients |
| Heavy mocking | Handlers/controllers with framework setup |
| Integration-prone | DB-heavy repositories, infra bootstraps, messaging consumers |
| Excluded | Generated code, constants, bootstrap, pure DTOs with no behavior |

## Step 7 — Targeted mode rules
If the user requested specific classes/files:
- read those files completely,
- trace direct dependencies and imports,
- explain what must be mocked,
- scope all later analysis and coverage decisions to those targets.

## Step 8 — Required output
Produce:

```markdown
## Architecture & Testability Report

### HLD
- Purpose:
- Architecture style:
- Modules:
- Integrations:
- Security model:

### Enterprise Project Graph
#### Module: {name}
| Layer | Classes | Lines | Coverage |
|-------|---------|-------|----------|

#### Journeys Discovered
| Journey | Entry Point | Layers Traversed | DTOs | Versions |
|---------|-------------|------------------|------|----------|

### LLD
| Module/Package | Key Types | Responsibility | Test Seam |
|---|---|---|---|

### Flows
1. ...
2. ...

### Testability Priorities
1. ...
2. ...

### Risks for Unit Testing
- import-time side effects
- global state
- heavy framework bootstrap
```

Focus on information that directly improves later testing decisions.
The Enterprise Project Graph is the most important output — it drives all subsequent phases.
