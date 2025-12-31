FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY app/ ./app/

# Default port (can be overridden by FASTAPI_PORT env var)
ENV FASTAPI_PORT=8000

# Expose port
EXPOSE 8000

# Run the application using the config settings (reads FASTAPI_PORT)
CMD ["python", "-m", "app.main"]
