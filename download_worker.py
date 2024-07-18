
# reloads if file changes, this is done by simply exiting when the file changes and `crontab` keeps starting it
# listens for interuption signals and cleans up

from dbutils import Connection
import signal
import os
import hashlib
from waivek import Code
import sys
from types import FrameType
import time
from portionurl_to_download_path import downloads_folder, downloaded
import psutil
from download_portionurl import download_portionurl

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

def get_lock_path(portionurl_id):
    lock_path = os.path.join(downloads_folder(), f"{portionurl_id}.lock")
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
    cursor = connection.execute("SELECT id FROM portionurls WHERE selected = 1;")
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

def tables_exist(connection, table_names: list[str]) -> bool:
    # get list of table-names in sqlite database
    cursor = connection.execute("SELECT name FROM sqlite_master WHERE type='table';")
    db_table_names = [ name for name, in cursor.fetchall() ]
    return all([ name in db_table_names for name in table_names ])

def get_missing_table_names(connection, table_names: list[str]) -> list[str]:
    # get list of table-names in sqlite database
    cursor = connection.execute("SELECT name FROM sqlite_master WHERE type='table';")
    db_table_names = [ name for name, in cursor.fetchall() ]
    return [ name for name in table_names if name not in db_table_names ]

def connection_to_db_path(connection):
    return connection.execute("PRAGMA database_list;").fetchone()[2]

def main():
    if not tables_exist(connection, [ "portionurls" ]):
        missing_table_names = get_missing_table_names(connection, [ "portionurls" ])
        db_path = connection_to_db_path(connection)
        log(db_path)
        log("Missing tables: %s", missing_table_names)
        log("Exiting. (tables do not exist)")

        sys.exit(0)
    if not os.path.exists(downloads_folder()):
        os.makedirs(downloads_folder())
    release_stale_global_colored_lock()
    if global_lock_exists():
        # Another instance is running.
        sys.exit(0)
    log("")
    global_lock_acquire()
    loop()
    global_lock_release()

connection = Connection("data/main.db")
# 
if __name__ == "__main__":
    main()

# run.vim:blue
