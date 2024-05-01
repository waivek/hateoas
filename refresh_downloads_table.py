
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
    import hashlib
    with open(__file__, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

class LockFile:

    def __init__(self):
        self.lock_file_path = "/tmp/refresh_downloads_table.lock"
        if self.exists():
            self.remove_lock_file_if_pid_does_not_exist()
        assert not self.exists(), f"Lock file {self.lock_file_path} already exists."

    def remove_lock_file_if_pid_does_not_exist(self):
        from waivek import Code
        D = self.parse_lock_file()
        PID = int(D["PID"])
        if not os.path.exists(f"/proc/{PID}"):
            print(Code.RED + f"Removing lock file {self.lock_file_path} because PID {PID} does not exist.")
            self.release()

    def exists(self):
        return os.path.exists(self.lock_file_path)

    def acquire(self):
        PID = os.getpid()
        time_string = time.ctime()
        time_epoch = int(time.time())
        lines = [ f"PID: {PID}", f"Time: {time_string}", f"Epoch: {time_epoch}" ]
        with open(self.lock_file_path, "w") as f:
            f.write("\n".join(lines))

    def release(self):
        os.remove(self.lock_file_path)

    def parse_lock_file(self):
        with open(self.lock_file_path) as f:
            lines = f.readlines()
        D = {}
        for line in lines:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            D[key] = value
        return D

def loop():

    lock_file = LockFile()

    def cleanup(signum, frame):
        log(f"Received signal {signum}.")
        lock_file.release()

    lock_file.acquire()

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    original_hash = self_hash()

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
        loop()

