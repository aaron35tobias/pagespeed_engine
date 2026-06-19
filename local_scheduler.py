import os
import time
from datetime import datetime, timezone, timedelta

# Daily audit schedule: 06:00 AM UTC
SCHEDULE_HOUR_UTC   = 6
SCHEDULE_MINUTE_UTC = 0


def next_run_at():
    """Return the next datetime when the audit should fire (06:00 AM UTC)."""
    now    = datetime.now(timezone.utc)
    target = now.replace(hour=SCHEDULE_HOUR_UTC, minute=SCHEDULE_MINUTE_UTC, second=0, microsecond=0)
    # If we are already past today's 06:00 AM UTC, schedule for tomorrow
    if now >= target:
        target += timedelta(days=1)
    return target


print("[*] PageSpeed Wisoft — Daily Scheduler")
print(f"[*] Audits will run every day at {SCHEDULE_HOUR_UTC:02d}:{SCHEDULE_MINUTE_UTC:02d} UTC")
print("[*] Press Ctrl+C to stop.\n")

while True:
    target       = next_run_at()
    wait_seconds = (target - datetime.now(timezone.utc)).total_seconds()

    print(f"[*] Next audit → {target.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"[*] Sleeping for {wait_seconds / 3600:.2f} hours ({wait_seconds / 60:.0f} min)...\n")
    print("-" * 50)

    # Sleep until the exact trigger time
    time.sleep(wait_seconds)

    run_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n[{run_time}] Triggering daily audit sequence...")

    # Runs the Django management command which scans all active websites
    os.system("python manage.py run_audits")

    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}] Daily audit complete.")
    print("-" * 50 + "\n")

    # 60s buffer so the loop doesn't re-trigger immediately at 06:00:01
    time.sleep(60)