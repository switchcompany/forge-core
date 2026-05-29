# Knowledge Pack — Kotlin / Ktor

Use this pack when the backend is Kotlin-based and commonly uses Ktor, coroutines, MockK, Koin, Gradle, and JaCoCo/Kover.

---

## 1. Core testing stack
- **Runner:** JUnit 5 or existing project convention
- **Mocking:** MockK
- **Coverage:** Kover first for Kotlin-heavy projects, JaCoCo fallback
- **Coroutines:** `runTest` or project-standard coroutine test harness

---

## 2. Singleton mocking (`object`)
Kotlin `object` singletons are a common source of broken tests.

### Key rule
Do **not** assume `mockk<SomeObject>()` will replace a Kotlin `object`.

Preferred tactics:
- assign mutable test properties directly,
- use supported object mocking carefully,
- always tear down static/object mocks after each test.

Example pattern:
```kotlin
@BeforeEach
fun setUp() {
    stopKoin()
    Configuration.env = testConfig
}
```

---

## 3. `every` vs `coEvery`
Use:
- `every { ... }` for normal functions and properties,
- `coEvery { ... }` for suspend functions.

Mixing them causes coroutine-related failures and misleading test errors.

Also pair verifications correctly:
- `verify { ... }`
- `coVerify { ... }`

---

## 4. DTO drift / data-class changes
Large Kotlin test suites frequently break when DTO fields change.

Symptoms:
- missing constructor args,
- wrong named parameter,
- stale fixture JSON,
- type mismatch after model evolution.

Fix strategy:
1. read the current production data class,
2. update shared builders/factories first,
3. update direct constructor calls next,
4. recompile frequently in small batches.

---

## 5. JaCoCo on JDK 21
If JaCoCo fails on modern JDKs, pin:
```kotlin
jacoco { toolVersion = "0.8.12" }
```

If you see duplicate or bundled class errors, restrict class directories to compiled project classes.

---

## 6. `ignoreFailures = true`
Coverage reports often disappear entirely if any test fails.

Preserve report generation with:
```kotlin
tasks.withType<Test> {
    ignoreFailures = true
}
```

This is critical during repair and iteration phases.

---

## 7. Mock placement rules
Never insert mock/stub setup:
- inside multi-line function arguments,
- after the act step,
- mid-builder chain unless you are sure of scope.

Place all MockK arrangement before execution.

---

## 8. `ExceptionInInitializerError` from top-level vals
Top-level values such as:
```kotlin
val dao = DAOFacadeImpl()
```
can trigger constructor chains at class-load time.

If those constructors depend on config or infra, tests fail before setup runs.

Fix options:
- establish required config before the class is loaded,
- mock the static provider if safe,
- skip unit coverage if the seam is too hostile and document it.

---

## 9. Time assertions
Never assert against `LocalDateTime.now()` or similar wall-clock values.

Use fixed timestamps:
```kotlin
val now = LocalDateTime.of(2024, 1, 15, 10, 30, 0)
```

This avoids timezone and near-midnight failures.

---

## 10. Koin state leaks
Tests that pass alone but fail in suite often leak Koin or MockK state.

Recommended cleanup:
```kotlin
@BeforeEach
fun before() {
    stopKoin()
}

@AfterEach
fun after() {
    unmockkAll()
    stopKoin()
}
```

Use `@DirtiesContext`-style thinking sparingly; prefer explicit cleanup.

---

## 11. Kotlin inline reified coverage
JaCoCo may under-report or fail to instrument `inline reified` functions.

If coverage matters for inline-heavy clients/helpers, prefer **Kover**.
If the code executes but coverage is implausibly low, treat JaCoCo as the limitation, not necessarily the tests.

---

## 12. Ktor-specific notes
When testing Ktor handlers/routes:
- prefer project-standard Ktor test harness,
- mock downstream clients/services,
- isolate auth/context setup,
- verify serialization and status codes deterministically.

---

## 13. High-value target order
1. services/use-cases,
2. route handlers,
3. mappers,
4. utils,
5. adapter/client wrappers with mocked I/O.

Lower value:
- bootstrap,
- generated code,
- pure constants/data holders.

---

## 14. Kotlin/Ktor completion checklist
Before accepting a batch, confirm:
- correct `every`/`coEvery` usage,
- singleton config handled safely,
- Koin + MockK cleanup present,
- fixed time sources used,
- DTO builders aligned to current model,
- coverage tool behavior understood if inline functions are involved.

---

## 15. JaCoCo coverage exclusion detection
Before generating tests, always scan `build.gradle.kts` or `build.gradle` for JaCoCo exclusion patterns.

Common exclusion locations:
```kotlin
tasks.jacocoTestReport {
    classDirectories.setFrom(fileTree("build/classes") {
        exclude("**/config/**", "**/dto/**", "**/model/**", "**/exception/**", "**/util/**")
    })
}
```

Tests for excluded packages improve correctness but won't move coverage metrics. Prioritize included packages first.

---

## 16. NotImplemented adapter testing
When adapter classes implement interfaces but throw `NotImplementedError` for most methods:

```kotlin
@Test
fun `method throws NotImplementedError`() {
    assertThrows<NotImplementedError> { adapter.someMethod(params) }
}
```

Each test is 3 lines, covers 1-2 source lines. Highest coverage-per-effort pattern for large adapter interfaces.

---

## 17. Extension function imports
Kotlin extension functions in companion objects or top-level files must be imported explicitly:

```kotlin
import com.example.mapper.BBMapper.getAddToCartRequest
import com.example.mapper.BBMapper.formatPrice
```

The receiver type determines which overload resolves.

---

## 18. Global mutable adapter maps
Enterprise projects often use a global mutable map to route requests to adapters:

```kotlin
var serviceAdapter: HashMap<String, NCAdapter> = HashMap()
```

Tests must initialize this map in `@BeforeEach`. Forgetting causes `invalidProgramId()` exceptions.

---

## 19. Top-level val configuration
Mappers and adapters often depend on a top-level val like `val configProp = ConfigProps.configProp`. Tests must ensure config is set up before importing mapper/adapter classes.

---

## 20. Journey-based testing strategy
Prefer journey-based testing on enterprise services:
- Trace the complete user journey before writing any test
- Test `CartService.getCart()` understanding the full flow: Route → Service → Adapter → Client → Mapper
- Use the DTO registry for constructor signatures — never re-read DTO files
- Use journey-weighted prioritization: critical journeys → orchestration → adapters → mappers → utils → gap fill

---

## 21. Kotlin/Ktor enterprise completion checklist
Before accepting a batch on enterprise Kotlin projects:
- JaCoCo exclusions checked and respected,
- DTO constructors verified against current production signatures (or DTO registry),
- Extension function imports correct,
- Global mutable state initialized in `@BeforeEach`,
- Top-level config vals set up before class loading,
- Koin started with required bindings even for throw-only tests,
- NotImplemented patterns used for interface coverage,
- Journey-weighted targets prioritized over individual function tests.

---

## 22. Assembler-service deep engagement learnings (Kotlin/Ktor, 15K+ lines)

### Coverage progression: 36.3% → 55.5% over 7 waves
- **Wave 1 (CASCADE):** Services first → 43.2% (+6.9%). Highest ROI from service-level tests.
- **Wave 2-4 (MAPPERS):** Mapper v1/v2/v3 → 46.5%. Deep mapper logic requires precise DTO knowledge.
- **Wave 5-6 (DEEP):** Complex functions + all mappers → 54.4%. 429 new tests in parallel push.
- **Wave 7 (ADAPTER):** CromaAdapterDeepTest → 55.5%. Adapter validation code = easy coverage gains.

### Key patterns discovered
- **Suspend inline reified = untestable**: `CromaClient` methods are `suspend inline fun <reified T>`. MockK cannot mock them, JaCoCo cannot instrument them. ~280 lines are a hard ceiling.
- **Adapter try/catch pattern**: Wrap adapter calls in try/catch to cover validation code before the unmockable CromaClient call.
- **ConfigProps mockkObject pattern**: `mockkObject(ConfigProps); every { configProp } returns ConfigPropDto()` in @BeforeEach. Required by almost every class.
- **Import ambiguity**: Must use `import org.junit.jupiter.api.Test` NOT wildcard imports — ambiguity with `kotlin.test.Test`.
- **Realistic ceiling**: ~85-88% due to inline reified functions being untestable with current tools.

### Speed observations
- Parallel agents got stuck after ~10-15 tool calls on complex mapper methods
- DTO re-reading across waves wasted significant time (fixed by DTO Registry in v2)
- Static priority order missed high-value targets (fixed by Journey-Weighted Prioritization in v2)

