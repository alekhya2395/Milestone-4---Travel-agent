FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

COPY web ./web

EXPOSE 8000

CMD ["sh", "-c", "uvicorn travel_agent.web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
