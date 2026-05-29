---
mode: agent
description: "Capture new backend testing learnings, deduplicate them, append safely, and sync to the central Forge Core hub"
tools: ["bash", "glob", "grep", "view", "edit"]
---

# Self-Learn

Run this at the end of every completed workflow.

## Step 1 — Reflect on the run
Review everything that happened and identify reusable learnings:
- new failure patterns,
- stack-specific mocking or fixture tactics,
- DI cleanup requirements,
- coverage tool issues and fallbacks,
- dead ends that wasted time,
- the highest-ROI test targets for that stack.

## Step 2 — Deduplicate
Read local `LEARNINGS.md` and, if configured, central `LEARNINGS.md`.
Only add learnings that are genuinely new and reusable.
Do not append duplicates or trivial rewordings.

## Step 3 — Sanitize before writing
Never store:
- secrets,
- credentials,
- tokens,
- proprietary business logic,
- copied large source snippets,
- personal data.

Convert learnings into generalized patterns.

## Step 4 — Append to local LEARNINGS.md
Add a new dated section with:
- project name,
- stack,
- numbered new patterns,
- coverage insights,
- blockers,
- useful notes for future runs.

Use this shape:

```markdown
### Project: {name} | Stack: {stack} | Date: {YYYY-MM-DD}

**New Patterns:**
1. ...

**Coverage Insights:**
- Starting: ...
- Final: ...
- Biggest wins: ...
- Blockers: ...

**Tech Stack Notes:**
- ...
```

## Step 4.5 — Enterprise Pattern Library
Structure each learning as a searchable pattern entry when the pattern is significant enough:

### Pattern format
```
#### [CATEGORY-NNN] Pattern Title
- **Stack:** Kotlin/Ktor, Python/FastAPI, Java/Spring, etc.
- **Category:** DTO-drift | mock-placement | DI-cleanup | coverage-tool | async-harness | cascade-coverage | exclusion-detection
- **Severity:** high | medium | low
- **Symptom:** What goes wrong
- **Root Cause:** Why it happens
- **Fix:** How to resolve it
- **Prevention:** How Forge Core avoids it in future runs
- **Discovered:** Project name, date
```

### Cross-project pattern matching
When loading learnings in Phase -1:
1. Filter patterns by the detected stack.
2. Prioritize high-severity patterns.
3. Pre-load relevant fix patterns into Phase 3.5 and Phase 5.
4. Track pattern hit rates — patterns that fire on every project are "universal", stack-specific ones are "conditional".

## Step 5 — Sync to central hub
Read `.github/agent-config.yml`.
If `central_agent_path` exists:
1. read central `LEARNINGS.md`,
2. append only the same new non-duplicate learnings,
3. leave the central file in a clean, deduplicated state.

## Step 6 — Update durable assets if needed
If a new durable pattern was discovered:
- update `.github/copilot-instructions.md`,
- update `fix-broken-tests.prompt.md`,
- update `write-unit-tests.prompt.md`,
- update `coverage-exclusion-scan.prompt.md` if new exclusion patterns were found,
- update `journey-mapping.prompt.md` if new journey patterns or mock boundaries were discovered,
- update or create a relevant knowledge pack.

## Step 7 — Report summary
Produce:

```markdown
## Self-Learning Report
- New patterns captured:
- Local LEARNINGS updated: yes/no
- Central LEARNINGS synced: yes/no
- Prompt/knowledge-pack updates made: yes/no
```

## Quality bar
A learning is worth saving only if it is:
- reusable across projects,
- specific enough to guide action,
- safe to share,
- more helpful than obvious.
