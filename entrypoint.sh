#!/bin/bash
set -e

# Mealie Backup - Docker Entrypoint
# This script sets up and runs the backup on a cron schedule

echo "=========================================="
echo "Mealie Backup - Docker Container"
echo "========================================="

# Set timezone
TZ="${TZ:-UTC}"
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
echo $TZ > /etc/timezone
echo "Timezone: $TZ ($(date))"

# Default cron schedule: daily at 2 AM
CRON_SCHEDULE="${CRON_SCHEDULE:-0 2 * * *}"

echo "Cron schedule: $CRON_SCHEDULE"

# Validate required environment variables
REQUIRED_VARS=(
    "MEALIE_URL"
    "API_TOKEN"
    "GITHUB_BACKUP_REPO"
    "GITHUB_USERNAME"
    "GITHUB_PAT"
)

echo "Validating environment variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: Missing required environment variable: $var"
        exit 1
    fi
done
echo "All required environment variables present."

# Create the cron job that runs the backup script
# Export all environment variables to a file that cron can source
echo "Setting up cron job..."

# Create environment file for cron (cron doesn't inherit environment)
printenv | grep -v "no_proxy" > /etc/environment

# Create the cron job
# We need to source the environment and then run the Python script
CRON_CMD="$CRON_SCHEDULE . /etc/environment; cd /app && /usr/local/bin/python backup.py >> /var/log/cron.log 2>&1"
echo "$CRON_CMD" > /etc/cron.d/mealie-backup

# Set proper permissions
chmod 0644 /etc/cron.d/mealie-backup

# Apply cron job
crontab /etc/cron.d/mealie-backup

echo "Cron job installed: $CRON_SCHEDULE"

# Create log file
touch /var/log/cron.log

# Option to run immediately on startup
if [ "$RUN_ON_STARTUP" = "true" ]; then
    echo "=========================================="
    echo "Running initial backup (RUN_ON_STARTUP=true)..."
    echo "=========================================="
    cd /app
    python backup.py
    echo "Initial backup completed."
    echo "=========================================="
fi

# Start cron in foreground
echo "Starting cron daemon..."
echo "Container is ready. Logs will appear below."
echo "=========================================="

# Start cron and tail the log
cron && tail -f /var/log/cron.log
