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

... (truncated for brevity — full file mirrors central prompt)