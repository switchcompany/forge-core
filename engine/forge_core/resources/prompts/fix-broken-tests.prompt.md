---
mode: agent
description: "Repair broken backend tests using a cross-language library of common compile/runtime failure patterns"
tools: ["bash", "glob", "grep", "view", "edit"]
---

# Fix Broken Tests

Fix failing or non-compiling tests **without modifying production code**.

## Operating rules
- work only in tests, fixtures, test resources, and test-only config,
- preserve passing tests,
- fix deterministic issues first,
- compile and rerun after each batch,
- stop fighting clearly integration-only failures and document them.

---

## Step 1 — Gather failures
Run the project’s existing test/compile command and capture:
- compile errors,
- runtime failures,
- import/load failures,
- flaky behavior caused by shared state,
- coverage tool failures that block reporting.

---

## Step 2 — Categorize by known pattern

### Pattern 1 — DTO / Model Drift
**Symptom:** wrong field names, missing constructor args, invalid fixture JSON.
**Fix:** align test builders and payloads with the current production model.

### Pattern 2 — Method Signature Drift
**Symptom:** argument count/type mismatch, nullable mismatch, wrong generic type.
**Fix:** read the current signature and update test invocation + mocks.

### Pattern 3 — New Required Parameters or Defaults Changed
**Symptom:** compiler says missing required param; runtime says field required.
**Fix:** add deterministic values and update common factories.

### Pattern 4 — Async vs Sync Mocking Mismatch
**Symptom:** coroutine never awaited, Promise mismatch, wrong await style.
**Fix:**
- Python: `AsyncMock` and `pytest.mark.asyncio`
- Kotlin: `coEvery` / `coVerify`
- Node: `mockResolvedValue`, `mockRejectedValue`
- C#: `ReturnsAsync`, `ThrowsAsync`

### Pattern 5 — Kotlin Singleton / Object Mocking
**Symptom:** object/singleton remains real even after mocking attempt.
**Fix:** assign test state directly or use supported object/static mocking with teardown.

### Pattern 6 — Wrong Patch Target
**Symptom:** patched dependency is ignored and real code still runs.
**Fix:** patch where the symbol is imported/used, not where it was originally defined.

### Pattern 7 — Mock Placement Errors
**Symptom:** added stub is inside call arguments or after invocation.
**Fix:** move all arrangement/stubbing before the act step.

### Pattern 8 — Import-Time Side Effects
**Symptom:** import triggers DB connection, settings load, model initialization, or network client creation.
**Fix:** patch before import, override startup hooks, or force lazy fixture setup.

### Pattern 9 — `ExceptionInInitializerError` / Static Initialization Failures
**Symptom:** class loading fails before test logic starts.
**Fix:** establish required config first, mock static initializers if safe, or mark as integration-prone.

### Pattern 10 — DI Container Leaks
**Symptom:** tests pass in isolation but fail in suite.
**Fix:**
- Koin: `stopKoin()` and `unmockkAll()`
- Spring: minimize dirty contexts, reset shared singletons
- Nest/FastAPI: rebuild app/container per test or fixture scope

### Pattern 11 — Time-Dependent Assertions
**Symptom:** timezone or time-of-day failures.
**Fix:** replace wall-clock assumptions with fixed timestamps or injected clocks.

### Pattern 12 — Database State Leakage
**Symptom:** cross-test contamination, order dependence, residual rows/files.
**Fix:** isolated DB per test/session, transaction rollback, schema reset, unique test data.

### Pattern 13 — Cached Configuration / Settings
**Symptom:** env overrides ignored.
**Fix:** clear memoized settings/cache and rebuild config objects.

### Pattern 14 — HTTP / ASGI / Host Test Harness Mismatch
**Symptom:** wrong client for the framework runtime.
**Fix:**
- FastAPI/Starlette: `httpx.AsyncClient` + `ASGITransport`
- Spring MVC: `MockMvc`
- Express/Fastify: `supertest`
- ASP.NET Core: `WebApplicationFactory` only where needed

### Pattern 15 — Assertion Weakness or Wrong Behavioral Expectation
**Symptom:** test compiles but fails because it asserts outdated or incidental behavior.
**Fix:** re-read production behavior, update assertions to actual contract, not implementation noise.

### Pattern 16 — Coverage Exclusion Mismatch
**Symptom:** tests pass, but coverage numbers don't change.
**Fix:** the target package may be excluded from coverage reporting. Check the exclusion map from Phase 1.5. Redirect effort to included packages.

### Pattern 17 — NotImplemented Method Pattern
**Symptom:** adapter/interface methods throw NotImplementedError/UnsupportedOperationException.
**Fix:** generate simple `assertThrows` tests for all throw-only methods. Each test covers 1-2 source lines with minimal effort. This is the highest coverage-per-effort pattern.

### Pattern 18 — Extension Function Resolution
**Symptom:** Kotlin extension functions not found or wrong overload resolved.
**Fix:** import extension functions explicitly by their containing file/object. Check the receiver type to ensure the correct overload is used.

### Pattern 19 — Global Mutable State for Routing
**Symptom:** adapter selection throws "invalid program" or "not found" errors in tests.
**Fix:** initialize global routing/selection maps (e.g., `serviceAdapter`, `routeRegistry`) in `@BeforeEach` before tests that depend on adapter resolution.

### Pattern 20 — Top-Level Val Configuration Dependencies
**Symptom:** mapper/adapter tests fail with uninitialized config.
**Fix:** top-level `val configProp = ConfigProps.configProp` or similar must be initialized before any test in that module. Set up config in a shared test fixture or `@BeforeAll`.

---

## Step 3 — Apply fixes in safe batches
For each batch:
1. fix a narrow set of related failures,
2. recompile/rerun,
3. verify pass count did not regress,
4. keep notes on patterns used.

Avoid mass regex edits unless the pattern is mechanically safe and verified.

---

## FastAPI / Sentinel-specific guidance
When the stack is Python + FastAPI:
- clear cached settings with `get_settings.cache_clear()`,
- patch where used,
- use `pytest.mark.asyncio`,
- use `AsyncClient` + `ASGITransport`,
- override lifespan for expensive startup work,
- use isolated SQLite files for DB tests,
- patch module-level `DB_PATH` or similar globals,
- assert fallback chains explicitly.

---

## Required output
Produce:

```markdown
## Broken Test Fix Report
- Errors fixed:
- Categories used:
- Tests now passing:
- Remaining failures:

| Pattern | Count | Notes |
|---|---:|---|
```

If anything remains broken, state whether it is:
- infra-dependent,
- flaky legacy behavior,
- unsupported without broader refactoring.
