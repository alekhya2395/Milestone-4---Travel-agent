# Travel Planning Multi-Agent System

Milestone 4 — multi-agent travel planner with a supervisor orchestrator and seven specialized agents.

**Status:** Phases 0–4 complete · LLM-only data · [Eval checklist](docs/eval.md) signed off

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env    # add GROQ_API_KEY and GEMINI_API_KEY — never commit .env
```

## Run

```powershell
# Live LLM pipeline (~60–90s, uses API quota)
plan "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds."

# Stub mode — no API calls (rehearsal / layout)
plan --stub "Plan a 5-day trip to Japan..."

# Raw JSON instead of markdown
plan --json "..."
```

Each run saves to `outputs/{run_id}/`: `itinerary.md`, `trace.md`, `state.json`.

## Demo

See **[docs/demo.md](docs/demo.md)** for a 5-minute walkthrough script, agent cheat sheet, and backup evidence paths.

Pre-captured live evidence: `outputs/evidence_manifest.json`

## Test

```powershell
pytest tests/ -q                  # full suite (65+ tests, no quota)
pytest tests/test_repo_hygiene.py -q   # security before git push
pytest tests/test_eval_checklist.py -v # verify live evidence artifacts
```

## Security

| Rule | Detail |
|------|--------|
| API keys | `.env` only — listed in `.gitignore` |
| Trace exports | PII + key patterns redacted (`orchestrator/safety.py`) |
| Outputs | `outputs/*` gitignored — local evidence only |
| Live runs | Fail fast if keys missing (`--stub` skips key check) |

Before first `git push`: run `pytest tests/test_repo_hygiene.py` and confirm `.env` is not staged.

## Architecture

- **Brain 1 (Groq):** Parser, Research, Accommodation, Transport, Composer  
- **Brain 2 (Gemini):** Budget, Validator  
- **Orchestrator:** Parallel gather → budget → compose → validate (+ retry loop)

## Docs

| Doc | Purpose |
|-----|---------|
| [problemstatement.md](docs/problemstatement.md) | Product intent |
| [architecture.md](docs/architecture.md) | System design |
| [implementation-plan.md](docs/implementation-plan.md) | Build phases |
| [eval.md](docs/eval.md) | Milestone checklist |
| [demo.md](docs/demo.md) | Demo script |
| [stitch/](stitch/) | Google Stitch UI mockup + design system (`screen.png`, `DESIGN.md`) |
| [edgecases.md](docs/edgecases.md) | Edge cases & fixtures |
