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
from download_chat import download_chat
from worker_utils import get_chat_downloads_folder, is_chat_downloaded, has_chat_part_file
import psutil
from worker_utils import log

def get_self_hash() -> str:
    with open(__file__, "r") as f:
        contents = f.read()

    file_hash = hashlib.md5(contents.encode()).hexdigest()
    return file_hash

def get_lock_path(video_id):
    lock_path = os.path.join(get_chat_downloads_folder(), f"video_chat-{video_id}.lock")
    return lock_path

def lock_acquire(video_id):
    lock_path = get_lock_path(video_id)
    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))
    log("Acquired lock for video_id: %s", video_id)

def lock_release(video_id):
    lock_path = get_lock_path(video_id)
    os.remove(lock_path)
    log("Released lock for video_id: %s", video_id)

def lock_exists(video_id):
    lock_path = get_lock_path(video_id)
    return os.path.exists(lock_path)

def lock_is_stale(video_id):
    lock_path = get_lock_path(video_id)
    with open(lock_path, "r") as f:
        pid = int(f.read())
    pid_exists = psutil.pid_exists(pid)
    if pid_exists:
        return False
    else:
        return True

def get_global_lock_path():
    if len(sys.argv) > 1 and sys.argv[1] in [ "red", "blue", "green", "yellow" ]:
        color = sys.argv[1]
        return f"/tmp/chat_download_worker_{color}.lock"
    return f"/tmp/chat_download_worker_{os.getpid()}.lock"

def global_lock_acquire():
    lock_path = get_global_lock_path()
    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))
    log("Acquired global lock for PID: %s (%s)", os.getpid(), lock_path)

def global_lock_release():
    lock_path = get_global_lock_path()
    os.remove(lock_path)
    log("Released global lock for PID: %s (%s)", os.getpid(), lock_path)

def global_lock_exists():
    lock_path = get_global_lock_path()
    return os.path.exists(lock_path)

def release_stale_global_colored_lock():
    # checks {{{
    if len(sys.argv) != 2:
        return
    if sys.argv[1] not in [ "red", "blue", "green", "yellow" ]:
        return
    lock_path = get_global_lock_path()
    if not os.path.exists(lock_path):
        return
    # checks }}}
    pid = int(open(lock_path, "r").read())
    if psutil.pid_exists(pid):
        return
    os.remove(lock_path)
    log("Released stale global lock: %s (%s)", pid, lock_path)

def get_video_id():
    global connection
    cursor = connection.execute("SELECT video_id FROM queue_chat;")
    video_ids = [ video_id for video_id, in cursor.fetchall() if not is_chat_downloaded(video_id) ]

    # remove stale locks
    for video_id in video_ids:
        if lock_exists(video_id) and lock_is_stale(video_id):
            log("Removing stale lock for video_id: %s", video_id)
            lock_release(video_id)

    # select a video_id that is not locked
    for video_id in video_ids:
        if not lock_exists(video_id):
            return video_id

    return None

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
        
        video_id = get_video_id()

        if video_id:
            lock_acquire(video_id)
            log("Downloading video_id: %s", video_id)
            exit_code = download_chat(video_id)
            if exit_code == 0:
                log("Downloaded video_id: %s", video_id)
            else:
                log("Failed to download video_id: %s (exit_code=%d)", video_id, exit_code)
            lock_release(video_id)
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
    if not tables_exist(connection, [ "queue_chat" ]):
        missing_table_names = get_missing_table_names(connection, [ "queue_chat" ])
        db_path = connection_to_db_path(connection)
        log(db_path)
        log("Missing tables: %s", missing_table_names)
        log("Exiting. (tables do not exist)")

        sys.exit(0)
    if not os.path.exists(get_chat_downloads_folder()):
        os.makedirs(get_chat_downloads_folder())
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
