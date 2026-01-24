"""
Automation script to run all data processing tasks sequentially.

This script executes the following tasks in order:
1. Fetch bank data
2. Export transactions to Google Sheets
3. Send Telegram notifications about new transactions
"""
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set Django settings module environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coin_counter.settings")


def run_command(cmd):
    """
    Execute a command and print its output.

    Args:
        cmd (list): Command and arguments to execute.
    """
    print(f"\n==> Running: {' '.join(cmd)}\n")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    print(result.stdout)
    if result.stderr:
        print("WARNING: Error output:\n", result.stderr)


if __name__ == "__main__":
    # 1. Fetch bank data
    run_command([sys.executable, "manage.py", "fetch_bank_data"])

    # 2. Export transactions to Google Sheets
    run_command([sys.executable, "manage.py", "export_transactions_to_sheets"])

    # 3. Send Telegram notifications about new transactions
    run_command([sys.executable, "manage.py", "notify_about_new_transactions"])
