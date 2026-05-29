---
mode: agent
description: "Map complete user journeys through the codebase, build a DTO registry, and produce a journey-weighted test strategy"
tools: ["bash", "glob", "grep", "view"]
---

# Journey Mapping & DTO Registry

Purpose: Trace real user journeys through the codebase so every test is written with full understanding of WHY a function exists, what data flows through it, and what must be mocked. Replaces depth-based cascade analysis with flow-based journey analysis.

This is a **static analysis** phase. Do not execute application code.

---

## Step 1 — Discover Entry Points

Identify all entry points where external requests or events enter the application.

Entry point types:
- **HTTP routes** — REST endpoints, GraphQL resolvers, WebSocket handlers
- **Message consumers** — Kafka listeners, RabbitMQ consumers, SQS handlers, event subscribers
- **Scheduled jobs** — cron tasks, scheduled executors, background workers
- **CLI commands** — command-line handlers, management commands
- **gRPC services** — service method implementations
- **Startup hooks** — initialization code, module loaders, DI container setup

For each entry point, record:
- method signature or route definition,
- HTTP method + path (if applicable),
- handler function/class,
- which module (Level 1 of the Project Graph) it belongs to,
- version indicator (v1, v2, etc.) if present.

---

## Step 2 — Trace Journeys

For each entry point, trace the **complete request-response journey** through all architectural layers.

A journey = one user action traced from entry to exit. Trace:

1. **Entry layer** — route/controller/handler that receives the request
2. **Service layer** — business logic, orchestration, validation
3. **Adapter layer** — translation between internal and external representations
4. **Client/Repository layer** — external I/O (database, HTTP, cache, queue)
5. **Mapper/Transformer layer** — data transformation between layers
6. **Validator/Policy layer** — input validation, authorization checks
7. **Utility layer** — shared helpers invoked along the path

For each journey, document:

```markdown
### Journey: {name} (e.g., "getCart", "placeOrder", "searchProducts")

**Entry point:** {method} {path} → {handler class/function}
**Version:** {v1/v2/v3 or "none"}

**Layer traversal:**
1. Route: {class.method} → receives request, extracts params
2. Service: {class.method} → orchestrates business logic
3. Adapter: {class.method} → translates to/from external format
4. Client: {class.method} → calls external service / database
5. Mapper: {class.method} → transforms DTOs between layers

**DTOs consumed:** {list of DTOs read as input at any layer}
**DTOs produced:** {list of DTOs created as output at any layer}

**Branch points:**
- {condition} → {happy path outcome}
- {condition} → {error/alternate outcome}
- {condition} → {cache hit vs miss}
- {condition} → {feature flag variants}

**Mock boundaries:** (where tests must mock to isolate)
- {external client/repository that performs real I/O}
- {third-party SDK calls}
- {environment/config dependencies}
```

### Versioned flows
If the project has versioned endpoints (v1, v2, v3, v4):
- Group them as **variants of the same journey**, not separate journeys.
- Identify what changed between versions (different mapper, different DTO, different adapter).
- Tests for one version inform tests for others — shared patterns should be extracted.

### Journey completeness check
Every non-trivial source file should appear in at least one journey. After tracing all journeys:
- List any source files that appear in **zero journeys** — these are either dead code, shared utilities, or missed entry points.
- Re-examine missed files: could they be reached from an undiscovered entry point?

---

## Step 3 — Build DTO Registry

Read **every** DTO, data class, model, request/response object, and entity class in the project. Read each file **exactly once**.

For each DTO, record:

```markdown
| Field | Value |
|-------|-------|
| **Class** | {fully qualified name} |
| **Package** | {package/module path} |
| **File** | {relative file path} |
| **Constructor params** | {name: Type = default, ...} |
| **Required params** | {params without defaults} |
| **Optional params** | {params with defaults, and what the defaults are} |
| **Nested DTOs** | {other DTOs referenced as fields} |
| **Builder/Factory** | {companion object, builder pattern, factory method — if any} |
| **Validation** | {annotations, init blocks, require() calls — if any} |
| **Journeys** | {which journeys consume or produce this DTO} |
| **Layers** | {which layers use this DTO: route, service, adapter, mapper} |
```

### Registry rules
1. **Read once, share everywhere.** The registry is built here and passed to every subsequent phase and agent. No agent should ever re-read a DTO source file.
2. **Include ALL DTOs** — even simple ones. Missing a DTO causes constructor errors that waste time during test generation.
3. **Capture defaults accurately** — knowing that `quantity: Int = 1` has a default of `1` prevents agents from always passing it explicitly.
4. **Track nesting** — if `OrderDto` contains `List<OrderItemDto>`, both must be in the registry with the relationship noted.
5. **Track which journeys use each DTO** — this connects the registry to the journey map, enabling targeted test data creation.

---

## Step 4 — Map Mock Boundaries

For each journey, identify **exactly what must be mocked** to test each layer in isolation.

Mock boundary types:
- **External HTTP clients** — calls to other services, third-party APIs
- **Database repositories** — direct DB access (JDBC, ORM, NoSQL)
- **Message producers** — queue/topic publishers
- **Cache clients** — Redis, Memcached, in-memory cache
- **File system** — file reads/writes
- **Clock/time** — `Instant.now()`, `System.currentTimeMillis()`
- **Random/UUID** — non-deterministic generators
- **Environment/config** — config properties, feature flags, env vars
- **Framework internals** — DI containers, HTTP engine, middleware

For each mock boundary:
```markdown
| Boundary | Type | Mock Strategy | Journeys Affected |
|----------|------|---------------|-------------------|
| CromaClient | HTTP client | mockk<CromaClient>() | getCart, placeOrder |
| ConfigProps | Config | mockkObject(ConfigProps) | ALL |
| OrderRepository | Database | mockk<OrderRepository>() | placeOrder, cancelOrder |
```

### Unmockable components
Identify components that **cannot be mocked** due to language/framework limitations:
- Kotlin `inline` + `reified` functions (MockK cannot proxy)
- Final classes without mock-maker extensions
- Static methods in Java without PowerMock
- Sealed interfaces with complex type hierarchies

For each unmockable component:
- explain WHY it can't be mocked,
- estimate the coverage ceiling impact,
- suggest workaround if possible (wrapper class, interface extraction).

---

## Step 5 — Produce Journey Test Strategy

Convert the journey map into a prioritized test generation plan.

### Journey-weighted prioritization
Rank journeys by testing value:

1. **Critical business journeys** — revenue-impacting, user-facing core flows (checkout, authentication, payment)
2. **Service orchestration** — methods that coordinate multiple adapters/clients
3. **Adapter per version** — adapters for each API version (v1, v2, v3)
4. **Mappers/transformers** — data transformation logic (high branch density, high LOC)
5. **Shared utilities** — helpers used across multiple journeys
6. **Gap fill** — remaining components not yet covered

### Per-journey test plan
For each journey (in priority order):

```markdown
### Test Plan: {journey name}

**Components to test (in order):**
1. {ServiceClass.method} — {reason: orchestrates the journey}
2. {AdapterClass.method} — {reason: handles external translation}
3. {MapperClass.method} — {reason: 15 branches, high logic density}

**Mock setup:**
- Mock: {list of boundaries to mock}
- Real: {list of components to keep real for cascade coverage}

**Test data from DTO Registry:**
- Input: {DTO class with constructor params}
- Expected output: {DTO class with expected values}

**Branch coverage targets:**
- Happy path: {description}
- Error: {exception scenarios}
- Edge: {null values, empty lists, boundary values}

**Estimated coverage gain:** {approximate lines that will be covered}
```

---

## Step 6 — Output

Produce the complete journey mapping report:

```markdown
## Journey Mapping Report

### Project Summary
- Entry points discovered: {count}
- Journeys traced: {count}
- DTOs registered: {count}
- Mock boundaries identified: {count}
- Unmockable components: {count}
- Source files covered by journeys: {count}/{total}
- Estimated coverage ceiling: {percentage}

### Entry Points
| # | Type | Path/Method | Handler | Module | Version |
|---|------|-------------|---------|--------|---------|

### Journey Map
{journey details from Step 2 — one section per journey}

### DTO Registry
{full registry from Step 3}

### Mock Boundary Map
{boundary table from Step 4}

### Unmockable Components
{list with reasons and ceiling impact}

### Journey-Weighted Test Strategy
{prioritized plan from Step 5}

### Orphan Files
{source files not appearing in any journey — candidates for dead code or missed entry points}
```

This report replaces the dependency graph and cascade coverage analysis. Every subsequent phase — test generation, prioritization, agent assignment — uses this journey map and DTO registry as their primary input.
