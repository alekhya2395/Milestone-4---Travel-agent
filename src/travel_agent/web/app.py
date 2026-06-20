from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from travel_agent.web.paths import static_dir

logger = logging.getLogger(__name__)

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


@app.get("/health")
def health_alt() -> dict:
    return {"status": "ok", "service": "tripzy"}


@app.post("/api/plan")
def plan_trip(body: PlanRequest) -> dict:
    from travel_agent.web.service import execute_plan, state_to_api_payload

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
        logger.exception("plan_trip failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return state_to_api_payload(state)


def _resolve_static_dir() -> Path | None:
    path = static_dir()
    return path if path.is_dir() else None


@app.on_event("startup")
def on_startup() -> None:
    static = _resolve_static_dir()
    logger.info("Tripzy starting — static dir: %s", static or "not found")


_static = _resolve_static_dir()
if _static is not None:
    app.mount("/", StaticFiles(directory=str(_static), html=True), name="static")
else:

    @app.get("/")
    def root_fallback() -> dict:
        return JSONResponse(
            {"status": "ok", "service": "tripzy", "message": "API running; static UI not bundled"}
        )
