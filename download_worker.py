
# reloads if file changes, this is done by simply exiting when the file changes and `crontab` keeps starting it
# listens for interuption signals and cleans up

from dbutils import Connection
import signal
import os
import hashlib
from waivek import ic
from waivek import ib, rel2abs
from waivek import Code
import sys
from types import FrameType
import time
from download_queue import portionurl_id_queue_pop
from portionurl_to_download_path import portionurl_to_download_path
import psutil
from download_portionurl import download_portionurl
from operator import mod

def log(message: str, *args):
    prefix = Code.LIGHTBLACK_EX + f"[download_worker.py] [PID={os.getpid()}]"
    formatted_message = message % args
    output = " ".join([prefix, formatted_message])
    print(output, flush=True)

def get_self_hash() -> str:
    with open(__file__, "r") as f:
        contents = f.read()

    file_hash = hashlib.md5(contents.encode()).hexdigest()
    return file_hash

def downloaded(portionurl_id):
    download_path = portionurl_to_download_path(portionurl_id)
    return os.path.exists(download_path)

def get_lock_path(portionurl_id):
    download_path = portionurl_to_download_path(portionurl_id)
    lock_path = f"{download_path}.lock"
    return lock_path

def lock_acquire(portionurl_id):
    lock_path = get_lock_path(portionurl_id)
    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))
    log("Acquired lock for portionurl_id: %s", portionurl_id)

def lock_release(portionurl_id):
    lock_path = get_lock_path(portionurl_id)
    os.remove(lock_path)
    log("Released lock for portionurl_id: %s", portionurl_id)

def lock_exists(portionurl_id):
    lock_path = get_lock_path(portionurl_id)
    return os.path.exists(lock_path)

def lock_is_stale(portionurl_id):
    lock_path = get_lock_path(portionurl_id)
    with open(lock_path, "r") as f:
        pid = int(f.read())
    pid_exists = psutil.pid_exists(pid)
    if pid_exists:
        return False
    else:
        return True

def get_portionurl_id():
    global connection
    cursor = connection.execute("SELECT id FROM portionurls;")
    portionurl_ids = [ id for id, in cursor.fetchall() ]

    # filter out downloaded portionurls
    portionurl_ids = [ id for id in portionurl_ids if not downloaded(id) ]

    # remove stale locks
    for portionurl_id in portionurl_ids:
        if lock_exists(portionurl_id) and lock_is_stale(portionurl_id):
            log("Removing stale lock for portionurl_id: %s", portionurl_id)
            lock_release(portionurl_id)

    # select a portionurl_id that is not locked
    for portionurl_id in portionurl_ids:
        if not lock_exists(portionurl_id):
            return portionurl_id

    return None

def get_global_lock_path():
    if len(sys.argv) > 1 and sys.argv[1] in [ "red", "blue", "green", "yellow" ]:
        color = sys.argv[1]
        return f"/tmp/download_worker_{color}.lock"
    return f"/tmp/download_worker_{os.getpid()}.lock"

def global_lock_exists():

    lock_path = get_global_lock_path()
    return os.path.exists(lock_path)

def release_stale_global_colored_lock():
    if len(sys.argv) != 2:
        return
    if sys.argv[1] not in [ "red", "blue", "green", "yellow" ]:
        return
    lock_path = get_global_lock_path()
    if not os.path.exists(lock_path):
        return
    pid = int(open(lock_path, "r").read())
    if psutil.pid_exists(pid):
        return
    os.remove(lock_path)
    log("Released stale global lock: %s (%s)", pid, lock_path)

def global_lock_acquire():
    lock_path = get_global_lock_path()
    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))
    log("Acquired global lock for PID: %s (%s)", os.getpid(), lock_path)

def global_lock_release():
    lock_path = get_global_lock_path()
    os.remove(lock_path)
    log("Released global lock for PID: %s (%s)", os.getpid(), lock_path)

def loop():

    def cleanup(signum: int, frame: FrameType | None):
        nonlocal allow_loop
        global connection
        allow_loop = False
        connection.close()
        log("Cleaning up. (signum=%d)", signum)
        if os.path.exists(get_global_lock_path()):
            global_lock_release()
        sys.exit(0)

    allow_loop = True
    original_file_hash = get_self_hash()

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGQUIT, cleanup)

    while True:

        if original_file_hash != get_self_hash():
            log("File has changed.")
            cleanup(0, None)
            break

        if not allow_loop:
            log("Received signal to stop.")
            break

        # portionurl_id = portionurl_id_queue_pop()
        portionurl_id = get_portionurl_id()
        if portionurl_id:
            lock_acquire(portionurl_id)
            log("Downloading portionurl_id: %s", portionurl_id)
            # download_portionurl_interruptable(portionurl_id)
            exit_code = download_portionurl(portionurl_id)
            if exit_code == 0:
                log("Downloaded portionurl_id: %s", portionurl_id)
            else:
                log("Failed to download portionurl_id: %s (exit_code=%d)", portionurl_id, exit_code)
            lock_release(portionurl_id)
            if exit_code != 0:
                allow_loop = False

        if allow_loop:
            time.sleep(1)

def main():
    log("")
    release_stale_global_colored_lock()
    if global_lock_exists():
        log("Another instance is running.")
        sys.exit(0)
    global_lock_acquire()
    loop()
    global_lock_release()

connection = Connection("data/main.db")
# 
if __name__ == "__main__":
    main()

# run.vim:red
