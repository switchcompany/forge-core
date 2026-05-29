# Forge Core — Architecture

## System Overview

Forge Core operates as an **engine-first architecture**: the AI test generation engine is the core product, delivered through multiple channels.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      CORE ENGINE (forge-core)                         │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐   │
│  │   Prompts    │  │  Knowledge   │  │     LEARNINGS.md          │   │
│  │  (workflow)  │  │   Packs      │  │  (cross-project memory)   │   │
│  └──────────────┘  └──────────────┘  └───────────────────────────┘   │
│                                                                       │
│  Engine delivers to projects via setup.sh or API                      │
└────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   CLI Channel   │ │  CI/CD Channel  │ │  Web Portal     │
│                 │ │                 │ │  Channel        │
│ forge-core run  │ │ GitHub Action / │ │ theswitchco.    │
│ /path/to/proj   │ │ GitLab CI step  │ │ online          │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────┐
│              AI Runtime (execution backend)               │
│                                                          │
│  Any compatible AI runtime:                              │
│  GitHub Copilot · Claude · GPT · Local LLM               │
│                                                          │
│  Engine reads prompts + instructions and executes using  │
│  available tools: bash, glob, grep, view, edit, create   │
│                                                          │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────────┐  │
│  │Analyze │▶│Generate│▶│  Run   │▶│ Report + Learn  │  │
│  │ Code   │ │ Tests  │ │ Tests  │ │                 │  │
│  └────────┘ └────────┘ └────────┘ └─────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Knowledge Flow

```
                    ┌─────────────┐
                    │ Central Hub │
                    │ LEARNINGS   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │Project A │ │Project B │ │Project C │
        │(Python)  │ │(Kotlin)  │ │(Go)      │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                    ┌─────────────┐
                    │ Central Hub │
                    │ LEARNINGS   │
                    │ (enriched)  │
                    └─────────────┘

Bidirectional sync: Read at start, Write at end
```

## Phase Pipeline Detail

### Detection → Analysis → Generation → Learning

```
Phase -1: Load LEARNINGS.md from central hub + local project
     │
Phase 0: User selects mode (Full / Targeted / Analyze Only)
     │
Phase 1: DETECT STACK
     │  Read build files (pom.xml, build.gradle, package.json, go.mod, etc.)
     │  Determine: language, framework, test runner, mock library, coverage tool
     │  Detect monorepo structure if applicable
     │
Phase 1.5: COVERAGE EXCLUSION SCAN
     │  Read build/coverage config for exclusion patterns
     │  Classify excluded vs included packages
     │  Adjust target list to avoid wasted effort
     │
Phase 2: ANALYZE PROJECT
     │  HLD: system purpose, module map, integrations, communication patterns
     │  LLD: per-module classes, public APIs, data models, DI setup
     │  Flows: request lifecycle, business logic, error handling
     │
Phase 2.5: JOURNEY MAPPING & DTO REGISTRY
     │  Discover entry points, trace complete user journeys
     │  Build DTO registry (read once, share everywhere)
     │  Map mock boundaries per journey
     │  Produce journey-weighted test strategy
     │
Phase 3: AUDIT EXISTING TESTS
     │  Scan test directories
     │  Compile and run existing tests
     │  Generate baseline coverage report
     │  Produce gap analysis table
     │
Phase 3.5: FIX BROKEN TESTS
     │  Apply 10+ battle-tested fix patterns
     │  Re-run coverage, update baseline
     │
Phase 4: ITERATIVE TEST GENERATION + AUTO COMPILE-FIX LOOP (up to 10 rounds)
     │  ┌─ 4.1: Identify coverage gaps
     │  │  4.2: Generate tests (prioritized by impact)
     │  │  4.3: Compile, auto-fix, run, measure coverage
     │  │  4.4: Rollback protection (revert if coverage drops)
     │  │  4.5: Check exit conditions (target reached / max iterations / stall)
     │  └─ Loop back to 4.1 if not done
     │
Phase 5: GENERATE FINAL REPORT
     │  Before/after coverage, files created/modified, remaining gaps
     │
Phase 6: SELF-LEARN
        Capture new patterns → LEARNINGS.md → sync to central hub
```

## Coverage Rollback Algorithm

```
BEST_COVERAGE = baseline
STALL_COUNT = 0

for iteration in 1..MAX_ITERATIONS:
    generate_tests()
    NEW_COVERAGE = measure_coverage()

    if NEW_COVERAGE < BEST_COVERAGE:
        # Coverage dropped — try to fix
        fix_failing_tests()
        NEW_COVERAGE = measure_coverage()

        if NEW_COVERAGE < BEST_COVERAGE:
            # Still dropping — rollback
            delete_new_test_files()
            log("Iteration {N} rolled back")
            STALL_COUNT += 1
    else:
        delta = NEW_COVERAGE - BEST_COVERAGE
        BEST_COVERAGE = NEW_COVERAGE

        if delta < 2.0:
            STALL_COUNT += 1
        else:
            STALL_COUNT = 0

    # Exit conditions
    if BEST_COVERAGE >= TARGET: break    # Target reached
    if STALL_COUNT >= 2: break           # Diminishing returns
```

## Enterprise Project Graph (4-Level DAG)

The structural backbone of Forge Core v2. Every project — small or enterprise-scale — is decomposed into this universal structure before any test is written.

```
Level 0: Project
├── Level 1: Modules (parallelism boundary)
│   ├── Level 2: Layers (route, service, adapter, client, mapper, validator, util, dto)
│   │   └── Level 3: Journeys (real user flows traced across layers)
│   │       └── Level 4: Components (individual classes/functions with testability scores)
```

### How Each Level Drives Testing

| Level | What It Contains | How It's Used |
|-------|-----------------|---------------|
| **0 — Project** | Root metadata: language, framework, build tool, LOC | Stack detection, knowledge pack selection |
| **1 — Modules** | Backend packages/services | **Parallelism boundary** — distribute across agents |
| **2 — Layers** | Architectural layers per module | Layer classification drives mock strategy |
| **3 — Journeys** | Real user flows crossing layers | **Understanding boundary** — know WHY before testing |
| **4 — Components** | Individual classes/functions | **Prioritization boundary** — testability score drives order |

### Journey Tracing (replaces Cascade)

Instead of measuring cascade depth (layers traversed), Forge Core traces **complete user journeys**:

```
Journey: "getCart"
  Entry:   GET /api/v1/cart/{userId}
  Path:    CartRoute → CartService → CartAdapter → CromaClient → CartMapper
  DTOs:    CartRequest → CartEntity → CartResponse
  Versions: v1 (legacy), v2 (current)
  Branches: cache hit/miss, empty cart, expired items
```

Each journey produces a **journey test strategy** — which components to test, what to mock, what data to use — before any test file is created.

### DTO Registry (Zero Re-Reading)

All DTOs are read **once** during journey mapping and stored in a structured registry:

```
DTO Registry Entry:
  class: CartItemDto
  package: com.example.dto
  constructor: (id: String, name: String, price: Double, quantity: Int = 1)
  defaults: { quantity: 1 }
  used_in_journeys: [getCart, addToCart, checkout]
  used_by_layers: [service, mapper, adapter]
```

Every agent receives the registry. No agent ever re-reads a DTO file.

## Auto Compile-Fix Loop

```
Generate Test Batch
        │
        ▼
    Compile ──── Pass ──── Run Tests ──── Coverage
        │
      Fail
        │
        ▼
  Classify Error ──┬── DTO drift → fix constructors
                   ├── Missing import → add import
                   ├── Wrong mock type → fix every/coEvery
                   ├── Type mismatch → align types
                   └── DI setup → add Koin/Spring config
        │
        ▼
   Recompile (up to 3 retries)
        │
      Still failing?
        │
        ▼
   Isolate broken test → continue with working tests
```

## Speed & Parallel Execution Architecture

```
┌─────────────────────────────────────────────────────────┐
│               ORCHESTRATOR (full-workflow)               │
│                                                         │
│  Phase 1-2.5 ─── Sequential (architecture analysis)    │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────┐            │
│  │        PARALLEL GENERATION ENGINE        │            │
│  │                                         │            │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐  │            │
│  │  │ Scope A │ │ Scope B │ │ Scope C │  │  Parallel  │
│  │  │ Agent   │ │ Agent   │ │ Agent   │  │  agents    │
│  │  │ (pkg.a) │ │ (pkg.b) │ │ (pkg.c) │  │  per scope │
│  │  └────┬────┘ └────┬────┘ └────┬────┘  │            │
│  │       │           │           │        │            │
│  │       ▼           ▼           ▼        │            │
│  │  ┌──────────────────────────────────┐  │            │
│  │  │          MERGE & VALIDATE        │  │            │
│  │  │    Full suite → Coverage report  │  │            │
│  │  └──────────────────────────────────┘  │            │
│  └─────────────────────────────────────────┘            │
│       │                                                 │
│       ▼                                                 │
│  .forge-cache/ ── Architecture + journey map + DTO registry │
│       │            (cached for repeat runs)             │
│       ▼                                                 │
│  Target reached? ── YES → Early exit                    │
│                     NO  → Next iteration                │
└─────────────────────────────────────────────────────────┘
```

### Performance Optimization Layers

| Layer | Optimization | Impact |
|-------|-------------|--------|
| **Analysis** | Architecture + DTO registry caching in `.forge-cache/` | 60-70% faster on repeat runs |
| **Planning** | Lazy phase execution (skip unnecessary phases) | 2-5 min saved per run |
| **Generation** | Parallel agents per package scope | 4-6x throughput on large projects |
| **Compilation** | Smart batching (3-5 files, compile once) | ~3x fewer compile cycles |
| **Coverage** | Incremental (new tests only, full at boundaries) | ~50% faster iterations |
| **Scaffolding** | Pre-computed templates from knowledge packs | 30-40% faster per file |
| **Termination** | Early exit when target reached | No wasted generation |

## Security Model

- Engine runs entirely within the customer's environment (CLI/CI) or in isolated SaaS containers (Web Portal)
- No external API calls beyond project's own build tools
- No credentials stored or transmitted
- LEARNINGS.md contains only patterns, never source code
- Company data is fully isolated — learnings never cross tenant boundaries
- All operations are local in CLI mode; sandboxed in SaaS mode
