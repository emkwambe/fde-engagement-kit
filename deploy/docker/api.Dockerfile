# syntax=docker/dockerfile:1.7
# API image: FastAPI + LangGraph agent + the agent console at "/" (D-12, NFR-11, NFR-12).
# The same image also runs the one-shot jobs: migrate, seed, ingest, eval (different command, same code).
#
# Build (repo root):  docker build -f deploy/docker/api.Dockerfile --build-arg BUILD_SHA=$(git rev-parse --short HEAD) -t fde-api:local .
#
# Why multi-stage: the build stage has uv and the download cache; the runtime stage gets only the finished
# virtual environment and our source. Smaller image, fewer packages for a scanner to flag, no build tools at runtime.
# Why pinned by digest: a tag like "3.12-slim" moves; a digest is one exact image, so builds are repeatable (NFR-12).

ARG PYTHON_IMAGE=python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c

FROM ghcr.io/astral-sh/uv:0.8.1@sha256:5754244acb75f7c7dcc40f6bac02101fe3d0cae6d536e776de62e392a4753f3a AS uv

# ---------------------------------------------------------------- build: dependencies only (cached until uv.lock changes)
FROM ${PYTHON_IMAGE} AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY pyproject.toml uv.lock ./
# --frozen: use uv.lock exactly (fail if it is out of date); --no-dev: no pytest/ruff/mypy in production.
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE} AS runtime
ARG BUILD_SHA=dev
LABEL org.opencontainers.image.title="fde-api" \
      org.opencontainers.image.source="https://github.com/emkwambe/fde-engagement-kit" \
      org.opencontainers.image.revision="${BUILD_SHA}"
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BUILD_SHA=${BUILD_SHA} \
    HOME=/tmp \
    FAKE_LLM=1 \
    OTEL_TRACES_EXPORTER=console
# A fixed, non-root user (uid 10001). Kubernetes can then enforce runAsNonRoot without guessing the uid.
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY core/ core/
COPY engagements/ engagements/
COPY services/mock-erp/openapi.yaml services/mock-erp/openapi.yaml
COPY deploy/sql/ deploy/sql/
COPY ui/ ui/
# The seed job writes CSV exports under engagements/<name>/data/tables; everything else stays root-owned (read-only).
RUN find engagements -type d -path '*/data/tables' -exec chown app:app {} +
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
CMD ["uvicorn", "core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
