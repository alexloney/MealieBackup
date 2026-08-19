# MealieBackup

Automated backup script for Mealie that pushes backups to GitHub.

## Features

- Connects to your Mealie instance via API
- Creates and downloads backup files
- Automatically commits and pushes backups to a GitHub repository
- Uses environment variables for secure credential management
- Docker container with cron scheduling for automated backups
- Automatic retry logic with exponential backoff for network resilience
- ZIP file validation to ensure backup integrity
- Handles "no changes" case when backup is identical to previous version
- Robust error handling with detailed logging

## Setup

### Option 1: Run Locally

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure your `.env` file with the following variables:
   - `MEALIE_URL` - Your Mealie instance URL
   - `API_TOKEN` - Mealie API token (create in Mealie settings)
   - `GITHUB_BACKUP_REPO` - GitHub repository URL for storing backups
   - `GITHUB_USERNAME` - Your GitHub username
   - `GITHUB_PAT` - GitHub Personal Access Token with repo access

3. Ensure Git is installed and available in your PATH

4. Run the backup script:
   ```bash
   python backup.py
   ```

### Option 2: Run with Docker

1. Copy `.env.example` to `.env` and configure your credentials:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Mealie and GitHub credentials

3. Build and start the container:
   ```bash
   docker-compose up -d
   ```

4. View logs:
   ```bash
   docker-compose logs -f
   ```

5. Stop the container:
   ```bash
   docker-compose down
   ```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MEALIE_URL` | Your Mealie instance URL | `https://mealie.example.com` |
| `API_TOKEN` | Mealie API token | Generate in Mealie user settings |
| `GITHUB_BACKUP_REPO` | GitHub repository URL | `https://github.com/user/repo.git` |
| `GITHUB_USERNAME` | GitHub username | `your_username` |
| `GITHUB_PAT` | GitHub Personal Access Token | Generate at github.com/settings/tokens |
| `CRON_SCHEDULE` | Backup schedule (cron format) | `0 2 * * *` (daily at 2 AM) |
| `RUN_ON_STARTUP` | Run backup when container starts | `true` or `false` |
| `TZ` | Timezone for cron schedule | `America/New_York`, `Europe/London`, `UTC` |

### Cron Schedule Examples

- `0 2 * * *` - Daily at 2 AM
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Weekly on Sunday at midnight
- `*/30 * * * *` - Every 30 minutes (for testing)

## How It Works

The script will:
1. Connect to your Mealie instance
2. Create a new backup via API
3. Download the backup as `mealie_backup.zip`
4. Clone/update the GitHub repository
5. Commit and push the backup to GitHub (overwriting previous backup)
6. Delete the backup from Mealie to save space
7. Git history preserves all previous backups

## Automation

### Docker (Recommended)
Use the provided Docker container with cron scheduling for automated backups.

### Manual Scheduling
You can also automate this script using:
- **Windows Task Scheduler** - Schedule regular backups
- **Cron** (Linux/macOS) - Add to crontab for scheduled execution
- **GitHub Actions** - Run on a schedule in the cloud

## Directory Structure

```
.
├── backup.py              # Main backup script
├── .env                   # Environment variables (not committed)
├── .env.example          # Example environment variables
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker container definition
├── docker-compose.yml    # Docker Compose configuration
├── entrypoint.sh         # Docker entrypoint script
├── backups/              # Local backup files (created automatically)
└── repo/                 # Cloned GitHub repository (created automatically)
```

## Security Notes

- Never commit your `.env` file to version control
- Use a GitHub Personal Access Token with minimal required permissions (repo access only)
- Consider using a dedicated Mealie API token for backups
- The Docker container uses environment variables passed through docker-compose