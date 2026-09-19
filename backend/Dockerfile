FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install --with-deps chromium

# Copy application code
COPY . .

# Cloud Run sets PORT env var (default 8080)
ENV PORT=8080

# Expose port
EXPOSE ${PORT}

# Run API server — Cloud Run requires listening on $PORT
# In unified mode (default), the worker runs as a background task inside this process
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
