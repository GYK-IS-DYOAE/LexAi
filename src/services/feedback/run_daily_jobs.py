# src/services/feedback/run_daily_jobs.py

from services.feedback.aggregate_daily import run as aggregate_daily
from services.feedback.action_executor import run as action_executor

if __name__ == "__main__":
    print("[*] Running daily feedback aggregation...")
    aggregate_daily()

    print("[*] Executing queued actions...")
    action_executor()
