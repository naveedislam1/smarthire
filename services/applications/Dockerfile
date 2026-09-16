# Build context = REPO ROOT. docker build -f services/applications/Dockerfile -t smarthire-applications .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /repo
COPY pyproject.toml uv.lock* ./
COPY libs ./libs
COPY services/applications ./services/applications

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package smarthire-applications --no-dev

WORKDIR /repo/services/applications
EXPOSE 8004
CMD ["uv", "run", "--no-sync", "--package", "smarthire-applications", \
     "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
