FROM python:3.11-slim-bookworm AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium + system deps into shared directory
RUN mkdir -p /ms-playwright && \
    python -m playwright install --with-deps chromium && \
    chmod -R 777 /ms-playwright

# Copy application code
COPY . .

# Create a non-root user for security
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid 1001 --create-home appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Cloud Run sets PORT env var (default 8080)
ENV PORT=8080

# Expose port
EXPOSE ${PORT}

# Health check — Cloud Run uses HTTP probes, but this helps local Docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Run API server — Cloud Run requires listening on $PORT
# In unified mode (default), the worker runs as a background task inside this process
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
