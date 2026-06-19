# Problem Statement — Milestone 4: Automations & Multi-Agent Systems

## Context

This milestone focuses on **multi-agent orchestration**: how several specialized AI agents can collaborate on a single real-world task that product managers can easily understand.

Unlike Milestone 3 (a single agent calling MCP tools), here you design a **Travel Planning Multi-Agent System** — a supervisor orchestrator plus seven domain-specific agents that turn a short natural-language travel request into a structured, validated trip plan.

The goal is **not** to build a production travel product. It is to demonstrate clear agent boundaries, shared state, orchestration phases, and a validation loop — with explainable output suitable for demos.

---

## Background

Planning a trip sounds simple at first, but in practice it quickly becomes overwhelming.

A traveler may have a request like:

> Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds.

To fulfill that well, we need to combine many different kinds of work:

- Understanding the traveler's goals
- Researching destinations and attractions
- Comparing hotels and transport options
- Staying within budget
- Checking whether the final itinerary actually matches the request

No single monolithic prompt handles this well. Each concern maps naturally to a **specialized agent** coordinated by an **orchestrator**.

---

## Goal

Design a simple **AI Travel Planner** that automatically turns a short travel request into a useful trip plan.

**Input:** Natural-language travel request (duration, destinations, budget, preferences, constraints).

**Output:** A final itinerary that includes:

1. **Day-by-day trip outline**
2. **Suggested neighborhoods / areas to stay**
3. **Travel logistics between cities**
4. **Budget-friendly recommendations**
5. **Evidence that preferences and constraints were respected**

---

## Who This Helps

| Audience | Benefit |
|----------|---------|
| **Travelers** | A coherent first draft without hours of fragmented research |
| **Product Managers** | A concrete example of multi-agent workflows they can explain to stakeholders |
| **Engineers** | A clean separation of concerns: one agent per planning task, shared artifacts, orchestrated pipeline |

---

## Real-World Problem: "AI Travel Planner"

### Canonical example request

```
Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds.
```

### Expected deliverable shape

The system should produce a scannable itinerary (markdown or similar) covering:

| Section | Content |
|---------|---------|
| **Overview** | Parsed constraints, trip length, destinations, budget |
| **Day-by-day plan** | Activities, themes, and logistics per day |
| **Where to stay** | Neighborhood recommendations per city |
| **Transport** | Inter-city routes (e.g. Tokyo ↔ Kyoto), local transit notes |
| **Budget** | Estimated costs by category with total vs. budget |
| **Validation** | Pass/fail sign-off or explicit list of unresolved gaps |

---

## What You Must Build

### 1. Shared trip state

A single source of truth (`TripState`) that evolves as agents run. Core artifacts:

| Artifact | Primary owner | Description |
|----------|---------------|-------------|
| `trip_spec` | Request Parser | Structured constraints and preferences |
| `destination_research` | Destination Research | Attractions, areas, timing tips per city |
| `accommodation_options` | Accommodation | Neighborhoods and stay recommendations |
| `transport_plan` | Transport | Inter-city and local logistics |
| `budget_breakdown` | Budget | Estimated costs by category |
| `draft_itinerary` | Itinerary Composer | Day-by-day outline |
| `validation_report` | Validator | Pass/fail + gaps vs. original request |

### 2. Seven specialized agents

Each agent owns **one slice** of travel planning. Agents do not call each other directly; the orchestrator passes shared state.

| Agent | Traveler question it answers | Primary output |
|-------|------------------------------|----------------|
| **Request Parser** | "What did you think I meant?" | `trip_spec` |
| **Destination Research** | "What should we do there?" | `destination_research` |
| **Accommodation** | "Where should we stay?" | `accommodation_options` |
| **Transport** | "How do we get between cities?" | `transport_plan` |
| **Budget** | "Can we afford this?" | `budget_breakdown` |
| **Itinerary Composer** | "What does each day look like?" | `draft_itinerary` |
| **Validator** | "Does this match what I asked?" | `validation_report` |

### 3. Orchestrator (supervisor)

The orchestrator is the **project manager**: it schedules agents, merges artifacts, runs validation retries, and delivers the final itinerary.

**Workflow phases:**

| Phase | Agents | Parallelism |
|-------|--------|-------------|
| 1. Understand | Request Parser | Sequential (must run first) |
| 2. Gather | Destination Research, Accommodation, Transport | **Parallel** |
| 3. Constrain | Budget | Sequential (needs phase 2) |
| 4. Synthesize | Itinerary Composer | Sequential |
| 5. Verify | Validator | Sequential |
| 6. Remediate | Orchestrator + subset of agents | Conditional retry loop |

**Retry policy:** Max **2** validation retries (configurable). On failure, attach `validation_report.issues` to targeted agent re-runs. If still failing, return best-effort itinerary plus explicit unresolved issues.

### 4. Structured contracts

**Trip Spec** (example produced by Request Parser):

```json
{
  "duration_days": 5,
  "destinations": ["Tokyo", "Kyoto"],
  "country": "Japan",
  "budget_usd": 3000,
  "preferences": ["food", "temples"],
  "constraints": ["avoid crowds"],
  "travel_style": "mid-range",
  "party_size": 1
}
```

Fields may be inferred with defaults when omitted (e.g. `party_size: 1`).

All agent outputs must be **structured (JSON / Pydantic)** so the orchestrator can merge reliably. Include `trip_spec` in every post-parse agent call to ground responses in user constraints.

### 5. CLI entrypoint

A single command should run the full pipeline end-to-end, e.g.:

```bash
plan "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds."
```

---

## Key Constraints

- **Agent separation:** Each artifact has exactly one primary writer agent; no direct agent-to-agent calls
- **Phase 1 data source:** Fully **LLM-driven** plans — mock or LLM-grounded knowledge is sufficient; label estimates clearly
- **No real-time booking:** No payments, live inventory APIs, or production travel integrations in MVP
- **Schema validation:** Validate agent outputs before merging; retry once on malformed JSON
- **Explainability:** Final output includes a short "How this plan was built" section (parsed constraints, agent contributions, budget summary, validator sign-off)
- **Security:** Treat user requests as sensitive; API keys via environment variables only (`.env` not committed)
- **Cost control:** Parallelize only independent agents in phase 2 (3 calls, not 7 serial)

### Validator minimum rules

- Trip length equals `duration_days`
- All destinations appear in the outline
- Estimated total ≤ `budget_usd` (or explicit overage called out)
- Each preference reflected at least once
- Each constraint addressed (e.g. crowd-avoidance strategies present)

---

## Non-Goals (MVP)

- Real-time booking, payments, or live hotel/flight inventory APIs
- Production-grade latency, cost optimization, or global scale
- Perfect travel recommendations — **correct orchestration and explainable output** matter more than domain completeness
- Optional external APIs (maps, web search, hotels) — deferred to later phases

---

## Technology Direction (recommended)

| Layer | Recommendation |
|-------|----------------|
| Language | Python 3.11+ |
| LLM access | Provider SDK (Groq for research/accommodation/transport; Gemini for budget/validator — two "brains" in the system) |
| Orchestration | Custom lightweight supervisor (avoid heavy frameworks until complexity demands it) |
| Schemas | Pydantic + JSON Schema |
| Interface | CLI first; optional FastAPI wrapper later |
| Observability | Structured logs per `run_id`; export trace as markdown for PM review |

---

## Success Criteria

- [ ] Single CLI command produces a full markdown itinerary from a natural-language request
- [ ] Validator passes on the canonical Japan fixture (5 days, Tokyo + Kyoto, food + temples, crowd mitigation, ≤ $3,000)
- [ ] Each artifact has exactly one primary writer agent
- [ ] Non-engineer can name 5+ agents and their roles after a 10-minute walkthrough
- [ ] Forced budget overrun surfaces in `validation_report`, not silent omission
- [ ] Final output includes day-by-day outline, neighborhoods, transport, budget breakdown, and validation sign-off
- [ ] Orchestrator runs phase 2 agents in parallel and supports validation retry loop

---

## Evolution Roadmap (future phases)

| Phase | Scope |
|-------|-------|
| **MVP (Phase 1)** | Orchestrator + 7 agents + CLI + in-memory state; LLM-only data |
| **v1.1** | Persist `TripState` to disk; rerun from last failed phase |
| **v1.2** | Optional tools: web search, maps API for real distances |
| **v2** | Human-in-the-loop approval between Validator and delivery |
| **v2+** | Specialized sub-agents (e.g. Food Agent, Culture Agent); real data for Indian cities and other destinations |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `docs/architecture.md` | Detailed system architecture, agent catalog, orchestration diagrams |
| `docs/implementation-plan.md` | Phase-wise build plan and data strategy |
| `docs/edgecases.md` | Edge cases and failure modes |
| `docs/eval.md` | Evaluation checklist for milestone sign-off |

---

## PM Cheat Sheet

| Traveler concern | Agent |
|------------------|-------|
| "What did you think I meant?" | Request Parser |
| "What should we do there?" | Destination Research |
| "Where should we stay?" | Accommodation |
| "How do we get between cities?" | Transport |
| "Can we afford this?" | Budget |
| "What does each day look like?" | Itinerary Composer |
| "Does this actually match what I asked?" | Validator |

**The Orchestrator** schedules the team, combines their work, and sends revisions when QA fails.
