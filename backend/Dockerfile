FROM python:3.11-slim AS base

WORKDIR /app

# Install dependencies first (cached layer)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/ app/

# Non-root user for security
RUN adduser --disabled-password --no-create-home appuser
USER appuser

# Railway sets PORT dynamically
ENV PORT=8000
EXPOSE ${PORT}

# Health check for container orchestrators
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/v1/health')" || exit 1

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
