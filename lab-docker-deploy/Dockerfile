# =============================================================================
#  Dockerfile - Multi-Stage Build for the Inventory API
# =============================================================================
#
#  Multi-stage builds produce SMALLER images:
#    Stage 1 (builder) - installs all dependencies (including build tools)
#    Stage 2 (runtime) - copies only the installed packages + app code
#
#  Build:  docker build -t inventory-api .
#  Run:    docker run -p 8080:8080 inventory-api
#  Test:   curl http://localhost:8080/health
#
# =============================================================================

# ---------------------------------------------------------------------------
#  Stage 1: Builder - install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy dependency file first (Docker layer caching)
COPY requirements.txt .

# Install dependencies into a prefix so we can copy them cleanly
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
#  Stage 2: Runtime - lean production image
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Copy installed Python packages from the builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/

# Expose the API port
EXPOSE 8080

# Health check - Docker (and orchestrators) will monitor this
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1

# Run the API
CMD ["python", "-m", "app.api"]
