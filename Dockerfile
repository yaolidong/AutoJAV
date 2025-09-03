# AV Metadata Scraper Docker Image
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install system dependencies for Chrome and application
RUN apt-get update && apt-get install -y \
    # Chrome dependencies
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    # Additional utilities
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium instead of Chrome for better ARM compatibility
# Also install Xvfb for virtual display support
RUN apt-get update && \
    apt-get install -y chromium chromium-driver xvfb && \
    rm -rf /var/lib/apt/lists/*

# Create symlinks for compatibility
RUN ln -s /usr/bin/chromium /usr/bin/google-chrome && \
    ln -s /usr/bin/chromedriver /usr/local/bin/chromedriver

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create application user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directories
WORKDIR /app
RUN mkdir -p /app/logs /app/config /app/source /app/target && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . /app/

# Copy and setup entrypoint scripts
COPY --chown=appuser:appuser docker/startup.sh /app/entrypoint.sh
COPY --chown=appuser:appuser docker/startup_with_api.sh /app/entrypoint_api.sh
RUN chmod +x /app/entrypoint.sh /app/entrypoint_api.sh

# Install gosu for proper user switching
RUN apt-get update && apt-get install -y gosu && rm -rf /var/lib/apt/lists/*

# Health check
HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD python /app/docker/healthcheck.py || exit 1

# Environment variables
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    WDM_LOCAL=1 \
    WDM_LOG=false \
    SE_DRIVER_PATH=/usr/bin/chromedriver

# Expose API port
EXPOSE 5001

# Set entrypoint with API
ENTRYPOINT ["/app/docker/startup_with_api.sh"]

# Default command (run API server)
CMD ["python", "src/api_server.py"]