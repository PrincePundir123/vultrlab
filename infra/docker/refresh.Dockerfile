# Development-only refresh after the service dependency image has already built.
FROM skg-service:local
WORKDIR /app
USER root
RUN mkdir -p /data/artifacts && chown 10001:10001 /data/artifacts
COPY guard guard
COPY portal portal
COPY worker worker
COPY runner runner
COPY migrations migrations
COPY infra/security infra/security
COPY tests tests
COPY infra/scripts/integration_acceptance.py acceptance.py
USER 10001:10001
