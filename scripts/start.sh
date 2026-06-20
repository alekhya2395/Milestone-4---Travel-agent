#!/usr/bin/env sh
set -e
PORT="${PORT:-8000}"
echo "Starting Tripzy on 0.0.0.0:${PORT}"
exec uvicorn travel_agent.web.app:app --host 0.0.0.0 --port "${PORT}" --proxy-headers --forwarded-allow-ips="*"
