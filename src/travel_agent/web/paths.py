from __future__ import annotations

from pathlib import Path


def static_dir() -> Path:
    """Locate web/static in dev (repo root) and production (Docker WORKDIR /app)."""
    candidates = [
        Path.cwd() / "web" / "static",
        Path(__file__).resolve().parents[3] / "web" / "static",
        Path("/app/web/static"),
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return candidates[0]
