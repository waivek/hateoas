#!/usr/bin/env /home/vivek/pyscripts/.direnv/python-3.10.12/bin/python
from datetime import datetime, timedelta
from tzlocal import get_localzone
import time

def main():
    while True:
        now = datetime.now(get_localzone())
        date_string = now.strftime("%Y-%m-%d %H:%M:%S")
        print(date_string, flush=True)
        time.sleep(1)

if __name__ == "__main__":
    main()
