#!/usr/bin/env python3
"""
Mealie Backup Script
This script connects to a Mealie instance, generates a backup, and pushes it to GitHub.
"""

import os
import sys
import time
import zipfile
import requests
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables
load_dotenv()

# Configuration from environment
MEALIE_URL = os.getenv("MEALIE_URL")
API_TOKEN = os.getenv("API_TOKEN")
GITHUB_BACKUP_REPO = os.getenv("GITHUB_BACKUP_REPO")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_PAT = os.getenv("GITHUB_PAT")

# Validate required environment variables
if not all([MEALIE_URL, API_TOKEN, GITHUB_BACKUP_REPO, GITHUB_USERNAME, GITHUB_PAT]):
    print("Error: Missing required environment variables in .env file")
    sys.exit(1)

# Remove trailing slash from Mealie URL if present
MEALIE_URL = MEALIE_URL.rstrip("/")

# Directories
WORK_DIR = Path(__file__).parent
BACKUP_DIR = WORK_DIR / "backups"
REPO_DIR = WORK_DIR / "repo"

# Request timeout in seconds
REQUEST_TIMEOUT = 30


def get_session_with_retries():
    """Create a requests session with retry logic."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,  # Total number of retries
        backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
        allowed_methods=["HEAD", "GET", "POST", "DELETE"]  # Methods to retry
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def create_mealie_backup():
    """Create a backup in Mealie and return the backup filename."""
    print(f"Connecting to Mealie at {MEALIE_URL}...")
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    session = get_session_with_retries()
    
    # Create backup
    print("Requesting backup creation...")
    create_url = f"{MEALIE_URL}/api/admin/backups"
    
    try:
        response = session.post(create_url, headers=headers, json={}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        print("Backup created successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error creating backup: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
        sys.exit(1)
    
    # Wait for backup to be processed
    print("Waiting for backup to be processed...")
    time.sleep(5)
    
    # Get list of backups to find the newest one
    print("Retrieving backup list...")
    list_url = f"{MEALIE_URL}/api/admin/backups"
    
    try:
        response = session.get(list_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        backups = response.json()
        
        if not backups or "imports" not in backups:
            print("Error: No backups found")
            sys.exit(1)
        
        # Get the most recent backup
        latest_backup = sorted(backups["imports"], key=lambda x: x.get("date", ""), reverse=True)[0]
        backup_filename = latest_backup["name"]
        print(f"Latest backup: {backup_filename}")
        
        return backup_filename
        
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving backup list: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
        sys.exit(1)


def download_backup(backup_filename):
    """Download the backup file from Mealie and rename it to mealie_backup.zip."""
    print(f"Downloading backup: {backup_filename}...")
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }
    
    session = get_session_with_retries()
    
    try:
        # Step 1: Get the file token
        print("Getting file token...")
        token_url = f"{MEALIE_URL}/api/admin/backups/{backup_filename}"
        token_response = session.get(token_url, headers=headers, timeout=REQUEST_TIMEOUT)
        token_response.raise_for_status()
        
        file_token = token_response.json().get("fileToken")
        
        if not file_token:
            print(f"Error: No fileToken in response")
            sys.exit(1)
        
        # Step 2: Download the actual file using the utils/download endpoint
        print("Downloading backup file...")
        download_url = f"{MEALIE_URL}/api/utils/download?token={file_token}"
        response = session.get(download_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Ensure backup directory exists
        BACKUP_DIR.mkdir(exist_ok=True)
        
        # Save the backup file with standardized name
        local_backup_path = BACKUP_DIR / "mealie_backup.zip"
        
        with open(local_backup_path, "wb") as f:
            f.write(response.content)
        
        # Validate the ZIP file
        print("Validating ZIP file...")
        if not zipfile.is_zipfile(local_backup_path):
            print("Error: Downloaded file is not a valid ZIP file")
            sys.exit(1)
        
        print(f"✓ Backup downloaded and validated: {local_backup_path}")
        return local_backup_path, backup_filename
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading backup: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
        sys.exit(1)
    except zipfile.BadZipFile as e:
        print(f"Error: Invalid ZIP file - {e}")
        sys.exit(1)


def push_to_github(backup_file):
    """Push the backup file to GitHub repository, overwriting previous backup."""
    print(f"Preparing to push to GitHub repository...")
    
    # Create authenticated repo URL
    auth_repo_url = GITHUB_BACKUP_REPO.replace("https://", f"https://{GITHUB_USERNAME}:{GITHUB_PAT}@")
    
    try:
        # Clone or update repository
        if REPO_DIR.exists():
            print("Repository directory exists, resetting to remote state...")
            # Fetch latest changes
            subprocess.run(["git", "-C", str(REPO_DIR), "fetch", "origin"], check=True, capture_output=True)
            # Reset to remote state (discard any local changes)
            subprocess.run(["git", "-C", str(REPO_DIR), "reset", "--hard", "origin/HEAD"], check=True, capture_output=True)
            # Pull latest changes
            subprocess.run(["git", "-C", str(REPO_DIR), "pull"], check=True, capture_output=True)
        else:
            print("Cloning repository...")
            subprocess.run(["git", "clone", auth_repo_url, str(REPO_DIR)], check=True, capture_output=True)
        
        # Copy backup file to repo (overwriting previous)
        dest_file = REPO_DIR / "mealie_backup.zip"
        print(f"Copying backup to repository (overwriting previous)...")
        shutil.copy2(backup_file, dest_file)
        
        # Git operations
        print("Adding file to git...")
        subprocess.run(["git", "-C", str(REPO_DIR), "add", "mealie_backup.zip"], check=True, capture_output=True)
        
        # Create commit message with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Backup: mealie_backup.zip - {timestamp}"
        
        print(f"Committing changes...")
        commit_result = subprocess.run(
            ["git", "-C", str(REPO_DIR), "commit", "-m", commit_message],
            capture_output=True,
            text=True
        )
        
        # Check if commit succeeded or if there were no changes
        if commit_result.returncode == 0:
            print("Changes committed successfully.")
            print("Pushing to GitHub...")
            subprocess.run(["git", "-C", str(REPO_DIR), "push"], check=True, capture_output=True)
            print(f"✓ Successfully pushed backup to GitHub!")
        elif "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
            print("No changes detected - backup file is identical to previous version.")
            print("✓ Backup verified (no changes needed).")
        else:
            # Actual error occurred
            print(f"Git commit failed with exit code {commit_result.returncode}")
            print(f"stdout: {commit_result.stdout}")
            print(f"stderr: {commit_result.stderr}")
            raise subprocess.CalledProcessError(commit_result.returncode, commit_result.args)
        
    except subprocess.CalledProcessError as e:
        print(f"Error with git operation: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout.decode()}")
        if e.stderr:
            print(f"stderr: {e.stderr.decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def delete_mealie_backup(backup_filename):
    """Delete the backup from Mealie instance to save space."""
    print(f"Deleting backup from Mealie: {backup_filename}...")
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }
    
    session = get_session_with_retries()
    delete_url = f"{MEALIE_URL}/api/admin/backups/{backup_filename}"
    
    try:
        response = session.delete(delete_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        print(f"✓ Backup deleted from Mealie successfully!")
        
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not delete backup from Mealie: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
        print("Continuing anyway as backup is already saved to GitHub...")


def main():
    """Main execution function."""
    print("=" * 60)
    print("Mealie Backup Script")
    print("=" * 60)
    
    # Create backup in Mealie
    backup_filename = create_mealie_backup()
    
    # Download the backup
    local_backup, original_filename = download_backup(backup_filename)
    
    # Push to GitHub
    push_to_github(local_backup)
    
    # Delete backup from Mealie
    delete_mealie_backup(original_filename)
    
    print("=" * 60)
    print("Backup completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
