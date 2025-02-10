import os
import signal
import time
import psutil

# Get the current process ID
pid = os.getpid()

# Send SIGSTOP to pause the process
print("BEFORE: Process is paused for 5 seconds")
def handler(signum, frame):
    print("Signal handler called with signal", signum)
signal.signal(signal.SIGALRM, handler)
while True:
    signal.alarm(1)
    signal.pause()
print("AFTER: Process is paused for 5 seconds")

process = psutil.Process(pid)
print("Process status: ", process.status())
# Wait for 1 minute (process is paused, so the delay occurs only after SIGCONT)
time.sleep(5)

# Send SIGCONT to resume the process
os.kill(pid, signal.SIGCONT)

print("Process resumed after 5 seconds")

