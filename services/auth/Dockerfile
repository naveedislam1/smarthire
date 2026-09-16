# Build context is the REPO ROOT (needs libs/smarthire_common from the workspace).
# Build: docker build -f services/auth/Dockerfile -t smarthire-auth .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /repo
COPY pyproject.toml uv.lock* ./
COPY libs ./libs
COPY services/auth ./services/auth

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package smarthire-auth --no-dev

WORKDIR /repo/services/auth
EXPOSE 8001
CMD ["uv", "run", "--no-sync", "--package", "smarthire-auth", \
     "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
