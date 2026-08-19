FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    cron \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configure git (required for commits)
RUN git config --global user.email "backup@mealie.local" && \
    git config --global user.name "Mealie Backup"

# Set working directory
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backup.py .
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Set environment variables with defaults
ENV CRON_SCHEDULE="0 2 * * *"
ENV RUN_ON_STARTUP="false"
ENV TZ="UTC"

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
