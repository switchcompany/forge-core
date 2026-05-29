# 🔥 Forge Core — AI Backend Test Generation Engine

> **Standalone SaaS product that auto-generates unit tests for any backend project, in any language.**
> Zero production code changes. 90%+ coverage. Self-learning. Multi-tenant.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Engine: AI](https://img.shields.io/badge/Engine-AI%20Powered-purple.svg)](#how-it-works)
[![Stacks: 9+](https://img.shields.io/badge/Stacks-9%2B%20Languages-green.svg)](#supported-stacks)

---

## 🎯 What It Does

Forge Core is an **AI-powered test generation engine** that analyzes your backend codebase and generates comprehensive unit tests — automatically. It understands your architecture, traces user journeys, builds a DTO registry, writes idiomatic tests, and iterates until coverage targets are met.

```
Your Backend Project + Forge Core = 90%+ Test Coverage
```

### Key Capabilities

| Feature | Description |
|---------|-------------|
| 🔍 **Auto Stack Detection** | Detects language, framework, test tools, and coverage system automatically |
| 🧠 **Deep Architecture Analysis** | Understands HLD/LLD, dependency chains, DI containers, and data flows |
| ✍️ **Intelligent Test Generation** | Writes idiomatic tests using your project's existing patterns and conventions |
| 🔄 **Iterative Coverage Loop** | Runs up to 10 iterations, each time targeting the biggest coverage gaps |
| 🛡️ **Rollback Protection** | Never allows coverage to drop — automatically reverts harmful changes |
| 📚 **Self-Learning** | Captures new patterns after each run, making itself smarter for every future project |
| 🎯 **Targeted Mode** | Generate tests for specific classes only (with dependency mocking) |
| 🏗️ **Monorepo Support** | Works with multi-module projects (Gradle, npm workspaces, etc.) |
| 🎯 **Coverage Exclusion Detection** | Detects excluded packages before generating tests — zero wasted effort |
| 🌊 **Journey Mapping** | Traces complete user flows through the codebase for deep understanding before testing |
| 📦 **DTO Registry** | Reads all data classes once, shares everywhere — zero re-reading |
| 📊 **Coverage Impact Predictor** | Estimates which tests will cover the most lines before writing them |
| ⚡ **Auto Compile-Fix** | Autonomously fixes compilation errors — zero human intervention needed |
| 🤖 **Agent Self-Resolution** | Stuck agents auto-recover: heartbeat monitoring, scope splitting, graceful termination |
| 🏢 **Enterprise Project Graph** | 4-Level DAG decomposes any project for parallel analysis and testing |
| 🚀 **Speed-Optimized** | Parallel generation, smart batching, incremental coverage, architecture caching |
| 🏗️ **Multi-Tenant SaaS** | Multiple companies, multiple users per company — isolated and secure |

---

## 🚀 Quick Start

### Delivery Channels

Forge Core runs as a **standalone engine** with three delivery channels:

| Channel | Use Case | How |
|---------|----------|-----|
| **CLI** | Local development | `forge-core run /path/to/project` |
| **CI/CD** | Automated pipelines | GitHub Actions, GitLab CI, Jenkins |
| **Web Portal** | Team dashboard | [theswitchcompany.online](https://theswitchcompany.online) |

### Option A — CLI (Local)
```bash
# Install
git clone https://github.com/switchcompany/forge-core.git
cd forge-core

# Run on your project
./setup.sh /path/to/your/backend/project

# Execute with any AI runtime (Copilot, Claude, GPT, local LLM)
# The engine reads .github/copilot-instructions.md and prompts/
```

### Option B — CI/CD Integration
```yaml
# .github/workflows/forge-core.yml
- name: Run Forge Core
  uses: switchcompany/forge-core-action@v2
  with:
    target: full     # or "targeted: src/services/UserService.kt"
    coverage: 90
```

### Option C — Web Portal
1. Sign up at [theswitchcompany.online](https://theswitchcompany.online)
2. Connect your repository
3. Configure coverage targets
4. Forge Core runs automatically on PRs or on-demand

---

## 📊 Supported Stacks

| Language | Frameworks | Test Runner | Mock Library | Coverage |
|----------|-----------|-------------|--------------|----------|
| **Python** | FastAPI, Django, Flask, Starlette | pytest | unittest.mock, pytest-mock | pytest-cov |
| **Java** | Spring Boot, Micronaut, Quarkus | JUnit 5 | Mockito | JaCoCo |
| **Kotlin** | Ktor, Spring Boot | JUnit 5, Kotest | MockK | Kover, JaCoCo |
| **Node.js** | Express, Fastify, NestJS, Koa | Jest, Vitest, Mocha | jest.mock, sinon | c8, istanbul |
| **Go** | stdlib, Gin, Echo, Fiber | testing | testify, gomock | go cover |
| **Rust** | Actix, Axum, Rocket | built-in | mockall | tarpaulin |
| **C#** | ASP.NET Core, Minimal APIs | xUnit, NUnit | Moq, NSubstitute | coverlet |
| **Ruby** | Rails, Sinatra, Hanami | RSpec, Minitest | rspec-mocks | simplecov |
| **PHP** | Laravel, Symfony, Slim | PHPUnit | Mockery, Prophecy | phpunit --coverage |

---

## 🔄 How It Works

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Forge Core — Engine                             │
│                                                                      │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ Load    │─▶│ Detect  │─▶│ Exclusion│─▶│ Analyze  │─▶│Journey │  │
│  │Learnings│  │ Stack   │  │  Scan    │  │ Project  │  │Mapping │  │
│  └─────────┘  └─────────┘  └──────────┘  └──────────┘  └───┬────┘  │
│                                                              │       │
│  ┌─────────┐  ┌──────────────────────────────────────┐      │       │
│  │ Self-   │◀─│     Iteration Loop (×10)             │◀─────┘       │
│  │ Learn   │  │ Fix → Generate → Auto-Fix → Rollback │              │
│  └─────────┘  └──────────────────────────────────────┘              │
│                                                                      │
│  Output: Tests + Coverage Report + Journey Map + DTO Registry        │
└──────────────────────────────────────────────────────────────────────┘
```

### Phase Breakdown

| Phase | Action | Output |
|-------|--------|--------|
| **-1** | Load learnings from central hub + local | Pattern library |
| **0** | User confirmation (full/targeted/analyze) | Mode selection |
| **1** | Detect tech stack from build files | Stack profile |
| **1.5** | Scan coverage exclusions | Exclusion map |
| **2** | Deep project analysis (HLD/LLD/flows) | Architecture map |
| **2.5** | Journey mapping & DTO registry | Journey map, DTO registry, mock boundaries |
| **3** | Scan & run existing tests, measure baseline | Baseline coverage % |
| **3.5** | Fix broken tests (10+ battle-tested patterns) | Fixed test suite |
| **4** | Iterative test generation with auto compile-fix (up to 10 rounds) | New test files |
| **5** | Final report (before/after, gaps, files) | Coverage report |
| **6** | Capture new patterns to LEARNINGS.md | Updated knowledge |

---

## 🛡️ Safety Guarantees

- ✅ **Zero production code changes** — only test files are created/modified
- ✅ **Rollback protection** — coverage never goes backwards
- ✅ **No flaky tests** — deterministic assertions, no random/network/timing
- ✅ **Existing tests preserved** — never deletes passing tests
- ✅ **No secrets in learnings** — LEARNINGS.md contains patterns, never source code

---

## 📚 Knowledge Packs

Pre-seeded knowledge for common stacks (in `knowledge-packs/`):

| Pack | Patterns | Source |
|------|----------|--------|
| `python-fastapi.md` | 15+ patterns | Learned from production FastAPI project |
| `kotlin-ktor.md` | 11+ patterns | Learned from production Ktor/Koin project |
| `java-spring.md` | 12+ patterns | Spring Boot best practices |
| `node-express.md` | 10+ patterns | Express/NestJS patterns |
| `go-stdlib.md` | 10+ patterns | Go testing idioms |

These grow automatically as the agent runs on more projects.

---

## 📁 Repository Structure

```
forge-core/
├── .github/
│   ├── copilot-instructions.md          # Agent brain — 500+ lines of instructions
│   ├── copilot-setup-steps.yml          # Environment verification
│   ├── agent-config.yml                 # Central hub path config
│   ├── ISSUE_TEMPLATE/
│   │   └── analyze-and-test.yml         # GitHub Issue trigger template
│   └── prompts/
│       ├── full-workflow.prompt.md      # Main orchestrator
│       ├── detect-tech-stack.prompt.md  # Stack detection playbook
│       ├── coverage-exclusion-scan.prompt.md  # Coverage exclusion scan
│       ├── analyze-project.prompt.md    # Architecture analysis
│       ├── journey-mapping.prompt.md   # Journey tracing & DTO registry
│       ├── analyze-existing-tests.prompt.md  # Test audit
│       ├── generate-coverage-report.prompt.md  # Coverage tools
│       ├── write-unit-tests.prompt.md   # Test writing playbook
│       ├── fix-broken-tests.prompt.md   # Fix patterns
│       └── self-learn.prompt.md         # Knowledge capture
├── knowledge-packs/
│   ├── python-fastapi.md
│   ├── kotlin-ktor.md
│   ├── java-spring.md
│   ├── node-express.md
│   └── go-stdlib.md
├── LEARNINGS.md                         # Cross-project knowledge base
├── setup.sh                             # Project setup script
├── update.sh                            # Update script
├── ARCHITECTURE.md                      # System architecture docs
├── CONTRIBUTING.md                      # Contribution guide
├── SECURITY.md                          # Security policy
└── LICENSE                              # MIT License
```

---

## 📈 POC Results

### Sentinel — AI Social Media Monitor (Python/FastAPI)

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| **Line Coverage** | 0% | 89% | +89% |
| **Test Files** | 0 | 8 | +8 |
| **Test Cases** | 0 | 145 | +145 |
| **Iterations** | — | 3 | — |
| **Production Files Modified** | — | 0 | ✅ |

**Patterns Discovered:** 11 (cached settings, async mocking, ASGI testing, DB isolation, lifespan override, fallback behavior testing, NLP model mocking)

### Assembler-Service — Enterprise E-Commerce Backend (Kotlin/Ktor)

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| **Line Coverage** | 35.1% | 55.5% | +20.4% |
| **Method Coverage** | 44.2% | ~65% | +~21% |
| **Test Files** | 60 | ~85 | +~25 |
| **Test Cases** | 269 | ~1,200 | +~930 |
| **Patterns Discovered** | — | 19 | — |
| **Production Files Modified** | — | 0 | ✅ |

**Key Achievement:** Enterprise-grade Kotlin codebase with 209 source files, 15K+ lines, Koin DI, MockK, complex adapter patterns. 7 waves of generation. Discovered 19 reusable patterns including 3 that drove product v2 improvements.

---

## 🏢 Enterprise Features

- **Multi-tenant SaaS** — multiple companies, isolated environments, per-org knowledge
- **Cross-project learning** — patterns from Project A help Project B automatically
- **Central knowledge hub** — org-wide learnings sync automatically
- **Journey-based testing** — understands WHY each function exists before writing tests
- **Enterprise Project Graph** — 4-Level DAG decomposes any project size
- **Agent self-resolution** — zero user intervention required during runs
- **Targeted mode** — test specific classes without analyzing the entire project
- **Monorepo support** — works with multi-module builds
- **CI/CD integration** — trigger via CLI, GitHub Actions, or web portal
- **Audit trail** — every decision logged in the final report

---

## 📄 License

MIT © 2025 [TheSwitchCompany](https://theswitchcompany.online)

---

<p align="center">
  <strong>Forge Core</strong> — Part of the <a href="https://theswitchcompany.online">TheSwitchCompany</a> AI Agent Suite<br/>
  <em>Forge Core · Forge UI · More agents coming soon</em>
</p>
