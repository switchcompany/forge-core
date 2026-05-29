# Forge Core — Product Overview

## The Problem

Backend teams spend **30-40% of development time** writing and maintaining unit tests. Most projects have:
- Incomplete coverage (industry average: 40-60%)
- Fragile tests that break with every refactor
- No consistent testing patterns across the team
- Knowledge silos — only the author understands the test

## The Solution

**Forge Core** is a **standalone SaaS product** — an AI-powered test generation engine that acts as a dedicated test engineer for your entire organization. It:

1. **Analyzes** your architecture (HLD, LLD, user journeys, DTOs)
2. **Generates** idiomatic unit tests in your project's style
3. **Iterates** until 90%+ coverage is achieved
4. **Learns** from every project, getting smarter over time
5. **Scales** across teams — multi-company, multi-user, isolated environments

### Zero Risk Guarantee
- ✅ Never modifies production code
- ✅ Never deletes existing tests
- ✅ Automatic rollback if coverage drops
- ✅ No secrets or proprietary code stored
- ✅ Runs in your environment — code never leaves your infrastructure

---

## What You Get

### For Developers
- **Hours saved**: Typical project goes from 0% → 85%+ coverage in one run
- **Quality tests**: Not boilerplate — tests that actually catch bugs
- **Consistent patterns**: Same testing conventions across all services
- **Edge case coverage**: Null inputs, error paths, boundary conditions, concurrency
- **Speed**: Parallel generation, smart batching — enterprise projects in under 45 minutes
- **Zero babysitting**: Auto compile-fix loop means you walk away and come back to results

### For Engineering Managers
- **Measurable coverage gains**: Before/after reports for every run
- **Team-wide knowledge**: Patterns learned on one project help all projects
- **Reduced review cycles**: Well-structured tests pass PR review faster
- **Compliance ready**: Coverage reports for audit requirements

### For CTOs
- **ROI**: A single test engineer costs $120K-180K/year. Forge Core delivers comparable output at a fraction of the cost
- **Scalability**: Works across all your backend services simultaneously
- **Vendor-agnostic**: Supports 9+ languages — no stack lock-in
- **Data privacy**: Runs in your environment, nothing leaves your infrastructure

---

## Supported Technologies

| Category | Technologies |
|----------|-------------|
| **Languages** | Python, Java, Kotlin, Go, Rust, C#, Ruby, PHP, Node.js |
| **Frameworks** | FastAPI, Django, Flask, Spring Boot, Ktor, Express, NestJS, Gin, Actix, ASP.NET, Rails, Laravel |
| **Databases** | PostgreSQL, MySQL, MongoDB, Redis, SQLite, DynamoDB |
| **Message Queues** | Kafka, RabbitMQ, SQS, Redis Streams |
| **Cloud** | AWS, Azure, GCP services |
| **CI/CD** | GitHub Actions, GitLab CI, Jenkins, CircleCI |

---

## How It Works

```
  ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
  │  Your Repo  │────▶│    Forge     │────▶│  PR with    │
  │  (any lang) │     │  Core Agent  │     │  New Tests  │
  └─────────────┘     └──────┬───────┘     └─────────────┘
                             │
                    ┌────────┼────────┐
                    ▼        ▼        ▼
              ┌─────────┐┌────────┐┌──────────┐
              │ Analyze ││Generate││ Coverage │
              │ & Learn ││ Tests  ││ Report   │
              └─────────┘└────────┘└──────────┘
```

### Workflow Phases

| # | Phase | Duration | Output |
|---|-------|----------|--------|
| 1 | Stack Detection | ~30s | Language, framework, test tools identified |
| 1.5 | Exclusion Scan | ~15s | Coverage exclusion map and included packages |
| 2 | Architecture Analysis | ~2min | HLD/LLD, dependency map, flow documentation |
| 2.5 | Journey Mapping & DTO Registry | ~2min | Journey map, DTO registry, mock boundaries, test strategy |
| 3 | Existing Test Audit | ~1min | Baseline coverage, gap analysis, quality score |
| 4 | Test Generation (iterative) | ~15-25min | New test files with 90%+ coverage |
| 5 | Final Report | ~30s | Before/after metrics, files created, remaining gaps |
| 6 | Knowledge Capture | ~30s | New patterns saved for future projects |

**Total time: ~20-30 minutes** (vs. 2-4 weeks manually)

---

## Multi-Tenant Architecture

Forge Core is designed for **multi-company, multi-user** operation:

```
┌─────────────────────────────────────────────────────┐
│                  Forge Core SaaS                     │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │  Company A   │  │  Company B   │  │Company C │  │
│  │  ┌────────┐  │  │  ┌────────┐  │  │┌────────┐│  │
│  │  │User A1 │  │  │  │User B1 │  │  ││User C1 ││  │
│  │  │User A2 │  │  │  │User B2 │  │  ││User C2 ││  │
│  │  │User A3 │  │  │  │User B3 │  │  │└────────┘│  │
│  │  └────────┘  │  │  └────────┘  │  └──────────┘  │
│  │              │  │              │                  │
│  │  Projects:   │  │  Projects:   │  Projects:      │
│  │  - api-svc   │  │  - payments  │  - storefront   │
│  │  - auth-svc  │  │  - billing   │  - admin-panel  │
│  │  - worker    │  │  - gateway   │                  │
│  │              │  │              │                  │
│  │  Learnings:  │  │  Learnings:  │  Learnings:     │
│  │  (isolated)  │  │  (isolated)  │  (isolated)     │
│  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────┘
```

### Isolation Model
| Scope | Isolation | Shared |
|-------|-----------|--------|
| **Company** | Full — data, learnings, reports never cross company boundaries | Product updates, knowledge packs |
| **User** | RBAC within company — admin, developer, viewer roles | Company learnings, project reports |
| **Project** | Independent runs, independent coverage tracking | Company-level learnings |
| **Knowledge** | Company learnings are private | Public knowledge packs (language patterns) shipped with product |

### Delivery Channels
| Channel | Description | Use Case |
|---------|-------------|----------|
| **CLI** | `forge-core run /path/to/project` | Local development, quick runs |
| **CI/CD** | GitHub Action / GitLab CI step | Automated pipeline, PR-triggered |
| **Web Portal** | [theswitchcompany.online](https://theswitchcompany.online) | Dashboard, config, reports, team management |

---

## Proven Results

### Case Study: AI Social Media Monitor (Python/FastAPI)

**Project Profile:**
- Language: Python 3.9
- Framework: FastAPI + async/await
- Components: REST API, NLP classifier, email notifier, SQLite database, Reddit poller
- Lines of code: ~1,200

**Results:**

| Metric | Before Forge Core | After Forge Core |
|--------|-------------------|------------------|
| Line Coverage | 0% | 89% |
| Test Files | 0 | 8 |
| Test Cases | 0 | 145 |
| Edge Cases Covered | 0 | 47 |
| Execution Time | — | 18 minutes |

**What was generated:**
- API endpoint tests (all routes, error handling, validation)
- NLP classifier tests (sentiment analysis, keyword boosting, edge cases)
- Email notification tests (API, SMTP, and console fallback paths)
- Database tests (CRUD operations, concurrent access, error handling)
- Pipeline integration tests (classify → notify → save flow)
- Configuration tests (env vars, defaults, caching)

### Case Study: Enterprise E-Commerce Backend (Kotlin/Ktor)

**Project Profile:**
- Language: Kotlin 2.0
- Framework: Ktor + Koin DI
- Components: REST API, adapters, mappers, services, Redis/Dapr clients
- Lines of code: ~15,000
- Existing test coverage: 35.1% line coverage

**Results:**

| Metric | Before Forge Core | After Forge Core |
|--------|-------------------|------------------|
| Line Coverage | 35.1% | 36.3% |
| Method Coverage | 44.2% | 48.2% |
| Test Files | 60 | 69 |
| Test Cases | 269 | 416 |
| Patterns Discovered | — | 9 |
| Execution Time | — | ~45 minutes |

---

## Pricing

| Plan | Price | What's Included |
|------|-------|----------------|
| **Starter** | Free | 1 repo, 500 tests/month, Core OR UI |
| **Pro** | $49/mo per repo | Unlimited tests, both agents, CI/CD, cross-project learning |
| **Enterprise** | Custom | Unlimited repos, self-hosted, SSO, SLA, org-wide learning |

---

## Getting Started

1. **Sign up** at [theswitchcompany.online](https://theswitchcompany.online)
2. **Install** Forge Core in your repository
3. **Run** your first analysis
4. **Review** the generated tests and coverage report
5. **Merge** — tests are production-ready

---

## FAQ

**Q: Does it work with monorepos?**
A: Yes. Forge Core detects monorepo structures and can target specific modules.

**Q: Will it break my existing tests?**
A: No. It never deletes existing tests and has rollback protection if coverage drops.

**Q: Does it need GitHub Copilot?**
A: No. Forge Core is a **standalone product**. It works with any AI runtime — Copilot, Claude, GPT, or local LLMs. The engine is runtime-agnostic; the AI runtime is just one execution backend.

**Q: Does it need access to my source code?**
A: It runs locally in your environment. No code leaves your infrastructure. In SaaS mode, code is processed in isolated containers and never stored.

**Q: How is this different from Copilot's built-in test generation?**
A: Copilot generates tests for individual functions. Forge Core understands your entire architecture, traces user journeys, builds a DTO registry, iterates for coverage, handles complex mocking, and learns from every project across your organization.

**Q: Can it generate integration tests?**
A: The current focus is unit tests. Integration and E2E test generation is on the roadmap.

---

<p align="center">
  <strong>Ready to automate your backend testing?</strong><br/>
  <a href="https://theswitchcompany.online/contact?product=forge">Get Started →</a>
</p>
