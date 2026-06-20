from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from travel_agent.web.service import execute_plan, state_to_api_payload, static_dir

app = FastAPI(title="Tripzy — Travel Multi-Agent Planner", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlanRequest(BaseModel):
    request: str = Field(min_length=1, max_length=4000)
    stub: bool = False


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "tripzy"}


@app.post("/api/plan")
def plan_trip(body: PlanRequest) -> dict:
    request = body.request.strip()
    if not request:
        raise HTTPException(status_code=400, detail="Request cannot be empty")
    try:
        state = execute_plan(request, stub=body.stub, save=True)
    except SystemExit as exc:
        raise HTTPException(
            status_code=503,
            detail="API keys missing. Use stub mode or configure .env",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return state_to_api_payload(state)


_static = static_dir()
if _static.is_dir():
    app.mount("/", StaticFiles(directory=str(_static), html=True), name="static")
