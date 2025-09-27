FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Create data directory (will be mounted as volume)
RUN mkdir -p /app/data

# Copy requirements first for better layer caching
COPY requirements-docker.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy application code
COPY bookwyrms/ ./bookwyrms/
COPY static/ ./static/
COPY main.py .

# Note: Running as root for simplified volume permissions
# In production, consider using proper user mapping or init containers

# Expose the web server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health', timeout=5)" || exit 1

# Default command: start the web server
CMD ["python", "main.py", "web", "--host", "0.0.0.0", "--port", "8000"]