FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8046

# Health check (uses PORT env var with fallback)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8046}/health || exit 1

# Run FastAPI with uvicorn (PORT from env, fallback to 8046)
CMD sh -c "python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8046}"
