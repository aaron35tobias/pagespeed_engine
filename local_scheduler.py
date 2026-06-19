import os
import time
from datetime import datetime, timezone, timedelta

# Daily audit time (UTC)
SCHEDULE_HOUR_UTC   = 6
SCHEDULE_MINUTE_UTC = 0


def seconds_until_next_run():
    """Return seconds to sleep until the next 06:00 AM UTC."""
    now    = datetime.now(timezone.utc)
    target = now.replace(hour=SCHEDULE_HOUR_UTC, minute=SCHEDULE_MINUTE_UTC, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return (target - now).total_seconds(), target


def run_audits():
    """Invoke the Django management command that scans all active websites."""
    os.system("python manage.py run_audits")


if __name__ == "__main__":
    print("[*] PageSpeed Wisoft — Daily Scheduler")
    print(f"[*] Runs every day at {SCHEDULE_HOUR_UTC:02d}:{SCHEDULE_MINUTE_UTC:02d} UTC")
    print("[*] Press Ctrl+C to stop.\n")

    while True:
        wait_seconds, target = seconds_until_next_run()
        print(f"[*] Next audit  → {target.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"[*] Sleeping    → {wait_seconds / 3600:.2f} h ({wait_seconds / 60:.0f} min)\n")
    print("-" * 50)

    time.sleep(wait_seconds)

    run_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n[{run_time}] Triggering daily audit sequence...")

    # Runs the Django management command which scans all active websites
    os.system("python manage.py run_audits")

    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}] Daily audit complete.")
    print("-" * 50 + "\n")

    # 60s buffer so the loop doesn't re-trigger immediately at 06:00:01
    time.sleep(60)