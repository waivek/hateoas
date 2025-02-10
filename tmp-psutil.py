
import psutil
import time
import sys

from tmp_idle_process import lock_file_path

with open(lock_file_path, "r") as lock_file:
    pid = int(lock_file.read())

exists = psutil.pid_exists(pid)
if not exists:
    print("Process does not exist")
    sys.exit(0)
process = psutil.Process(pid)

status = process.status()
print(process)
print("Exists: ", exists)
