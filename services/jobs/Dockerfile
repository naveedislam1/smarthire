# Build context = REPO ROOT. docker build -f services/jobs/Dockerfile -t smarthire-jobs .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /repo
COPY pyproject.toml uv.lock* ./
COPY libs ./libs
COPY services/jobs ./services/jobs

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package smarthire-jobs --no-dev

WORKDIR /repo/services/jobs
EXPOSE 8003
# API by default; override the command to run the Temporal worker:
#   command: uv run --no-sync --package smarthire-jobs python -m app.worker
CMD ["uv", "run", "--no-sync", "--package", "smarthire-jobs", \
     "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
