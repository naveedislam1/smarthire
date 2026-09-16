# Build context is the REPO ROOT (needs libs/smarthire_common).
# Build: docker build -f services/gateway/Dockerfile -t smarthire-gateway .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /repo
COPY pyproject.toml uv.lock* ./
COPY libs ./libs
COPY services/gateway ./services/gateway

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package smarthire-gateway --no-dev

WORKDIR /repo/services/gateway
EXPOSE 8080
CMD ["uv", "run", "--no-sync", "--package", "smarthire-gateway", \
     "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
