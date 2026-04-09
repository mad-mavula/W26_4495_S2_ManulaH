FROM python:3.9-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy application code
COPY . .

# Copy attack simulation scripts
COPY scripts/ /app/scripts/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Create data directory for baseline storage
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data && chmod 755 /app/data

USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')" || exit 1

# Run application
CMD ["python", "src/app.py"]
