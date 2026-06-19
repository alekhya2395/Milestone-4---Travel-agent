# Demo Guide — Travel Planning Multi-Agent System

**Duration:** ~5 minutes live + 2 minutes Q&A  
**Audience:** PMs, reviewers, non-engineers  
**Prerequisite:** `.env` with `GROQ_API_KEY` and `GEMINI_API_KEY` (never share or commit)

---

## Before You Demo

1. **Security check** (run from project root):

   ```powershell
   .\.venv\Scripts\Activate.ps1
   pytest tests/test_safety.py tests/test_phase4_fixtures.py::test_trace_redacts_pii_and_secrets -q
   ```

2. **Quota check:** Gemini free tier ≈ 20 requests/day. One live run uses ~4–8 Gemini calls. Use `--stub` for dry runs.

3. **Optional — reuse captured evidence** (no API calls):

   ```powershell
   Get-Content outputs\8c3ff70a-b7e4-48a1-9065-7a5157707ffb\itinerary.md
   Get-Content outputs\8c3ff70a-b7e4-48a1-9065-7a5157707ffb\trace.md
   ```

---

## The One-Liner (Problem → Solution)

> *"You describe a trip in plain English. Seven specialized AI agents — orchestrated by a supervisor — research destinations, find stays, plan transport, build a budget, compose a day-by-day itinerary, and independently validate the plan. You get a full markdown report plus an audit trail."*

---

## Seven Agents (Name These in the Demo)

| # | Agent | Brain | One-line role |
|---|-------|-------|---------------|
| 1 | **Request Parser** | Groq | Understands your request → structured constraints |
| 2 | **Destination Research** | Groq | POIs, food, temples, crowd tips |
| 3 | **Accommodation** | Groq | Neighborhoods and lodging tiers |
| 4 | **Transport** | Groq | Inter-city legs, airport transfers, local transit |
| 5 | **Budget** | Gemini | Independent cost reconciliation |
| 6 | **Itinerary Composer** | Groq | Day-by-day schedule |
| 7 | **Validator** | Gemini | Checks plan vs original request (two-brain QA) |

**Two brains:** Groq *plans*; Gemini *checks money and compliance* — so one model doesn't grade its own homework.

---

## Live Demo Script

### Step 1 — Stub dry run (~5 sec, no API)

Shows pipeline shape without burning quota:

```powershell
plan --stub "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds."
```

Point out sections: Overview → Day-by-day → Stay → Transport → Budget → Validation → **How this plan was built**.

### Step 2 — Live run (~60–90 sec)

```powershell
plan "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds."
```

While it runs, explain phases on screen:

1. **Parse** — extract duration, cities, budget, preferences  
2. **Gather** (parallel) — research + accommodation + transport  
3. **Budget** — Gemini totals costs  
4. **Compose** — day-by-day outline  
5. **Validate** — Gemini + deterministic rules; retry if needed  

Output saves to `outputs/{run_id}/` (itinerary.md, trace.md, state.json).

### Step 3 — Show explainability

Open the trace file from stderr (`Saved to outputs/.../`):

- Per-agent timing table  
- Groq vs Gemini attribution  
- No API keys in trace (redacted if present)

### Step 4 — Validation sign-off

Scroll to **Validation** section:

- PASS/FAIL status  
- Rule checks (duration, destinations, budget, preferences, constraints)  
- Budget total vs ceiling — overages are never hidden  

---

## Backup: Pre-Captured Evidence

If live APIs fail or quota is exhausted, use the evidence manifest:

| Fixture | Run ID | Validation |
|---------|--------|------------|
| FIX-JP (Japan) | `8c3ff70a-b7e4-48a1-9065-7a5157707ffb` | pass |
| FIX-IN (India/INR) | `fdbf1948-9079-4f3b-a97a-8dd9e1205e91` | pass |

```powershell
Get-Content outputs\evidence_manifest.json
code outputs\8c3ff70a-b7e4-48a1-9065-7a5157707ffb\itinerary.md
```

---

## India / INR Variant (Optional)

```powershell
plan "Plan a 4-day trip to Rajasthan. Jaipur + Udaipur. 60000 INR budget. Love forts and street food, hate crowds."
```

Shows same pipeline, INR currency end-to-end.

---

## Common Questions

| Question | Answer |
|----------|--------|
| Is data live from booking sites? | No — LLM knowledge only; all costs labeled **estimated**. |
| What if validation fails? | Retry loop adjusts budget/itinerary; final output still renders with issues listed. |
| Can agents talk to each other? | No — only the orchestrator calls agents (shared `TripState`). |
| Where are secrets? | `.env` only; gitignored; never in trace exports. |

---

## Security Reminders for Presenters

- Do **not** screen-share `.env` or API keys  
- Do **not** commit `outputs/` (gitignored — local evidence only)  
- Use `--stub` when rehearsing  
- Run `git status` before push — `.env` must never appear staged  
