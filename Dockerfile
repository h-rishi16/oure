# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .[web]

# Copy the rest of the code
COPY . .

# Expose ports for API (8000) and Dashboard (8501)
EXPOSE 8000
EXPOSE 8501

# Default command (overridden by docker-compose)
CMD ["python", "-m", "oure.cli.main", "--help"]
