# Build context = REPO ROOT. docker build -f services/candidates/Dockerfile -t smarthire-candidates .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /repo
COPY pyproject.toml uv.lock* ./
COPY libs ./libs
COPY services/candidates ./services/candidates

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package smarthire-candidates --no-dev

WORKDIR /repo/services/candidates
EXPOSE 8002
CMD ["uv", "run", "--no-sync", "--package", "smarthire-candidates", \
     "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
