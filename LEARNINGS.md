# Forge Core Learnings

> This file is the shared memory of Forge Core.
> After each completed run, the agent appends **generalized**, **secret-free**, **reusable** learnings here.
> These learnings improve future analysis, broken-test repair, and unit-test generation across projects.

## How it works
Forge Core uses this file to store:
- failure patterns that repeat across projects,
- framework-specific mocking and fixture rules,
- coverage-tool workarounds,
- DI and global-state cleanup tactics,
- high-value testing heuristics.

### What belongs here
- reusable techniques,
- tooling fixes,
- framework gotchas,
- stable coverage insights.

### What must never be stored here
- secrets,
- tokens,
- credentials,
- proprietary business logic,
- large source-code excerpts,
- personal data.

---

## Learnings Log

### Project: ioh-order-hub | Stack: Kotlin/Ktor/Koin | Date: 2025-05-25

**Fix Patterns Discovered:**
1. **Kotlin `object` singleton mocking** — `mockk<Configuration>()` does not safely replace Kotlin `object` singletons. Prefer direct assignment of mutable configuration state or supported object mocking with explicit teardown.
2. **`every` vs `coEvery` in MockK** — Use `every {}` for regular functions/properties and `coEvery {}` for suspend functions. Mixing them produces misleading coroutine failures.
3. **DTO drift across large test suites** — When production DTOs evolve, broad test suites break in many places. Fix shared builders/factories first, then direct constructor calls.
4. **JaCoCo on JDK 21 requires an explicit version** — Use `toolVersion = "0.8.12"` when JaCoCo fails on newer JDKs.
5. **`ignoreFailures = true` keeps coverage reporting alive** — Without it, even one failing test can suppress report generation and break the iteration loop.
6. **Mock placement matters** — Do not insert MockK setup into the middle of multi-line call arguments. Keep all arrangement before execution.
7. **`ExceptionInInitializerError` from top-level vals** — Top-level values can trigger constructor chains before tests can set configuration. Establish required config before class load or mark the seam as integration-heavy.
8. **Time-dependent assertions are brittle** — Replace `now()`-based assertions with fixed timestamps to avoid timezone and near-midnight failures.
9. **Koin state leaks between tests** — Use `stopKoin()` and `unmockkAll()` around tests that manipulate DI or static/object state.
10. **JaCoCo under-reports `inline reified` Kotlin functions** — Prefer Kover when inline coverage matters.
11. **Kover may need fallback handling** — If Kover is configured but unreliable in a project, fall back to JaCoCo while preserving report generation.

**Coverage Insights:**
- Quickest gains came from services, mappers, and utility layers.
- Repo/infrastructure-heavy classes remained poor unit-test candidates without broader seams.
- Coverage loops were safest when broken tests were repaired before any new test generation.

**Tech Stack Notes:**
- Ktor + Koin projects are highly sensitive to leaked global state.
- Kotlin-heavy projects benefit from a clear distinction between unit-test targets and startup/bootstrap code.

---

### Project: Sentinel | Stack: Python/FastAPI/pytest | Date: 2025-06-14

**Fix Patterns Discovered:**
1. **Cached settings require explicit reset** — When settings are exposed through an `@lru_cache` function such as `get_settings()`, tests must call `get_settings.cache_clear()` before and after env/config changes.
2. **Patch where used, not where defined** — Patching `app.notifier.send_email` does nothing if the code under test imports and calls `app.pipeline.send_email`. Patch the symbol in the module actually using it.
3. **Async tests need the right harness** — Async service and route tests should use `pytest-asyncio` with `@pytest.mark.asyncio` and `AsyncMock` for awaited collaborators.
4. **ASGI-native route testing is more stable** — `httpx.AsyncClient` with `ASGITransport` provides deterministic FastAPI/Starlette route tests without spinning up a real server.
5. **Override lifespan to avoid expensive startup** — Expensive startup hooks such as NLP/ML model loads should be bypassed or overridden in tests.
6. **Real isolated SQLite beats deep DB mocking for many service tests** — Using a real isolated SQLite database file often produces more trustworthy tests than mocking every repository/database interaction.
7. **Fallback chains need explicit tests** — Notification pipelines such as API → SMTP → console should be tested branch by branch with deterministic mocked failures.
8. **Global DB path state must be patched for isolation** — Module-level state such as `DB_PATH` should be patched per test or fixture so tests do not collide.
9. **Mock model boundaries, not the whole world** — For NLP/ML-backed endpoints, patch model loaders or prediction methods at the boundary rather than reproducing real model startup.
10. **Env-var config tests require cache discipline** — `monkeypatch.setenv()` is not enough on its own if settings are cached; pair env updates with cache clearing.

**Coverage Insights:**
- Highest ROI came from service functions, route handlers with dependency overrides, and notification/error-path tests.
- Deterministic async harnesses and settings-cache resets removed a large class of false negatives.
- Database-backed tests were most reliable when using isolated per-test DB state.

**Tech Stack Notes:**
- FastAPI projects often fail at import/startup boundaries rather than inside the actual business logic.
- Lifespan overrides and cache clearing are core test hygiene for production-grade FastAPI suites.

---

### Project: assembler-service | Stack: Kotlin 2.0/Ktor/Koin/MockK/JaCoCo | Date: 2026-05-28

**Fix Patterns Discovered:**
1. **JaCoCo exclusions waste test effort** — Always read `jacocoTestReport` config first. This project excludes `**/config/**`, `**/dto/**`, `**/model/**`, `**/exception/**`, `**/util/**` from coverage reporting. Tests for those packages improve correctness but will never move coverage numbers. Focus effort on included packages: adapter, service, mapper, client, route, repository, validator, plugins.
2. **Broad glob exclusions hide testable logic** — The `**/util/**` exclusion removes `Common.kt` (query parsing, hashing, date formatting) and `ApiUtil.kt` (HttpResponseException) from coverage. Consider narrowing exclusions to specific constant/enum files only: `**/util/AppConstant**`, `**/util/ErrorConstant**`, `**/util/SYMBOL**` instead of `**/util/**`.
3. **NotImplemented adapter methods are coverage gold** — When an adapter implements an interface but throws `NotImplemented` for most methods, testing all 40+ throw-only methods covers every line of the class with minimal effort. Each test is 3 lines and covers 1-2 source lines.
4. **DTO constructor params evolve independently** — Kotlin data classes with many required params (e.g., `CartModificationRequest` requires `category`, `pinCode`) break tests silently when new required params are added. Always check the DTO constructor signature before writing tests.
5. **Extension functions need import awareness** — BBMapper extension functions like `formatPrice()`, `getAddToCartRequest()` must be imported explicitly (`import BBMapper.getAddToCartRequest`). The receiver type determines which overload resolves.
6. **`serviceAdapter` global mutable map drives adapter selection** — The `serviceAdapter` var in `Common.kt` maps programId → NCAdapter. Tests must set this map explicitly in `@BeforeEach` to control which adapter handles the request. Forgetting this causes `invalidProgramId()` exceptions.
7. **Koin lazy inject in adapters requires DI setup even for throw-only methods** — `BBAdapterImpl` uses `private val bbGenericClient by inject<BBClient>()`. Even though NotImplemented methods don't use the client, Koin must be initialized or construction fails.
8. **`IndexOutOfBoundsException` on `items?.get(0)` vs `items?.firstOrNull()`** — BBMapper's `getAddToCartRequest()` uses `items?.get(0)` which throws on empty list. Test should assert the exception, not a default value. This is a real bug worth flagging.
9. **JaCoCo duplicate blocks in build.gradle.kts** — This project has duplicate `tasks.test {}` and `jacoco {}` blocks. Only the last one takes effect. Worth consolidating.

**Coverage Insights:**
- Baseline: 269 tests, LINE 35.1%, INSTRUCTION 32.5%, BRANCH 15.1%, METHOD 44.2%
- After Forge Core: 416 tests (+147), LINE 36.3% (+1.2%), METHOD 48.2% (+4.0%), BRANCH 15.8% (+0.7%)
- Biggest method coverage gain (+4.0%) came from BBAdapterImpl NotImplemented tests — 50 methods covered with simple assertThrows patterns.
- Mapper/RequestTransformer pure function tests gave highest confidence-per-effort ratio.
- Service tests (SLPService, AdTechService) were medium effort, high value — they test real delegation logic.
- The project has very low BRANCH coverage (15.8%) because most branches are in adapter methods with complex conditional flows (Redis, JWT, coroutineScope). These need integration-level mocking.

**Tech Stack Notes:**
- Kotlin 2.0 with `@Serializable` annotation on DTOs — ensure kotlinx.serialization compatibility in test fixtures.
- `BBAuthUtility.getJwtToken()` is an extension on String from an `object` — requires `mockkObject(BBAuthUtility)` plus `every { any<String>().getJwtToken() }` pattern for adapter integration tests.
- `RedisDaprClient.getRedis()` / `setRedis()` are extension functions on String — must be mocked via `mockkObject(RedisDaprClient)` for any code path touching Redis.
- `configProp` is a top-level val from `ConfigProps.configProp` — deeply wired into mappers and adapters. Must be initialized before any adapter/mapper test.

---

### Project: assembler-service (Round 2) | Stack: Kotlin 2.0/Ktor/Koin/MockK/JaCoCo | Date: 2026-05-28

**Cascade-First Test Generation Results:**
- Baseline (start of round 2): 416 tests, LINE 36.3%, BRANCH 15.8%, METHOD 48.2%
- After Forge Core v2.5: 648 tests (+232), LINE 43.2% (+6.9%), BRANCH 21.5% (+5.7%), METHOD 53.2% (+5.0%)
- Total tests generated in this round: 232 new tests across 11 test files
- Zero test failures in final full suite run

**Critical Learning — Study Existing Test Patterns FIRST (Phase -1 Rule):**
1. **Before writing any test, study the project's existing test suite patterns** — understand their mock setup, teardown, HTTP client strategy, DI patterns. This is mandatory Phase -1 work.
2. **Mold your tests to match the project's established patterns** — if existing tests use `HttpClientEngine.getClientEngine()` with `ClientConfigFactory` mocks, follow that pattern. Don't invent a new MockEngine approach.
3. **If no existing tests exist, use framework best practices** — but when tests DO exist, their patterns are the golden standard for that project.
4. **Pattern mismatch causes cross-test contamination** — a sub-agent wrote V3 adapter tests with a custom companion-level `MockEngine` instead of the project's `HttpClientEngine` pattern. This caused 33 pre-existing tests to fail due to Ktor engine state leakage.

**Cross-Test Contamination Patterns Discovered:**
1. **Companion-level `MockEngine` leaks Ktor state** — `HttpClient(MockEngine { ... })` in a companion object creates engine state that persists across test classes. The `@AfterAll` close isn't sufficient. Use per-instance or project-standard mock engines instead.
2. **`unmockkAll()` is safer than individual `unmockkObject()` calls** — individual unmock calls risk missing objects. Always use `unmockkAll()` in `@AfterEach` for complete cleanup.
3. **Global mutable state (`serviceAdapter`, `configProp`) requires explicit reset** — these top-level vars in `Common.kt` persist across test classes. Any test that modifies them must restore original state.
4. **Binary search to find contaminator** — when N tests fail, remove test files one at a time until failures disappear. The last removed file is the contaminator.

**Agent Orchestration Learnings (Forge Core Product):**
1. **Stuck agent self-termination** — agents stuck for >5 minutes (50+ tool calls with no progress) should self-terminate and hand off full context to a fresh replacement agent.
2. **Agent overtake pattern** — when replacing a stuck agent, the new agent receives: (a) the stuck agent's scope, (b) all discovered patterns/errors, (c) any partial work produced. The new agent MUST NOT repeat the stuck agent's approach.
3. **Completed agents as helpers** — agents that finish their assigned scope can be re-deployed to help slow/stuck agents, but they must NOT interfere with the stuck agent's parallel work. They should work on complementary sub-tasks.
4. **Sub-agent spawning** — parent agents can spawn child sub-agents for their own scope, but must: (a) clearly define each child's scope, (b) track child progress, (c) ensure children align with parent's requirements.
5. **Progress reporting** — agents should report status every 3 minutes so the orchestrator can detect stuck agents early.
6. **Cascade-first strategy validation** — testing high-cascade-impact functions first (utility/mapper functions called by many classes) provides maximum coverage amplification. One mapper test can cover lines in 5+ adapter methods.
7. **~50% agent failure rate observed** — in production runs with 6+ parallel agents, roughly half got stuck. This is expected. The solution is fast detection + agent overtake, not prevention.
8. **Scope splitting > single overtake** — splitting a stuck agent's broad scope into 2-3 focused helpers is more reliable than a single overtake agent with the same broad scope.

**Tech Stack Notes (New):**
- `CromaAdapterImplV3` creates a `newFixedThreadPool(16)` in constructor — thread pool may leak between tests if instance isn't properly scoped.
- `CromaClient` inline reified functions (`getFailSafeClientResponse<T>`) cannot be mocked with standard `coEvery` — use `mockkObject(CromaClient)` or mock the `HttpClient` parameter instead.
- `FetchCartRequestDto`, `RemoveProductDto`, `ProceedToPaymentRequestDto` all require `category` parameter — always check DTO constructors before writing tests.

---

<!-- Append new learnings below this line. -->
