FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
ENV PIP_DEFAULT_TIMEOUT=120
COPY pyproject.toml ./
COPY guard guard
COPY portal portal
COPY worker worker
COPY runner runner
COPY migrations migrations
COPY alembic.ini ./
COPY infra/security infra/security
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home guard && mkdir -p /data/artifacts && chown -R guard:guard /data
USER 10001:10001
CMD ["uvicorn", "guard.api:app", "--host", "0.0.0.0", "--port", "8000"]
