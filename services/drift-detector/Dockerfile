FROM python:3.13-slim

WORKDIR /app

# Install build deps (needed for some native packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first for better layer caching
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application source
COPY app/ ./app/

# Run as non-root
RUN useradd -m -u 1001 detector
USER detector

ENTRYPOINT ["python", "-m", "app.main"]
