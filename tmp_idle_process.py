
import os
import psutil
import signal
import time

lock_file_path = "/home/vivek/hateoas/tmp/idle-process.lock"
PID = os.getpid()

def main():

    with open(lock_file_path, "w") as lock_file:
        lock_file.write(str(PID))

    process = psutil.Process(PID)
    while True:
        if os.fork() == 0:
            time.sleep(1)
            process.resume()
            print("[PID={}] Resumed".format(PID))
            os._exit(0)
        process.suspend()


if __name__ == "__main__":
    main()
