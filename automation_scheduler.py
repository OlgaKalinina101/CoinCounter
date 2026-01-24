"""
Scheduled automation runner using APScheduler.

This script runs the automation tasks (run_all.py) on a schedule:
- Daily at 12:00 (noon)
- Daily at 22:00 (10 PM)

The timezone is set to Europe/Moscow. Adjust as needed for your deployment.
"""
import logging
import os
import subprocess
import sys

import django
from apscheduler.schedulers.blocking import BlockingScheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coin_counter.settings")
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_automation():
    """
    Execute the automation script (run_all.py) with error handling.

    Runs all data processing tasks with a 5-minute timeout.
    """
    logger.info("Starting automation tasks...")

    script_path = os.path.join(BASE_DIR, "run_all.py")
    cmd = [sys.executable, script_path]

    try:
        logger.info(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=BASE_DIR,
            timeout=300  # 5 minutes timeout
        )
        
        if result.stdout:
            logger.info(result.stdout)
        
        if result.stderr:
            logger.warning(f"Error output:\n{result.stderr}")
        
        if result.returncode != 0:
            logger.error(f"Command failed with exit code: {result.returncode}")
        else:
            logger.info("Automation completed successfully!")
            
    except subprocess.TimeoutExpired:
        logger.error("Command exceeded 5-minute timeout")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")


if __name__ == "__main__":
    # Configure timezone for your deployment (default: Europe/Moscow)
    scheduler = BlockingScheduler(timezone="Europe/Moscow")
    
    # Schedule jobs: 12:00 and 22:00 daily
    scheduler.add_job(run_automation, 'cron', hour=12, minute=0)
    scheduler.add_job(run_automation, 'cron', hour=22, minute=0)
    
    logger.info("Scheduler started. Waiting for scheduled execution times...")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")