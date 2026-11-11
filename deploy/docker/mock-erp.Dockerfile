# syntax=docker/dockerfile:1.7
# Mock ERP image: the simulated "legacy system" (D-10, D-12). Deliberately independent of core/ at RUN time (it is
# someone else's system), so it gets its own tiny virtual environment with only what it imports. Versions match uv.lock.
#
# Build (repo root):  docker build -f deploy/docker/mock-erp.Dockerfile --build-arg BUILD_SHA=$(git rev-parse --short HEAD) -t fde-mock-erp:local .
#
# Its shipment export is generated at BUILD time by the project's own seed code (fixed seed number, so the data is
# byte-identical to what the ETL loads). Baking it in means the same image works on Compose, kind and Cloud Run,
# where there is no shared disk to hand a CSV over.

ARG PYTHON_IMAGE=python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c

FROM ${PYTHON_IMAGE} AS build
RUN python -m venv /venv && /venv/bin/pip install --no-cache-dir \
      fastapi==0.162.3 starlette==1.10.0 pydantic==2.14.3 pydantic-core==2.50.4 uvicorn==0.54.0 pyyaml==6.0.3

# ---------------------------------------------------------------- data: run the engagement's seed once, keep only its output
# The generator is engagement-owned and standard-library only (Sprint 01, kit-generic), so plain python runs it.
FROM ${PYTHON_IMAGE} AS data
COPY engagements/demo-logistics/extensions/seed.py /src/seed.py
RUN python /src/seed.py /src/tables

# ---------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE} AS runtime
ARG BUILD_SHA=dev
LABEL org.opencontainers.image.title="fde-mock-erp" org.opencontainers.image.revision="${BUILD_SHA}"
ENV PATH=/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 BUILD_SHA=${BUILD_SHA} HOME=/tmp \
    ERP_SHIPMENTS_CSV=/data/tables/shipments.csv ERP_TICKETS_FILE=/tmp/erp/tickets.json
# Security updates for the OS packages of the base image. Found by trivy in CI (Sprint 01): the pinned base had
# 7 CRITICAL CVEs with fixes already published (libssl3, gnutls, perl). Pinning by digest freezes these too, so we upgrade.
RUN apt-get update && apt-get -y upgrade --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /venv /venv
COPY --from=data /src/tables/shipments.csv /data/tables/shipments.csv
# Same folder depth as in the repo (app.py looks two levels up for its defaults).
WORKDIR /srv/services/mock-erp
COPY services/mock-erp/app.py services/mock-erp/openapi.yaml ./
USER 10001:10001
EXPOSE 8100
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=3)"]
CMD ["uvicorn", "app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8100"]
