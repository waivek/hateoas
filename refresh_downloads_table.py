
from dbutils import Connection
from portionurl_to_download_path import portionurl_to_download_path
import os.path
import time
import sys
import signal
import os
connection = Connection("data/main.db")

from enum import Enum

class Path(Enum):
    BOTH_EXIST = 1
    NEITHER_EXIST = 2
    ONLY_PATH_EXIST = 3
    ONLY_PART_EXIST = 4


def portionurl_id_to_enum(portionurl_id):
    path = portionurl_to_download_path(portionurl_id)
    part_path = path + ".part"
    both_exist = os.path.exists(path) and os.path.exists(part_path)
    if both_exist:
        return Path.BOTH_EXIST
    elif not os.path.exists(path) and not os.path.exists(part_path):
        return Path.NEITHER_EXIST
    elif os.path.exists(path) and not os.path.exists(part_path):
        return Path.ONLY_PATH_EXIST
    elif not os.path.exists(path) and os.path.exists(part_path):
        return Path.ONLY_PART_EXIST
    else:
        assert False, "Should not reach here."

def refresh_downloads_table():
    cursor = connection.execute("SELECT portionurl_id FROM downloads;")
    portionurl_ids = [row[0] for row in cursor.fetchall()]
    for portionurl_id in portionurl_ids:
        enum = portionurl_id_to_enum(portionurl_id)
        match enum:
            case Path.BOTH_EXIST:
                raise Exception(f"Both path and part file exist for portionurl_id {portionurl_id}.")
            case Path.NEITHER_EXIST:
                cursor = connection.execute("SELECT status FROM downloads WHERE portionurl_id = ?;", (portionurl_id,))
                status = cursor.fetchone()[0]
                if status in [ "downloading", "complete" ]:
                    connection.execute("UPDATE downloads SET status = 'pending' WHERE portionurl_id = ?;", (portionurl_id,))
            case Path.ONLY_PATH_EXIST:
                connection.execute("UPDATE downloads SET status = 'complete' WHERE portionurl_id = ?;", (portionurl_id,))
            case Path.ONLY_PART_EXIST:
                connection.execute("UPDATE downloads SET status = 'downloading' WHERE portionurl_id = ?;", (portionurl_id,))
            case _:
                assert False, "Should not reach here."
    connection.commit()

def self_hash():
    # get the hash of this file
    import hashlib
    with open(__file__, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

class LockFile:

    def __init__(self):
        self.lock_file_path = "/tmp/refresh_downloads_table.lock"
        assert not self.exists(), "Lock file already exists."

    def exists(self):
        return os.path.exists(self.lock_file_path)

    def acquire(self):
        PID = os.getpid()
        time_string = time.ctime()
        lines = [ f"PID: {PID}", f"Time: {time_string}" ]
        with open(self.lock_file_path, "w") as f:
            f.write("\n".join(lines))

    def release(self):
        os.remove(self.lock_file_path)

def loop():

    lock_file = LockFile()

    def cleanup(signum, frame):
        log(f"Received signal {signum}.")
        lock_file.release()

    lock_file.acquire()

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    original_hash = self_hash()

    # if file has changed || lock file has been deleted || INT or TERM signal has been received, we break the loop
    # while lock_file.exists() and original_hash == self_hash() and not (signal.SIGINT or signal.SIGTERM):
    while True:
        if not lock_file.exists():
            log("Lock file has been deleted.")
            break
        if original_hash != self_hash():
            log("File has changed.")
            cleanup(None, None)
            break
        refresh_downloads_table()
        log("Refreshed downloads table.")
        time.sleep(1)


def log(message, *args):
    print(f"{int(time.time())} refresh_downloads_table.py {message}", *args)

if __name__ == "__main__":
    log(f"{sys.argv = }")
    if len(sys.argv) == 1:
        refresh_downloads_table()
        log("Refreshed downloads table.")
    elif sys.argv[1] == "loop":
        log("Looping")
        loop()

