import time
from datetime import datetime
import tzlocal

while True:
    now = datetime.now(tzlocal.get_localzone())
    print(f"Time = {now.strftime('%Y-%m-%d %H:%M:%S %Z')}", flush=True)
    time.sleep(1)
