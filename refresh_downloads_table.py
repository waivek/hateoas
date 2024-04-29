
from dbutils import Connection
from portionurl_to_download_path import portionurl_to_download_path
import os.path
import time
import sys
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

import signal
import os
def loop():

    lock_file_path = "/tmp/refresh_downloads_table.lock"
    if os.path.exists(lock_file_path):
        log("Lock file exists. Exiting.")
        return
    with open(lock_file_path, "w") as f:
        f.write(time.ctime())

    original_hash = self_hash()
    # loop_duration = 60
    # for _ in range(loop_duration):
    while True:
        refresh_downloads_table()
        log("Refreshed downloads table.")
        new_hash = self_hash()
        if new_hash != original_hash:
            log("Hash changed. Exiting.")
            break

        # handle signals
        # break on signal INT

        time.sleep(1)

    os.remove(lock_file_path)
    log("Removed lock file.")

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

