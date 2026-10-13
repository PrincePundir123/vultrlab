FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
RUN pip install --no-cache-dir playwright==1.63.0 pydantic pydantic-settings && playwright install --with-deps chromium && useradd --uid 10001 --create-home browser && chmod -R a+rX /ms-playwright
COPY guard/__init__.py guard/contracts.py guard/config.py guard/
COPY runner runner
USER 10001:10001
CMD ["python", "-m", "runner.main"]
