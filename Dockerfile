# --- Build stage ---
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir build \
    && python -m build --wheel --outdir /build/dist

# --- Runtime stage ---
FROM python:3.12-slim

WORKDIR /app

# Install the built wheel
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Default: run the API server
CMD ["uvicorn", "context_graph.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
