import os
import time
from datetime import datetime

# Set how often you want the test to run (in seconds)
# 120 seconds = 2 minutes. (Don't make it faster than 60s or Google will block you!)
INTERVAL = 120 

print(f"[*] Starting local Dev Scheduler...")
print(f"[*] Audits will automatically run every {INTERVAL} seconds.")
print("[*] Press Ctrl+C to stop.\n")

while True:
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"[{current_time}] Triggering automated audit sequence...")
    
    # This tells Windows to run your custom Django command
    os.system("python manage.py run_audits")
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sequence complete. Sleeping for {INTERVAL} seconds...\n")
    print("-" * 50)
    
    time.sleep(INTERVAL)