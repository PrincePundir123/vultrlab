#!/usr/bin/env bash
set -eu
if docker compose version >/dev/null 2>&1; then
    compose=(docker compose)
elif [ -x infra/tools/docker-compose ]; then
    compose=(infra/tools/docker-compose)
else
    echo "Docker Compose is missing; see docs/deployment.md" >&2
    exit 1
fi
case "${1:-status}" in
    start) "${compose[@]}" up -d --no-build ;;
    status) "${compose[@]}" ps ;;
    stop) "${compose[@]}" stop ;;
    *) echo "Use start, status or stop" >&2; exit 2 ;;
esac
